#!/usr/bin/env python
#coding:utf-8

import sys
import os
import conf
import const as vps_const
from _saas import VPS
from _saas.ttypes import CMD, NetFlow
from zthrift.client import get_client
from zkit.ip import int2ip 
from ops.vps import XenVPS
from ops.vps_ops import VPSOps
from lib.log import Log
import ops.vps_common as vps_common
from ops.xen import get_xen_inf, XenStore
import time
import re
import lib.daemon as daemon
import signal
import threading
from lib.timer_events import TimerEvents
import ops.netflow as netflow
import conf
from ops.migrate import MigrateClient

class VPSMgr (object):
    """ all exception should catch and log in this class """

    VERSION = 1

    def __init__ (self):
        self.logger = Log ("vps_mgr", config=conf)
        self.logger_net = Log ("vps_mgr_net", config=conf)
        self.logger_misc = Log ("misc", config=conf)
        self.logger_debug = Log ("debug", config=conf)
        self.host_id = conf.HOST_ID
        self.vpsops = VPSOps (self.logger)
        self.handlers = {
            CMD.OPEN: self.__class__.vps_open,
            CMD.REBOOT: self.__class__.vps_reboot,
            CMD.CLOSE: self.__class__.vps_close,
            CMD.OS: self.__class__.vps_reinstall_os,
            CMD.UPGRADE: self.__class__.vps_upgrade,
            CMD.BANDWIDTH: self.__class__.vps_set_bandwidth,
            CMD.RM: self.__class__.vps_delete,
        }
        self.timer = TimerEvents (time.time, self.logger_misc)
        assert conf.NETFLOW_COLLECT_INV > 0
        self.last_netflow = None
        self.netflow_inv = conf.NETFLOW_COLLECT_INV
        self.timer.add_timer (conf.NETFLOW_COLLECT_INV, self.monitor_netflow)
        self.timer.add_timer (12 * 3600, self.refresh_host_space)
        self.workers = []
        self.running = False

    def get_client (self):
        transport, client = get_client (VPS, timeout_ms=5000)
        return transport, client

    def monitor_netflow (self):
        result = None
        try:
            result = netflow.read_proc ()
        except Exception, e:
            self.logger_misc.exception ("cannot read netflow data from proc: %s" % (str(e)))
            return
        ts = time.time ()
        netflow_list = list ()
        try:
            for ifname, v in result.iteritems ():
                om = re.match ("^vps(\d+)$", ifname)
                if not om:
                    continue
                vps_id = int(om.group (1))
                if vps_id <= 0:
                    continue
                # direction of vps bridged network interface needs to be reversed
                netflow_list.append (NetFlow (vps_id, rx=v[1], tx=v[0]))
                if self.last_netflow and conf.LARGE_NETFLOW:
                    last_v = self.last_netflow.get (ifname)
                    if last_v:
                        _in = (v[1] - last_v[1]) * 8.0 / self.netflow_inv
                        _out = (v[0] - last_v[0]) * 8.0 / self.netflow_inv
                        if _in >= conf.LARGE_NETFLOW or _out >= conf.LARGE_NETFLOW:
                            self.logger_misc.warn ("%s in: %.3f mbps, out: %.3f mbps" % 
                                    (ifname, _in / 1024.0 / 1024.0, _out / 1024.0 /1024.0))
            self.last_netflow = result
        except Exception, e:
            self.logger_misc.exception ("netflow data format error: %s" % (str(e)))
            return
        if not netflow_list:
            self.logger_misc.info ("no netflow data is to be sent")
            return
        trans, client = self.get_client ()
        try:
            trans.open ()
            try:
                client.netflow_save (self.host_id, netflow_list, ts)
                self.logger_misc.info ("netflow data sent")
            finally:
                trans.close ()
        except Exception, e:
            self.logger_misc.exception ("cannot send netflow data: %s" % (str(e)))


    def run_once (self, cmd):
        vps_id = None
        vps_info = None
        try:
            trans, client = self.get_client ()
            trans.open ()
            try:
                vps_id = client.todo (self.host_id, cmd)
                self.logger_debug.info ("cmd:%s, vps_id:%s" % (cmd, vps_id))
                if vps_id > 0:
                    vps_info = client.vps (vps_id)
                    if not self.vps_is_valid (vps_info):
                        self.logger.error ("invalid vps data received, cmd=%s, %s" % (cmd, self.dump_vps_info (vps_info)))
                        self.done_task(cmd, vps_id, False, "invalid vpsinfo")
                        vps_info = None
            finally:
                trans.close ()
        except Exception, e:
            self.logger_net.exception (e) 
            return False
        if not vps_info:
            return False
        h = self.handlers.get (cmd)
        if callable (h):
            try:
                h (self, vps_info)
                return True
            except Exception, e:
                self.logger.exception ("vps %s, uncaught exception: %s" % (vps_info.id, str(e)))
                #TODO notify maintainments
                return False
        else:
            self.logger.warn ("no handler for cmd %s, vps: %s" % (str(cmd), self.dump_vps_info(vps_info)))
            self.done_task (cmd, vps_id, False, "not implemented")
            return False

    def run_loop (self, *cmds):
        self.logger.info ("worker for %s started" % (str(cmds)))
        while self.running:
            time.sleep(0.5)
            try:
                for cmd in cmds:
                    if not self.running:
                        break
                    res = self.run_once (cmd)
                    if not self.running:
                        break
                    if not res:
                        time.sleep (1.5)
                    else:
                        time.sleep (1)
            except Exception, e:
                self.logger.exception ("uncaught exception: " + str(e))
        self.logger.info ("worker for %s stop" % (str(cmds)))

    def done_task (self, cmd, vps_id, is_ok, msg=''):
        state = 0
        if not is_ok:
            state = 1 
        try:
            trans, client = self.get_client ()
            trans.open ()
            try:
                self.logger.info ("send done_task cmd=%s vps_id=%s" % (str(cmd), str(vps_id)))
                client.done (self.host_id, cmd, vps_id, state, msg)
            finally:
                trans.close ()
        except Exception, e:
            self.logger_net.exception (e)

    @staticmethod
    def vps_is_valid (vps_info):
        if vps_info is None or vps_info.id <= 0:
            return None
        if not vps_info.harddisks.has_key(0) or vps_info.harddisks[0] <= 0:
            return None
        if not vps_info.password:
            return None
        return vps_info

    @staticmethod
    def vpsinfo_check_ip (vps_info):
        if not vps_info.ext_ips or not vps_info.gateway or not vps_info.gateway.ipv4 or vps_info.cpu <= 0 or vps_info.ram <= 0:
            return None
        return vps_info


    @staticmethod
    def dump_vps_info (vps_info):
        ip = vps_info.ext_ips and "(%s)" % ",".join (map (lambda ip:"%s/%s(%s)" % (int2ip(ip.ipv4), int2ip(ip.ipv4_netmask), ip.mac), vps_info.ext_ips)) or None
        if vps_info.int_ip and vps_info.int_ip.ipv4:
            ip_inter = "%s/%s" % (int2ip(vps_info.int_ip.ipv4), int2ip(vps_info.int_ip.ipv4_netmask))
        else:
            ip_inter = None
        if vps_info.gateway and vps_info.gateway.ipv4:
            gateway = "%s/%s" % (int2ip(vps_info.gateway.ipv4), int2ip(vps_info.gateway.ipv4_netmask))
        else:
            gateway = None
        hd = vps_info.harddisks and "(%s)" % ",".join (map (lambda x: "%s:%s" % (x[0], x[1]), vps_info.harddisks.items ())) or None
        if vps_info.state is not None:
            state = "%s(%s)" % (vps_info.state, vps_const.VM_STATE_CN[vps_info.state])
        else:
            state = None
        return "host_id %s, id %s, state %s, os %s, cpu %s, ram %sM, hd %sG, ip %s, gateway %s, inter_ip:%s, bandwidth:%s" % (
                vps_info.host_id, vps_info.id, state, 
                vps_info.os, vps_info.cpu, vps_info.ram, hd, 
                ip, gateway, ip_inter, vps_info.bandwidth,
            )

    def setup_vps (self, xenvps, vps_info):
        root_size = vps_info.harddisks and vps_info.harddisks[0] or 0
        xenvps.setup (os_id=vps_info.os, vcpu=vps_info.cpu, mem_m=vps_info.ram,
                disk_g=root_size, root_pw=vps_info.password, gateway=vps_info.gateway and int2ip (vps_info.gateway.ipv4) or 0)
        ip_dict = dict ()
        for ip in vps_info.ext_ips:
            ip_dict[int2ip (ip.ipv4)] = int2ip (ip.ipv4_netmask)
            xenvps.add_netinf_ext (ip_dict, mac=ip.mac, bandwidth=vps_info.bandwidth)
        ip_inner_dict = dict ()
        if vps_info.int_ip and vps_info.int_ip.ipv4:
            ip_inner_dict[int2ip (vps_info.int_ip.ipv4)] = int2ip (vps_info.int_ip.ipv4_netmask)
            xenvps.add_netinf_int (ip_inner_dict)
        if vps_info.harddisks:
            for disk_id, disk_size in vps_info.harddisks.iteritems ():
                if disk_id != 0:
                    xenvps.add_extra_storage (disk_id, disk_size)



    def vps_open (self, vps_info, vps_image=None, is_new=True): 
        vps_id = vps_info.id
        self.logger.info ("to open vps %s" % (vps_id))
        if vps_info.host_id != self.host_id:
            msg = "vpsopen : vps %s host_id=%s != current host %s , abort" % (vps_id, vps_info.host_id, self.host_id)
            self.logger.error (msg)
            self.done_task (CMD.OPEN, vps_id, False, msg)
            return
        if not self.vpsinfo_check_ip (vps_info):
            msg = "no ip with vps %s" % (vps_id)
            self.logger.error (msg)
            self.done_task (CMD.OPEN, vps_id, False, msg)
            return
        xv = XenVPS (vps_id)
        try:
            domain_dict = XenStore.domain_name_id_map ()
            limit = None
            if 'VPS_NUM_LIMIT' in dir(conf):
                limit = conf.VPS_NUM_LIMIT
            if limit and len (domain_dict.keys ()) >= limit + 1:
                msg = "vps open: cannot open more than %d vps" % (limit)
                self.logger.error (msg)
                self.done_task (CMD.OPEN, vps_id, False, msg)
                return
            self.setup_vps (xv, vps_info)
            if xv.is_running ():
                msg = "vps %s is running" % (vps_id)
                self.logger.error (msg)
                self.done_task (CMD.OPEN, vps_id, True, msg)
                return
            if vps_info.state in [vps_const.VM_STATE.PAY, vps_const.VM_STATE.OPEN, vps_const.VM_STATE.CLOSE]:
                if self.vpsops.is_normal_exists (vps_id):
                    xv.check_storage_integrity ()
                    xv.check_xen_config ()
                    if not xv.is_running ():
                        self.logger.info ("seems vps %s was not closed, try to boot" % (vps_id))
                        self.vpsops._boot_and_test (xv, is_new=False)
                elif self.vpsops.is_trash_exists (vps_id):
                    self.vpsops.reopen_vps (vps_id, xv)
                else:
                    self.vpsops.create_vps (xv, vps_image, is_new)
            else:
                msg = "vps%s state is %s(%s)" % (str(vps_id), vps_info.state, vps_const.VM_STATE_CN[vps_info.state])
                self.logger.error (msg)
                self.done_task (CMD.OPEN, vps_id, False, msg)
                return
        except Exception, e:
            self.logger.exception ("vps %s: %s" % (str(vps_id), str(e)))
            self.done_task (CMD.OPEN, vps_id, False, "error, " + str(e))
            return
        self.done_task (CMD.OPEN, vps_id, True)
        self.refresh_host_space ()
        return True

    def vps_change_ip (self, vps_info):
        self.logger.info ("to change ip vps %s" % (vps_info.id))
        if not self.vpsinfo_check_ip (vps_info):
            msg = "no ip with vps %s" % (vps_info.id)
            self.logger.error (msg)
            return
        try:
            xv = XenVPS (vps_info.id)
            self.setup_vps (xv, vps_info)
            self.vpsops.change_ip (xv)
        except Exception, e:
            self.logger.error (e)
        return


    def vps_reinstall_os (self, vps_info):
        self.logger.info ("to reinstall vps %s, os=%s" % (vps_info.id, vps_info.os))
        if not self.vpsinfo_check_ip (vps_info):
            msg = "no ip with vps %s" % (vps_info.id)
            self.logger.error (msg)
            self.done_task (CMD.OS, vps_info.id, False, msg)
            return
        if vps_info.host_id != self.host_id:
            msg = "vps reinstall_os : vps %s host_id=%s != current host %s , abort" % (vps_info.id, vps_info.host_id, self.host_id)
            self.logger.error (msg)
            self.done_task (CMD.OS, vps_info.id, False, msg)
            return
        return self._reinstall_os (vps_info.id, vps_info)

    def _reinstall_os (self, vps_id, vps_info=None, os_id=None, vps_image=None):
        try:
            xv = None
            if vps_info:
                xv = XenVPS (vps_info.id)
                self.setup_vps (xv, vps_info)
            self.vpsops.reinstall_os (vps_id, xv, os_id, vps_image)
            if vps_info:
                self.done_task (CMD.OS, vps_id, True, "os:%s" % (vps_info.os))
            return True
        except Exception, e:
            self.logger.exception ("vps %s: %s" % (str(vps_id), str(e)))
            if vps_info:
                self.done_task (CMD.OS, vps_id, False, "os:%s, error: %s "% (vps_info.os,  str(e)))
            return False

    def vps_upgrade (self, vps_info):
        self.logger.info ("to upgrade vps %s" % (vps_info.id))
        #TODO done task
        if not self.vpsinfo_check_ip (vps_info):
            msg = "no ip with vps %s" % (vps_info.id)
            self.logger.error (msg)
            self.done_task (CMD.UPGRADE, vps_info.id, False, msg)
            return
        try:
            xv = XenVPS (vps_info.id)
            self.setup_vps (xv, vps_info)
            self.vpsops.upgrade_vps (xv)
            self.refresh_host_space ()
            self.done_task(CMD.UPGRADE, vps_info.id, True)
            return True
        except Exception, e:
            self.logger.exception ("vps %s: %s" % (str(vps_info.id), str(e)))
            self.done_task(CMD.UPGRADE, vps_info.id, False, "exception %s" % str(e))
            return False

    def vps_reboot (self, vps_info):
        xv = XenVPS (vps_info.id) 
        self.logger.info ("to reboot vps %s" % (vps_info.id))
        try:
            self.setup_vps (xv, vps_info)
            self.vpsops.reboot_vps (xv)
        except Exception, e:
            self.logger.exception (e)
            self.done_task (CMD.REBOOT, vps_info.id, False, "exception %s" % (str(e)))
            return
        self.done_task (CMD.REBOOT, vps_info.id, True)
        return True

    def vps_set_bandwidth (self, vps_info):
        xv = XenVPS (vps_info.id)
        self.logger.info ("to modify bandwidth for vps %s" % (vps_info.id))
        try:
            self.setup_vps (xv, vps_info)
            self.vpsops.change_qos (xv)
        except Exception, e:
            self.logger.exception (e)
            self.done_task (CMD.BANDWIDTH, vps_info.id, False, "exception %s" % (str(e)))
            return
        self.done_task (CMD.BANDWIDTH, vps_info.id, True)
        return True

    def vps_host_sync (self, vps_id):
        try:
            task = query_migrate_task (vps_id)
            if not task:
                self.logger.warn ("no migrate task for vps%s" % (vps_id))
                return
                return
            to_host_ip = int2ip (task.to_host_ip)
            mgclient = MigrateClient (self.logger, to_host_ip)
            # TODO speed
            self.vpsops.hotsync_vps (mgclient, vps_id, to_host_ip, speed=5)


    def query_vps (self, vps_id):
        trans, client = self.get_client ()
        trans.open ()
        vps_info = None
        try:
            vps_info = client.vps (vps_id)
        finally:
            trans.close ()
        if vps_info is None or vps_info.id <= 0:
            return None
        return vps_info

    def query_migrate_task (self, vps_id):
        trans, client = self.get_client ()
        trans.open ()
        task = None
        try:
            task = client.migrate_task (vps_id)
        finally:
            trans.close ()
        if task is None or task.id <= 0:
            return None
        if task.to_host_ip <= 0:
            raise Exception ("no destination host ip for task%s vps%s" % (task.id, vps_id))
        return task

    def refresh_host_space (self):
        disk_remain = None
        mem_remain = None
        disk_total = None
        mem_total = None
        try:
            disk_remain = -1
            disk_total = -1 
            if conf.USE_LVM:
                disk_remain, disk_total = vps_common.vg_space (conf.VPS_LVM_VGNAME) # in g
                if "LVM_VG_MIN_SPACE" in dir(conf) and conf.LVM_VG_MIN_SPACE:
                    extra = int(conf.LVM_VG_MIN_SPACE)
                    disk_remain -= extra
                if disk_remain < 0:
                    disk_remain = 0
            xen_inf = get_xen_inf ()
            mem_remain = xen_inf.mem_free () # in m
            mem_total = xen_inf.mem_total ()
        except Exception, e:
            self.logger.exception (e)
            return
        try:
            trans, client = self.get_client ()
            trans.open ()
            try:
                client.host_refresh (self.host_id, disk_remain, mem_remain, disk_total, mem_total)
            finally:
                trans.close ()
            self.logger.info ("send host remain disk:%dG, mem:%dM, total disk:%dG, mem:%dM" % (disk_remain, mem_remain, disk_total, mem_total))
        except Exception, e:
            self.logger_net.exception (e)

    def _vps_delete (self, vps_id, vps_info=None, check_date=False):
        try:
            xv = None
            if vps_info:
                xv = XenVPS (vps_id)
                self.setup_vps (xv, vps_info)
            self.vpsops.delete_vps (vps_id, xv, check_date=check_date)
            self.done_task(CMD.RM, vps_id, True)
        except Exception, e:
            self.logger.exception (e)
            raise e

    def vps_delete (self, vps_info):
        try:
            self._vps_delete (vps_info.id, vps_info, check_date=True)
        except Exception, e:
            self.done_task (CMD.RM, vps_info.id, False, "exception %s" % (str(e)))


    def vps_close (self, vps_info):
        try:
            if vps_info.state == vps_const.VM_STATE.CLOSE or vps_info.host_id != self.host_id:
                xv = XenVPS (vps_info.id)
                self.setup_vps (xv, vps_info)
                self.vpsops.close_vps (vps_info.id, xv)
            else:
                raise Exception ("state check not passed")
        except Exception, e:
            self.logger.exception (e)
            self.done_task (CMD.CLOSE, vps_info.id, False, "exception %s" % (str(e)))
            return
        self.done_task (CMD.CLOSE, vps_info.id, True)
        self.refresh_host_space ()
        return True

            
    def loop (self):
        while self.running:
            self.run_loop(CMD.BANDWIDTH) # because ovs db searching uses signal and can only work in main thread ...
            time.sleep (1)
        self.timer.stop () 
        self.logger.info ("timer stopped")
        while self.workers:
            th = self.workers.pop (0)
            th.join ()
        self.logger.info ("all stopped")

    def start_worker (self, *cmds):
        th = threading.Thread (target=self.run_loop, args=cmds)
        try:
            th.setDaemon (1)
            th.start ()
            self.workers.append (th)
        except Exception, e:
            self.logger.info ("failed to start worker for cmd %s, %s" % (str(cmds), str(e)))

    def start (self):
        if self.running:
            return
        self.running = True
        self.start_worker (CMD.OPEN, CMD.CLOSE, CMD.OS, CMD.UPGRADE, CMD.REBOOT, CMD.RM)
        self.timer.start ()
        self.logger.info ("timer started")

    def stop (self):
        if not self.running:
            return
        self.running = False
        self.logger.info ("stopping client")


def usage ():
    print "usage:\t%s star/stop/restart\t#manage forked daemon" % (sys.argv[0])
    print "\t%s run\t\t# run without daemon, for test purpose" % (sys.argv[0])
    os._exit (1)


stop_signal_flag = False
            
def _main():
    client = VPSMgr ()

    def exit_sig_handler (sig_num, frm):
        global stop_signal_flag
        if stop_signal_flag:
            return
        stop_signal_flag = True
        client.stop ()
        return
    client.start ()
    signal.signal (signal.SIGTERM, exit_sig_handler)
    signal.signal (signal.SIGINT, exit_sig_handler)
    client.loop ()
    return



if __name__ == "__main__":

    logger = Log ("daemon", config=conf) # to ensure log is permitted to write
    pid_file = "vps_mgr.pid"
    mon_pid_file = "vps_mgr_mon.pid"
    action = sys.argv[1]

    if len (sys.argv) <= 1:
        usage ()
    else:
        daemon.cmd_wrapper (action, _main, usage, logger, conf.log_dir, conf.RUN_DIR, pid_file, mon_pid_file)


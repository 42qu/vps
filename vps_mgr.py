#!/usr/bin/env python2.6
#coding:utf-8

import sys
import os
import conf
import saas.const.vps as vps_const
from saas import VPS
from saas.ttypes import Cmd
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
from saas.ttypes import NetFlow
import conf

class VPSMgr (object):
    """ all exception should catch and log in this class """

    VERSION = 1

    def __init__ (self):
        self.logger = Log ("vps_mgr", config=conf)
        self.logger_err = Log ("vps_mgr_err", config=conf)
        self.logger_misc = Log ("misc", config=conf) 
        self.logger_debug = Log ("debug", config=conf)
        self.host_id = conf.HOST_ID
        self.vpsops = VPSOps (self.logger)
        self.handlers = {
            Cmd.OPEN: self.__class__.vps_open,
            Cmd.REBOOT: self.__class__.vps_reboot,
            Cmd.CLOSE: self.__class__.vps_close,
            Cmd.OS: self.__class__.vps_reinstall_os,
        }
        self.timer = TimerEvents (time.time, self.logger_misc)
        assert conf.NETFLOW_COLLECT_INV > 0
        self.timer.add_timer (conf.NETFLOW_COLLECT_INV, self.send_netflow)
        self.timer.add_timer (12 * 3600, self.refresh_host_space)
        self.workers = []
        self.running = False

    def get_client (self):
        transport, client = get_client (VPS, timeout_ms=5000)
        return transport, client

    def send_netflow (self):
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
            self.logger_err.exception (e)
            return False
        if not vps_info:
            return False
        h = self.handlers.get (cmd)
        if callable (h):
            try:
                h (self, vps_info)
                return True
            except Exception, e:
                self.logger_err.exception ("vps %s, uncaught exception: %s" % (vps_info.id, str(e)))
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
                self.logger_err.exception ("uncaught exception: " + str(e))
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
            self.logger_err.exception (e)

    @staticmethod
    def vps_is_valid (vps_info):
        if vps_info is None or vps_info.id <= 0:
            return None
        if not vps_info.ipv4 or not vps_info.ipv4_gateway or vps_info.cpu <= 0 or vps_info.ram <= 0 or vps_info.hd <= 0 or not vps_info.password:
            return None
        return vps_info

    @staticmethod
    def dump_vps_info (vps_info):
        ip = vps_info.ipv4 is not None and int2ip (vps_info.ipv4) or None
        ip_inter = vps_info.ipv4_inter is not None  and int2ip (vps_info.ipv4_inter) or None
        netmask = vps_info.ipv4_netmask is not None and int2ip (vps_info.ipv4_netmask) or None
        gateway = vps_info.ipv4_gateway is not None and int2ip (vps_info.ipv4_gateway) or None
        if vps_info.state is not None:
            state = "%s(%s)" % (vps_info.state, vps_const.VPS_STATE2CN[vps_info.state])
        else:
            state = None
        return "host_id %s, id %s, state %s, os %s, cpu %s, ram %sM, hd %sG, ip %s, netmask %s, gateway %s, inter_ip:%s, bandwidth:%s" % (
                vps_info.host_id, vps_info.id, state, 
                vps_info.os, vps_info.cpu, vps_info.ram, vps_info.hd, 
                ip, netmask, gateway, ip_inter, vps_info.bandwidth,
            )

    def setup_vps (self, xenvps, vps_info):
        xenvps.setup (os_id=vps_info.os, vcpu=vps_info.cpu, mem_m=vps_info.ram, disk_g=vps_info.hd, root_pw=vps_info.password)
        xenvps.add_netinf_ext (ip=int2ip (vps_info.ipv4), netmask=int2ip (vps_info.ipv4_netmask), gateway=int2ip (vps_info.ipv4_gateway))


    def vps_open (self, vps_info, vps_image=None, is_new=True): 
        self.logger.info ("to open vps %s" % (vps_info.id))
        if vps_info.host_id != self.host_id:
            msg = "vpsopen : vps %s host_id=%s != current host %s , abort" % (vps_info.id, vps_info.host_id, self.host_id)
            self.logger.error (msg)
            self.done_task (Cmd.OPEN, vps_info.id, False, msg)
            return
        xv = XenVPS (vps_info.id)
        try:
            domain_dict = XenStore.domain_name_id_map ()
            msg = "vps open: cannot open more than 39 vps"
            if len (domain_dict.keys ()) >= 40:
                self.logger.error (msg)
                self.done_task (Cmd.OPEN, vps_info.id, False, msg)
                return
            self.setup_vps (xv, vps_info)
            if xv.is_running ():
                msg = "vps %s is running" % (vps_info.id)
                self.logger_err.error (msg)
                self.done_task (Cmd.OPEN, vps_info.id, False, msg)
                return
            if vps_info.state in [vps_const.VPS_STATE_PAY, vps_const.VPS_STATE_RUN]:
                self.vpsops.create_vps (xv, vps_image, is_new)
            elif vps_info.state == vps_const.VPS_STATE_CLOSE:
                self.vpsops.reopen_vps (vps_info.id, xv)
            else:
                msg = "vps%s state is %s(%s)" % (str(vps_info.id), vps_info.state, vps_const.VPS_STATE2CN[vps_info.state])
                self.logger_err.error (msg)
                self.done_task (Cmd.OPEN, vps_info.id, False, msg)
                return
        except Exception, e:
            self.logger_err.exception ("for %s: %s" % (str(vps_info.id), str(e)))
            self.done_task (Cmd.OPEN, vps_info.id, False, "error, " + str(e))
            return
        self.done_task (Cmd.OPEN, vps_info.id, True)
        return True

    def vps_reinstall_os (self, vps_info):
        self.logger.info ("to reinstall vps %s, os=%s" % (vps_info.id, vps_info.os))
        if vps_info.host_id != self.host_id:
            msg = "vps reinstall_os : vps %s host_id=%s != current host %s , abort" % (vps_info.id, vps_info.host_id, self.host_id)
            self.logger.error (msg)
            self.done_task (Cmd.OS, vps_info.id, False, msg)
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
                self.done_task (Cmd.OS, vps_id, True, "os:%s" % (vps_info.os))
            return True
        except Exception, e:
            self.logger_err.exception ("for %s: %s" % (str(vps_id), str(e)))
            if vps_info:
                self.done_task (Cmd.OS, vps_id, False, "os:%s, error: %s "% (vps_info.os,  str(e)))
            return False

    def vps_upgrade (self, vps_info):
        self.logger.info ("to upgrade vps %s" % (vps_info.id))
        #TODO done task
        try:
            xv = XenVPS (vps_info.id)
            self.setup_vps (xv, vps_info)
            self.vpsops.upgrade_vps (xv)
            return True
        except Exception, e:
            self.logger_err.exception ("for %s: %s" % (str(vps_info.id), str(e)))
            #TODO done task
            return False


    def vps_reboot (self, vps_info):
        xv = XenVPS (vps_info.id) 
        self.logger.info ("to reboot vps %s" % (vps_info.id))
        try:
            self.setup_vps (xv, vps_info)
            self.vpsops.reboot_vps (xv)
        except Exception, e:
            self.logger_err.exception (e)
            self.done_task (Cmd.REBOOT, vps_info.id, False, "exception %s" % (str(e)))
            return
        self.done_task (Cmd.REBOOT, vps_info.id, True)
        return True

    def modify_vif_rate (self, vps_info):
        xv = XenVPS (vps_info.id)
        self.logger.info ("to modify vif rate for vps %s" % (vps_info.id))
        try:
            self.setup_vps (xv, vps_info)
            self.vpsops.create_xen_config (vps_info)
        except Exception, e:
            self.logger_err.exception (e)
            self.done_task (Cmd.BANDWIDTH, vps_info.id, False, "exception %s" % (str(e)))
            return
        self.done_task (Cmd.BANDWIDTH, vps_info.id, True)
        return True


    def query_vps (self, vps_id):
        trans, client = self.get_client ()
        trans.open ()
        vps_info = None
        try:
            vps_info = client.vps (vps_id)
        finally:
            trans.close ()
        if VPSMgr.vps_is_valid (vps_info):
            return vps_info
        return None

    def refresh_host_space (self):
        if not conf.USE_LVM:
            return
        try:
            extra = 0
            if "LVM_VG_MIN_SPACE" in dir(conf) and conf.LVM_VG_MIN_SPACE:
                extra = int(conf.LVM_VG_MIN_SPACE)
            disk_remain = vps_common.vg_free_space (conf.VPS_LVM_VGNAME) # in g
            disk_remain -= extra
            if disk_remain < 0:
                disk_remain = 0
            xen_inf = get_xen_inf ()
            mem_remain = xen_inf.mem_free () # in m
            trans, client = self.get_client ()
            trans.open ()
            try:
                client.host_refresh (self.host_id, disk_remain, mem_remain)
            finally:
                trans.close ()
            self.logger.info ("send host remain disk:%dG, mem:%dM" % (disk_remain, mem_remain))
        except Exception, e:
            self.logger_err.exception (e)

    def _vps_delete (self, vps_id, vps_info=None):
        try:
            xv = None
            if vps_info:
                xv = XenVPS (vps_id)
                self.setup_vps (xv, vps_info)
            self.vpsops.delete_vps (vps_id, xv)
        except Exception, e:
            self.logger_err.exception (e)
            raise e

    def vps_close (self, vps_info):
        try:
            assert vps_info.state == vps_const.VPS_STATE_CLOSE
            xv = XenVPS (vps_info.id)
            self.setup_vps (xv, vps_info)
            self.vpsops.close_vps (vps_info.id, xv)
        except Exception, e:
            self.logger_err.exception (e)
            self.done_task (Cmd.CLOSE, vps_info.id, False, "exception %s" % (str(e)))
            return
        self.done_task (Cmd.CLOSE, vps_info.id, True)
        return True

            
    def loop (self):
        while self.running:
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
            self.logger_err.info ("failed to start worker for cmd %s, %s" % (str(cmds), str(e)))

    def start (self):
        if self.running:
            return
        self.running = True
        self.start_worker (Cmd.OPEN, Cmd.CLOSE, Cmd.OS)
        self.start_worker (Cmd.REBOOT)
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


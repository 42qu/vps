#!/usr/bin/env python
#coding:utf-8

import sys
import os
import conf
from lib.ip import is_host_ip
from ops.vps import XenVPS
from ops.vps_ops import VPSOps
from lib.log import Log
import ops.vps_common as vps_common
from ops.ixen import get_xen_inf, XenStore
from ops.xenstat import XenStat
import time
import re
import lib.daemon as daemon
import signal
import threading
from lib.timer_events import TimerEvents
import ops.netflow as netflow
import ops.diskstat as diskstat
from ops.migrate import MigrateClient
from ops.carbon_client import CarbonPayload, send_data, fix_flow
from ops.saas_rpc import SAAS_Client, RPC_Exception, CMD, VM_STATE, MIGRATE_STATE, VM_STATE_CN
import socket
import glob

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
            CMD.PRE_SYNC: self.__class__.vps_hot_sync,
            CMD.MIGRATE: self.__class__.vps_migrate,
            CMD.RESET_PW: self.__class__.vps_reset_pw,
        }
        self._locker = threading.Lock ()
        self._vps_locker = dict ()
        self.xenstat = XenStat ()
        self.timer = TimerEvents (time.time, self.logger_misc)
        assert conf.MONITOR_COLLECT_INV > 0
        self.last_netflow = None
        self.last_diskstat = None
        self.monitor_inv = conf.MONITOR_COLLECT_INV
        self.last_monitor_ts = None
        self.timer.add_timer (conf.MONITOR_COLLECT_INV, self.monitor_vps)
        self.timer.add_timer (12 * 3600, self.refresh_host_space)
        self.workers = []
        self.running = False

    def _try_lock_vps (self, cmd, vps_id):
        self._locker.acquire ()
        if self._vps_locker.has_key (vps_id):
            _cmd = self._vps_locker.get (vps_id)
            self.logger_debug.info ("CMD %s try to lock vps%s failed: locked by CMD %s" % (
                CMD._get_name(cmd), vps_id, CMD._get_name(_cmd)
                ))
            res = False
        else:
            self._vps_locker[vps_id] = cmd
            res = True
        self._locker.release ()
        return res

    def _unlock_vps (self, cmd, vps_id):
        self._locker.acquire ()
        try:
            _cmd = self._vps_locker.get (vps_id)
            if _cmd == cmd:
                del self._vps_locker[vps_id]
        except KeyError:
            pass
        self._locker.release ()

    def rpc_connect (self):
        rpc = SAAS_Client (self.host_id, self.logger)
        rpc.connect ()
        return rpc

    def monitor_vps (self):
        net_result = None
        disk_result = None
        try:
            net_result = netflow.read_proc ()
            disk_devs = glob.glob ("/dev/main/vps*")
            if 'MAIN_DISK' in dir (conf):
                disk_devs.append (conf.MAIN_DISK)
            disk_result = diskstat.read_stat (disk_devs)
        except Exception, e:
            self.logger_misc.exception ("cannot read netflow data from proc: %s" % (str(e)))
            return
        ts = time.time ()
        dom_map = XenStore.domain_name_id_map ()
        dom_names = dom_map.keys ()
        self.xenstat.run (dom_names)
        payload = CarbonPayload ()
        try:
            payload.append ("host.cpu.%s.all" % (self.host_id), ts, self.xenstat.total_cpu)
            for dom_name in dom_names:
                om = re.match ("^vps(\d+)$", dom_name)
                if not om:
                    # dom0
                    dom_cpu = self.xenstat.dom_dict.get (dom_name)
                    if dom_cpu:
                        payload.append ("host.cpu.%s.dom0" % (self.host_id), dom_cpu['ts'], dom_cpu['cpu_avg'])
                    if 'MAIN_DISK' in dir(conf) and self.last_diskstat:
                        t_elapse = ts - self.last_monitor_ts
                        v = disk_result.get (conf.MAIN_DISK)
                        last_v = self.last_diskstat.get (conf.MAIN_DISK)
                        read_ops, read_byte, write_ops, write_byte, util = diskstat.cal_stat (v, last_v, t_elapse)
                        payload.append ("host.io.%d.ops.read" % (self.host_id), ts, read_ops)
                        payload.append ("host.io.%d.ops.write" % (self.host_id), ts, write_ops)
                        payload.append ("host.io.%s.traffic.read" % (self.host_id), ts, read_byte)
                        payload.append ("host.io.%s.traffic.write" % (self.host_id), ts, write_byte)
                        payload.append ("host.io.%s.util" % (self.host_id), ts, util)
                        print conf.MAIN_DISK, read_ops, write_ops, read_byte, write_byte, util
                    if self.last_netflow:
                        t_elapse = ts - self.last_monitor_ts
                        v = net_result.get (conf.EXT_INF)
                        last_v = self.last_netflow.get (conf.EXT_INF)
                        _in = fix_flow ((v[0] - last_v[0]) * 8.0 / t_elapse)
                        _out = fix_flow ((v[1] - last_v[1]) * 8.0 / t_elapse)
                        _in_pp = (v[2] - last_v[2]) / t_elapse
                        _out_pp = (v[3] - last_v[3]) / t_elapse
                        payload.append ("host.netflow.%d.ext.in"%(self.host_id), ts, _in)
                        payload.append ("host.netflow.%d.ext.out"%(self.host_id), ts, _out)
                        payload.append ("host.netflow.%d.ext_pp.in"%(self.host_id), ts, _in_pp > 0 and _in_pp or 0)
                        payload.append ("host.netflow.%d.ext_pp.out"%(self.host_id), ts, _out_pp > 0 and _out_pp or 0)
                        v = net_result.get (conf.INT_INF)
                        last_v = self.last_netflow.get (conf.INT_INF)
                        _in = fix_flow ((v[0] - last_v[0]) * 8.0 / t_elapse)
                        _out = fix_flow ((v[1] - last_v[1]) * 8.0 / t_elapse)
                        _in_pp = (v[2] - last_v[2]) / t_elapse
                        _out_pp = (v[3] - last_v[3]) / t_elapse
                        payload.append ("host.netflow.%d.int.in"%(self.host_id), ts, _in)
                        payload.append ("host.netflow.%d.int.out"%(self.host_id), ts, _out)
                        payload.append ("host.netflow.%d.int_pp.in"%(self.host_id), ts, _in_pp > 0 and _in_pp or 0)
                        payload.append ("host.netflow.%d.int_pp.out"%(self.host_id), ts, _out_pp > 0 and _out_pp or 0)
                else:
                    vps_id = int(om.group (1))
                    xv = self.vpsops.load_vps_meta (vps_id)
                    dom_cpu = self.xenstat.dom_dict.get (dom_name)
                    if dom_cpu:
                        payload.append ("vps.cpu.%s" % (vps_id), dom_cpu['ts'], dom_cpu['cpu_avg'])
                    if not self.last_netflow or not self.last_diskstat:
                        break
                    #net
                    ifname = dom_name
                    vif = xv.vifs.get (ifname)
                    v = net_result.get (ifname)
                    last_v = self.last_netflow.get (ifname)
                    t_elapse = ts - self.last_monitor_ts
                    if v and last_v:
                        # direction of vps bridged network interface needs to be reversed
                        _in = fix_flow ((v[1] - last_v[1]) * 8.0 / t_elapse)
                        _out = fix_flow ((v[0] - last_v[0]) * 8.0 / t_elapse)
                        _in = (vif.bandwidth and vif.bandwidth * 1024 * 1024 < _in) and vif.bandwidth * 1024 * 1024 or _in
                        _out = (vif.bandwidth and vif.bandwidth * 1024 * 1024 < _out) and vif.bandwidth * 1024 * 1024 or _out
                        payload.append ("vps.netflow.%d.in"%(vps_id), ts, _in)
                        payload.append ("vps.netflow.%d.out"%(vps_id), ts, _out)
                        if conf.LARGE_NETFLOW and _in >= conf.LARGE_NETFLOW or _out >= conf.LARGE_NETFLOW:
                            self.logger_misc.warn ("%s in: %.3f mbps, out: %.3f mbps" % 
                                    (ifname, _in / 1024.0 / 1024.0, _out / 1024.0 /1024.0))
                    #disk
                    if conf.USE_LVM and self.last_diskstat:
                        for disk in xv.data_disks.values ():
                            v = disk_result.get (disk.dev)
                            last_v = self.last_diskstat.get (disk.dev)
                            if not last_v:
                                continue
                            read_ops, read_byte, write_ops, write_byte, util = diskstat.cal_stat (v, last_v, t_elapse)
                            print disk.xen_dev
                            payload.append ("vps.io.%d.%s.ops.read" % (vps_id, disk.xen_dev), ts, read_ops)
                            payload.append ("vps.io.%d.%s.ops.write" % (vps_id, disk.xen_dev), ts, write_ops)
                            payload.append ("vps.io.%d.%s.traffic.read" % (vps_id, disk.xen_dev), ts, read_byte)
                            payload.append ("vps.io.%d.%s.traffic.write" % (vps_id, disk.xen_dev), ts, write_byte)
                            payload.append ("vps.io.%d.%s.util" % (vps_id, disk.xen_dev), ts, util)
            self.last_netflow = net_result
            self.last_diskstat = disk_result
            self.last_monitor_ts = ts
        except Exception, e:
            self.logger_misc.exception (e)
            return
        if payload.is_empty ():
            self.logger_misc.info ("no netflow data is to be sent")
            return
        if 'METRIC_SERVER' in dir(conf):
            try:
                send_data (conf.METRIC_SERVER, payload.serialize ())
                self.logger_misc.info ("monitor data sent")
            except Exception, e:
                self.logger_misc.exception ("cannot send monitor data: %s" % (str(e)))


    def run_once (self, cmd, vps_id, vps_info):
        if not vps_info:
            return False
        h = self.handlers.get (cmd)
        if callable (h):
            try:
                if self._try_lock_vps (cmd, vps_id):
                    h (self, vps_info)
                    self._unlock_vps (cmd, vps_id)
                    return True
                else:
                    return False
            except Exception, e:
                self.logger.exception ("vps %s, uncaught exception: %s" % (vps_info.id, str(e)))
                self.done_task (cmd, vps_id, False, "uncaught exception %s" % (str(e)))
                return False
        else:
            self.logger.warn ("no handler for cmd %s, vps: %s" % (str(cmd), self.dump_vps_info(vps_info)))
            self.done_task (cmd, vps_id, False, "not implemented")
            return False

    def run_loop (self, *cmds):
        self.logger.info ("worker for %s started" % (",".join (map (CMD._get_name, cmds))))
        while self.running:
            try:
                rpc = self.rpc_connect ()
                pending_jobs = []
                try:
                    for cmd in cmds: 
                        vps_id = rpc.todo (cmd)
                        self.logger_debug.info ("cmd:%s, vps_id:%s" % (CMD._get_name(cmd), vps_id))
                        if vps_id > 0:
                            vps_info = rpc.vps (vps_id)
                            if not self.vps_is_valid (vps_info):
                                self.logger.error ("invalid vps data received, cmd=%s, %s" % (CMD._get_name(cmd), self.dump_vps_info (vps_info)))
                                self.done_task(cmd, vps_id, False, "invalid vpsinfo")
                                vps_info = None
                            else:
                                pending_jobs.append((cmd, vps_id, vps_info))
                finally:
                    rpc.close ()
                for cmd, vps_id, vps_info in pending_jobs: 
                    if not self.running:
                        break
                    self.run_once (cmd, vps_id, vps_info)
            except (socket.error, RPC_Exception), e:
                self.logger_net.exception (e)
            except Exception, e:
                self.logger.exception ("uncaught exception: " + str(e))
            self.sleep (15) 
        self.logger.info ("worker for %s stop" % (",".join (map (CMD._get_name, cmds))))

    def doing (self, cmd, vps_id):
        try:
            rpc = self.rpc_connect()
            try:
                rpc.doing (cmd, vps_id)
                self.logger.info ("send doing cmd=%s vps_id=%s" % (CMD._get_name(cmd), vps_id))
            finally:
                rpc.close ()
        except Exception, e:
            self.logger_net.exception (e)

    def done_task (self, cmd, vps_id, is_ok, msg=''):
        state = 0
        if not is_ok:
            state = 1 
        try:
            rpc = self.rpc_connect()
            try:
                self.logger.info ("send done_task cmd=%s vps_id=%s" % (CMD._get_name (cmd), str(vps_id)))
                rpc.done (cmd, vps_id, state, msg)
            finally:
                rpc.close ()
        except Exception, e:
            self.logger_net.exception (e)

    @staticmethod
    def vps_is_valid (vps_info):
        try:
            if vps_info is None or vps_info.id <= 0:
                return None
            if not vps_info.harddisks or vps_info.harddisks.unwrap()[0] <= 0:
                return None
            if not vps_info.password:
                return None
            if not vps_info.cpu or not vps_info.ram:
                return None
            return vps_info
        except (IndexError, ValueError, KeyError):
            return None

    @staticmethod
    def vpsinfo_check_ip (vps_info):
        if vps_info.ext_ips and vps_info.gateway and is_host_ip(vps_info.gateway.ipv4):
            return vps_info
        return None


    @staticmethod
    def dump_vps_info (vps_info):
        ip = vps_info.ext_ips and "(%s)" % ",".join (map (lambda ip:"%s/%s(%s)" % (ip.ipv4, ip.ipv4_netmask, ip.mac), vps_info.ext_ips)) or None
        if vps_info.int_ip and vps_info.int_ip.ipv4:
            ip_inter = "%s/%s" % (vps_info.int_ip.ipv4, vps_info.int_ip.ipv4_netmask)
        else:
            ip_inter = None
        if vps_info.gateway and vps_info.gateway.ipv4:
            gateway = "%s/%s" % (vps_info.gateway.ipv4, vps_info.gateway.ipv4_netmask)
        else:
            gateway = None
        hd = vps_info.harddisks and "(%s)" % ",".join (map (lambda x: "%s:%s" % (x[0], x[1]), vps_info.harddisks.unwrap().items ())) or None
        if vps_info.state is not None:
            state = "%s(%s)" % (vps_info.state, VM_STATE_CN.get (vps_info.state))
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
                disk_g=root_size, root_pw=vps_info.password, gateway=vps_info.gateway and vps_info.gateway.ipv4 or 0)
        if vps_info.ext_ips:
            ip_dict = dict ()
            for ip in vps_info.ext_ips:
                ip_dict[ip.ipv4] = ip.ipv4_netmask
            xenvps.add_netinf_ext (ip_dict, mac=vps_info.ext_ips[0].mac, bandwidth=vps_info.bandwidth)
        ip_inner_dict = dict ()
        if vps_info.int_ip and vps_info.int_ip.ipv4:
            ip_inner_dict[vps_info.int_ip.ipv4] = vps_info.int_ip.ipv4_netmask
            xenvps.add_netinf_int (ip_inner_dict)
        if vps_info.harddisks:
            for disk_id, disk_size in vps_info.harddisks.unwrap ().iteritems ():
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
            if vps_info.state in [VM_STATE.PAY, VM_STATE.OPEN, VM_STATE.CLOSE]:
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
                msg = "vps%s state is %s(%s)" % (str(vps_id), vps_info.state, VM_STATE_CN[vps_info.state])
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

    def vps_reset_pw (self, vps_info):
        xv = XenVPS (vps_info.id)
        self.logger.info ("to reset passwd for vps %s" % (vps_info.id))
        try:
            self.setup_vps (xv, vps_info) 
            self.vpsops.reset_pw (xv)
        except Exception, e:
            self.logger.exception (e)
            self.done_task (CMD.RESET_PW, vps_info.id, False, "exception %s" % (str(e)))
            return
        self.done_task (CMD.RESET_PW, vps_info.id, True)
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

    def vps_hot_sync (self, vps_info):
        self.doing (CMD.PRE_SYNC, vps_info.id)
        return self._vps_hot_sync (vps_info.id)

    def _vps_hot_sync (self, vps_id, force=False, to_host_ip=None, speed=None):
        task = None
        try:
            task = self.query_migrate_task (vps_id)
            if task:
                if task.state != MIGRATE_STATE.TO_PRE_SYNC and task.state != MIGRATE_STATE.PRE_SYNCED and not force:
                    raise Exception ("task%s state is not TO_PRE_SYNC" % (task.id))
                to_host_ip = task.to_host_ip
                speed = task.speed
            elif not force and not to_host_ip:
                raise Exception ("no destination host ip for vps%s" % (vps_id))
            self.logger.info ("to pre sync vps%s to host %s" % (vps_id, to_host_ip))
            mgclient = MigrateClient (self.logger, to_host_ip)
            self.vpsops.hotsync_vps (mgclient, vps_id, to_host_ip, speed=speed)
        except Exception, e:
            print str(e)
            self.logger.exception (e)
            self.done_task (CMD.PRE_SYNC, vps_id, False, "exception %s" % (str(e)))
            return False
        self.done_task (CMD.PRE_SYNC, vps_id, True)
        return True

    def vps_migrate (self, vps_info):
        self.doing (CMD.MIGRATE, vps_info.id)
        return self._vps_migrate (vps_info.id)

    def _vps_migrate (self, vps_id, force=False, to_host_ip=None, speed=None):
        try:
            xv = self.vpsops.load_vps_meta (vps_id)
            task = self.query_migrate_task (vps_id)
            if task:
                if task.state != MIGRATE_STATE.TO_MIGRATE and task.state != MIGRATE_STATE.PRE_SYNCED and not force:
                    raise Exception ("task%s state is not TO_MIGRATE" % (task.id))
                to_host_ip = task.to_host_ip
                xv.gateway = task.new_gateway and task.new_gateway.ipv4 or None
                xv.vifs = dict ()
                if task.new_ext_ips:
                    ip_dict = dict ()
                    for ip in task.new_ext_ips:
                        ip_dict[ip.ipv4] = ip.ipv4_netmask
                    xv.add_netinf_ext (ip_dict, mac=task.new_ext_ips[0].mac, bandwidth=task.bandwidth)
                ip_inner_dict = dict ()
                if task.new_int_ip and task.new_int_ip.ipv4:
                    ip_inner_dict[task.new_int_ip.ipv4] = task.new_int_ip.ipv4_netmask
                    xv.add_netinf_int (ip_inner_dict)
                speed = task.speed
            elif not force and not to_host_ip:
                raise Exception ("no migrate task for vps%s" % (vps_id))
            migclient = MigrateClient (self.logger, to_host_ip)
            self.logger.info ("to migrate vps%s to host %s" % (vps_id, to_host_ip))
            self.vpsops.migrate_vps (migclient, vps_id, to_host_ip, xv=xv, speed=speed)
        except Exception, e:
            print str(e)
            self.logger.exception (e)
            self.done_task (CMD.MIGRATE, vps_id, False, "exception %s" % (str(e)))
            return False
        self.done_task (CMD.MIGRATE, vps_id, True)
        return True



    def query_vps (self, vps_id):
        rpc = self.rpc_connect()
        vps_info = None
        try:
            vps_info = rpc.vps (vps_id)
        finally:
            rpc.close ()
        if vps_info is None or vps_info.id <= 0:
            return None
        return vps_info

    def query_migrate_task (self, vps_id):
        task = None
        try:
            rpc = self.rpc_connect()
            try:
                task = rpc.migrate_task (vps_id)
            finally:
                rpc.close ()
        except Exception, e:
            self.logger.exception (e)
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
            rpc = self.rpc_connect()
            try:
                rpc.host_refresh (disk_remain, mem_remain, disk_total, mem_total)
                self.logger.info ("send host remain disk:%dG, mem:%dM, total disk:%dG, mem:%dM" % (disk_remain, mem_remain, disk_total, mem_total))
            finally:
                rpc.close ()
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
            if vps_info.state == VM_STATE.CLOSE or vps_info.host_id != self.host_id:
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

    def sleep (self, sec):
        for i in xrange (sec * 2):
            if self.running:
                time.sleep (0.5)
            
    def loop (self):
        while self.running:
            self.run_loop(CMD.BANDWIDTH) # because ovs db searching uses signal and can only work in main thread ...
            self.sleep (15)
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
            self.logger.info ("failed to start worker for cmd %s, %s" % (",".join (map (CMD._get_name, cmds)), str(e)))

    def start (self):
        if self.running:
            return
        self.running = True
        self.start_worker (CMD.OPEN, CMD.CLOSE, CMD.OS, CMD.REBOOT, CMD.RM, CMD.RESET_PW)
        self.start_worker (CMD.UPGRADE)
        self.start_worker (CMD.PRE_SYNC)
        self.start_worker (CMD.MIGRATE)
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


#!/usr/bin/env python
#coding:utf-8

import sys
import os
import conf
from conf import HOST_ID
import saas.const.vps as vps_const
from saas import VPS
from saas.ttypes import Cmd
from zthrift.client import get_client
from zkit.ip import int2ip 
from ops.vps import XenVPS
from ops.vps_ops import VPSOps
from lib.log import Log
import time
import re
import lib.daemon as daemon
import signal
import threading
from lib.timer_events import TimerEvents
import ops.netflow as netflow
from saas.ttypes import NetFlow

class VPSMgr (object):
    """ all exception should catch and log in this class """

    VERSION = 1

    def __init__ (self):
        self.logger = Log ("vps_mgr", config=conf)
        self.logger_misc = Log ("misc", config=conf) 
        self.host_id = HOST_ID
        self.handlers = {
            Cmd.OPEN: self.__class__.vps_open,
            Cmd.REBOOT: self.__class__.vps_reboot,
        }
        self.timer = TimerEvents (time.time, self.logger_misc)
        assert conf.NETFLOW_COLLECT_INV > 0
        self.timer.add_timer (conf.NETFLOW_COLLECT_INV, self.send_netflow)
        self.workers = []
        self.running = False

    def get_client (self):
        return get_client (VPS)

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
                netflow_list.append (NetFlow (vps_id, rx=v[0], tx=v[1]))
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
        vps = None
        try:
            trans, client = self.get_client ()
            trans.open ()
            try:
                vps_id = client.todo (self.host_id, cmd)
                print cmd, vps_id
                if vps_id > 0:
                    vps = client.vps (vps_id)
                    if not self.vps_is_valid (vps):
                        self.logger.error ("invalid vps data received, cmd=%s, vps_id=%s" % (cmd, vps_id))
                        self.done_task(cmd, vps_id, False, "invalid data")
                        vps = None
            finally:
                trans.close ()
        except Exception, e:
            self.logger.exception (e)
            return False
        if not vps:
            return False
        h = self.handlers.get (cmd)
        if callable (h):
            try:
                h (self, vps)
                return True
            except Exception, e:
                self.logger.exception ("vps %s, uncaught exception: %s" % (vps.id, str(e)))
                #TODO notify maintainments
                return False
        else:
            self.logger.warn ("no handler for cmd %s, vps: %s" % (str(cmd), self.dump_vps_info(vps)))
            self.done_task (cmd, vps_id, False, "not implemented")
            return False

    def run_loop (self, cmd):
        self.logger.info ("worker for %s started" % (str(cmd)))
        while self.running:
            try:
                if self.run_once (cmd):
                    continue
            except Exception, e:
                self.logger.exception ("uncaught exception: " + str(e))
            time.sleep (2)
        self.logger.info ("worker for %s stop" % (str(cmd)))

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
            self.logger.exception (e)

    @staticmethod
    def vps_is_valid (vps):
        return vps.id > 0 

    @staticmethod
    def dump_vps_info (vps):
        ip = vps.ipv4 is not None and int2ip (vps.ipv4) or None
        ip_inter = vps.ipv4_inter is not None  and int2ip (vps.ipv4_inter) or None
        netmask = vps.ipv4_netmask is not None and int2ip (vps.ipv4_netmask) or None
        gateway = vps.ipv4_gateway is not None and int2ip (vps.ipv4_gateway) or None
        return "host_id %s, id %s, state %s, os %s, cpu %s, ram %sM, hd %sG, ip %s, netmask %s, gateway %s, inter_ip:%s" % (vps.host_id, vps.id, vps.state, vps.os, vps.cpu, vps.ram, vps.hd, \
            ip, netmask, gateway, ip_inter
            )

    def setup_vps (self, xenvps, vps):
        xenvps.setup (os_id=vps.os, vcpu=vps.cpu, mem_m=vps.ram, disk_g=vps.hd, 
                ip=int2ip (vps.ipv4), 
                netmask=int2ip (vps.ipv4_netmask), 
                gateway=int2ip (vps.ipv4_gateway),
                root_pw=vps.password)


    def vps_open (self, vps, vps_image=None, is_new=True): 
        self.logger.info ("to open vps %s" % (vps.id))
        if vps.host_id != conf.HOST_ID:
            msg = "vpsopen : vps %s host_id=%s != current host %s , abort" % (vps.id, vps.host_id, conf.HOST_ID)
            self.logger.error (msg)
            self.done_task (Cmd.OPEN, vps.id, False, msg)
            return
        if not vps.ipv4 or not vps.ipv4_gateway or vps.cpu <= 0 or vps.ram <= 0 or vps.hd <= 0 or not vps.password:
            self.logger.error ("vps open: invalid vps data received: %s" % (self.dump_vps_info (vps)))
            self.done_task (Cmd.OPEN, vps.id, False, "invalid vps data")
            return
        xv = XenVPS (vps.id) 
        vpsops = VPSOps (self.logger)
        try:
            self.setup_vps (xv, vps)
            vpsops.create_vps (xv, vps_image, is_new)
        except Exception, e:
            self.logger.exception ("for %s: %s" % (str(vps.id), str(e)))
            self.done_task (Cmd.OPEN, vps.id, False, "error, " + str(e))
            return
        self.done_task (Cmd.OPEN, vps.id, True)

    def vps_reboot (self, vps):
        xv = XenVPS (vps.id) 
        self.logger.info ("to reboot vps %s" % (vps.id))
        vpsops = VPSOps (self.logger)
        try:
            self.setup_vps (xv, vps)
            vpsops.reboot_vps (xv)
        except Exception, e:
            self.logger.exception (e)
            self.done_task (Cmd.REBOOT, vps.id, False, "exception %s" % (str(e))) 
            return
        self.done_task (Cmd.REBOOT, vps.id, True)

    def query_vps (self, vps_id):
        trans, client = self.get_client ()
        trans.open ()
        vps = None
        try:
            vps = client.vps (vps_id)
        finally:
            trans.close ()
        if VPSMgr.vps_is_valid (vps):
            return vps
        return None


    def delete_vps (self, vps):
        """ must be run manually """
        try:
            assert vps.state == vps_const.VPS_STATE_RM
            vpsops = VPSOps (self.logger)
            xv = XenVPS (vps.id)
            vpsops.delete_vps (xv)
        except Exception, e:
            self.logger.exception (e)
            raise e

            
    def loop (self):
        while self.running:
            time.sleep (1)
        self.timer.stop () 
        self.logger.info ("timer stopped")
        while self.workers:
            th = self.workers.pop (0)
            th.join ()
        self.logger.info ("all stopped")

    def start (self):
        if self.running:
            return
        self.running = True
        for cmd in self.handlers.keys ():
            th = threading.Thread (target=self.run_loop, args=(cmd, ))
            try:
                th.setDaemon (1)
                th.start ()
                self.workers.append (th)
            except Exception, e:
                self.logger.info ("failed to start worker for cmd %s, %s" % (str(cmd), str(e)))
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

    if len (sys.argv) <= 1:
        usage ()
    else:
        log_dir = conf.log_dir
        if not os.path.exists (log_dir):
            os.makedirs (log_dir, 0700)
        run_dir = conf.RUN_DIR
        if not os.path.exists (run_dir):
            os.makedirs (run_dir, 0700)
        logger = Log ("vps_mgr", config=conf) # to ensure log is permitted to write
        os.chdir (run_dir)

        pid_file = "vps_mgr.pid"
        mon_pid_file = "vps_mgr_mon.pid"


        def _log_err (msg):
            print msg
            logger.error (msg, bt_level=1)

        def _start ():
            daemon.start (_main, pid_file, mon_pid_file, _log_err)

        def _stop ():
            daemon.stop (signal.SIGTERM, pid_file, mon_pid_file)

        action = sys.argv[1]
        if action == "start":
            _start ()
        elif action == "stop":
            _stop ()
        elif action == "restart":
            _stop ()
            time.sleep (2)
            _start ()
        elif action == "status":
            daemon.status (pid_file, mon_pid_file)
        elif action == "run":
            _main ()
        else:
            usage ()


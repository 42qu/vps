#!/usr/bin/env python
#coding:utf-8

import sys
import os
from conf import HOST_ID
import conf.vps_env as config

from saas import VPS
from saas.ttypes import Cmd
from zthrift.client import get_client

from ops.vps import XenVPS
from ops.vps_ops import VPSOps
from lib.log import Log
import time
import lib.daemon as daemon
import signal

class VPSMgr (object):

    VERSION = 1

    def __init__ (self):
        self.logger = Log ("vps_mgr", config=config)
        self.host_id = HOST_ID
        self.handler = {
            Cmd.OPEN: self.vps_open,
        }
        self.running = False

    def run_once (self):
        task = None
        vps = None
        try:
            trans, client = get_client (VPS)
            trans.open ()
            try:
                task = client.todo (self.host_id)
                cmd = task.cmd
                if cmd:
                    vps = client.vps (task.id)
            finally:
                trans.close ()
        except Exception, e:
            self.logger.exception (e)
        if not vps:
            return
        h = self.handler.get (task.cmd)
        if callable (h):
            h (task, vps)
        else:
            self.logger.error ("unregconized cmd %s" % (str(task.cmd)))
            return

    def done_task (self, task, is_ok, msg=''):
        state = 0
        if not is_ok:
            state = 1  #TODO need confirm
        trans, client = get_client (VPS)
        trans.open ()
        try:
            client.done (self.host_id, task, state, msg)
        finally:
            trans.close ()

    def vps_open (self, task, vps): 
        xv = XenVPS (vps.id) 
        vpsops = VPSOps (self.logger)
        try:
            xv.setup (os_id=vps.os, vcpu=vps.cpu, mem_m=vps.ram, disk_g=vps.hd, 
                    ip=vps.ipv4, netmask=vps.ipv4_netmask, gateway=vps.ipv4_gateway,
                    root_pw=vps.password)
            vpsops.create_vps (xv)
            xv.start ()
            self.done_task (task, True)
        except Exception, e:
            self.logger.exception (e)
            self.done_task (task, False, str(e))
            
    def loop (self):
        while self.running:
            self.run_once ()
            time.sleep (2)
        self.logger.info ("stopped")

    def start (self):
        if self.running:
            return
        self.logger.info ("start client")
        self.running = True

    def stop (self):
        if not self.running:
            return
        self.running = False
        self.logger.info ("stopping client")


def usage ():
    print "usage:\t%s star/stop/restart\t#manage forked daemon" % (sys.argv[0])
    print "\t%s run\t\t# run without daemon, for test purpose" % (sys.argv[0])
    print "\t%s once\t\t# run without daemon, try to get task only once" % (sys.argv[0])


stop_singal_flag = False
            
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


def _run_once ():
    client = VPSMgr ()
    client.run_once()

if __name__ == "__main__":
    log_dir = config.log_dir
    if not os.path.exists (log_dir):
        os.makedirs (log_dir, 0700)
    run_dir = config.run_dir
    if not os.path.exists (run_dir):
        os.makedirs (run_dir, 0700)
    logger = Log ("vps_mgr", config=config)
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

    if len (sys.argv) > 1:
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
        elif action == "once":
            _run_once ()
        else:
            usage ()
    else:
        usage ()


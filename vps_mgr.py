#!/usr/bin/env python
#coding:utf-8

import sys
import os
import conf
from conf import HOST_ID

from saas import VPS
from saas.ttypes import Cmd
from zthrift.client import get_client
from zkit.ip import int2ip 
from ops.vps import XenVPS
from ops.vps_ops import VPSOps
from lib.log import Log
import time
import lib.daemon as daemon
import signal
import threading

class VPSMgr (object):
    """ all exception should catch and log in this class """

    VERSION = 1

    def __init__ (self):
        self.logger = Log ("vps_mgr", config=conf)
        self.host_id = HOST_ID
        self.handlers = {
            Cmd.OPEN: self.__class__.vps_open,
            Cmd.REBOOT: self.__class__.vps_reboot,
        }
        self.workers = []
        self.running = False

    def run_once (self, cmd):
        vps_id = None
        vps = None
        try:
            trans, client = get_client (VPS)
            trans.open ()
            try:
                vps_id = client.todo (self.host_id, cmd)
                if vps_id > 0:
                    vps = client.vps (vps_id)
                    if not self.vps_is_valid (vps.id):
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
            time.sleep (1)
        self.logger.info ("worker for %s stop" % (str(cmd)))

    def done_task (self, cmd, vps_id, is_ok, msg=''):
        state = 0
        if not is_ok:
            state = 1 
        try:
            trans, client = get_client (VPS)
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
        return "id %s, state %s, os %s, cpu %s, ram %sM, hd %sG, ip %s, netmask %s, gateway %s, inter_ip:%s" % (vps.id, vps.state, vps.os, vps.cpu, vps.ram, vps.hd, \
            ip, netmask, gateway, ip_inter
            )


    def vps_open (self, vps): 
        if vps.state != 10:
            self.logger.error ("vps %s open cmd received while vps.state=%d, ignored" % (str(vps.id), vps.state))
            self.done_task (Cmd.OPEN, vps.id, False, "ignored")
            return
        if not vps.ipv4 or not vps.ipv4_gateway or vps.cpu <= 0 or vps.ram <= 0 or vps.hd <= 0 or not vps.password:
            self.logger.error ("invalid vps data received: %s" % (self.dump_vps_info (vps)))
            self.done_task (Cmd.OPEN, vps.id, False, "invalid vps data")
            return
        xv = XenVPS (vps.id) 
        vpsops = VPSOps (self.logger)
        try:
            xv.setup (os_id=vps.os, vcpu=vps.cpu, mem_m=vps.ram, disk_g=vps.hd, 
                    ip=int2ip (vps.ipv4), 
                    netmask=int2ip (vps.ipv4_netmask), 
                    gateway=int2ip (vps.ipv4_gateway),
                    root_pw=vps.password)
            vpsops.create_vps (xv)
        except Exception, e:
            self.logger.exception ("for %s: %s" % (str(vps.id), str(e)))
            self.done_task (Cmd.OPEN, vps.id, False, "error, " + str(e))
            return
        self.done_task (Cmd.OPEN, vps.id, True)

    def vps_reboot (self, vps):
        xv = XenVPS (vps.id) 
        if vps.id != 51:
            #TODO TEST
            self.done_task (Cmd.REBOOT, vps.id, False, "no testing for online vps")
            self.logger.warn ("not restart for online vps %s" % (vps.id))
            return
        try:
            xv.reboot ()
        except Exception, e:
            self.done_task (Cmd.REBOOT, vps.id, False, "exception %s" % (str(e))) 
            return
        if xv.wait_until_reachable ():
            self.done_task (Cmd.REBOOT, vps.id, True)
        else:
            self.done_task (Cmd.REBOOT, vps.id, False, "timeout")

    def query_vps (self, vps_id):
        trans, client = get_client (VPS)
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
        raise NotImplementedError ()
        try:
            assert vps.state == 0  # TODO hard code
            vpsops = VPSOps (self.logger)
            xv = XenVPS (vps.id)
            vpsops.delete_vps (xv)
        except Exception, e:
            self.logger.exception (e)
            raise e


            
    def loop (self):
        while self.running:
            time.sleep (1)
        while self.workers:
            th = self.workers.pop (0)
            th.join ()
        self.logger.info ("all stopped")

    def start (self):
        if self.running:
            return
        for cmd in self.handlers.keys ():
            th = threading.Thread (target=self.run_loop, args=(cmd, ))
            try:
                th.setDaemon (1)
                th.start ()
                self.workers.append (th)
            except Exception, e:
                self.logger.info ("failed to start worker for cmd %s, %s" % (str(cmd), str(e)))
        self.running = True

    def stop (self):
        if not self.running:
            return
        self.running = False
        self.logger.info ("stopping client")


def usage ():
    print "usage:\t%s star/stop/restart\t#manage forked daemon" % (sys.argv[0])
    print "\t%s run\t\t# run without daemon, for test purpose" % (sys.argv[0])
    os._exit (1)


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
    return


def delete_vps (vps_id):
    """ interact operation """
    vps_id = int (vps_id)
    client = VPSMgr ()
    vps = None
    try:
        vps = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state:" + type(e) + str(e)
        return
    if vps.state != 0: #TODO hard code
        print "vps %s state=%s, is not to be deleted" % (vps_id, vps.state)
        return
    if vps.host_id != conf.HOST_ID:
        print "vps %s host_id=%s != current host %s ?" % (vps.id, vps.host_id, conf.HOST_ID)
    answer = raw_input ('if confirm to delete vps %s, please type "CONFIRM" in uppercase:' % (vps_id))
    if answer != 'CONFIRM':
        print "aborted"
        return
    print "you have 10 second to regreat"
    time.sleep(10)
    print "begin"
    try:
        client.delete_vps (vps)
        print "done"
    except Exception, e:
        print type(e), e
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
        elif action == "delete_vps":
            if len (sys.argv) < 3:
                print "missing vps id"
                usage ()
            else:
                delete_vps (sys.argv[2])
        else:
            usage ()


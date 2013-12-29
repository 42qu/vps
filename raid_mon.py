#!/usr/bin/env python
# coding:utf-8

import os
import sys
import conf
from lib.log import Log
import signal
import time
import subprocess
from vps_mgr import VPSMgr
import lib.daemon as daemon
import socket

class RaidMonitor(object):

    def __init__(self):
        self.logger = Log("raid_mon", config=conf)
        self.is_running = False
        self.last_state = True
        self.vps_mgr = VPSMgr()
        self.hostname = socket.gethostname()

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.logger.info("started")

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False

    def send_alarm(self, msg):
        rpc = self.vps_mgr.rpc_connect()
        try:
            rpc.alarm("%s: %s" % (self.hostname, msg))
        finally:
            rpc.close()

    def check(self):
        cmd = """MegaCli64 -pdlist -aall | grep -i 'firmware state:' | grep -P -v -i "online|Unconfigured\(good\) """
        try:
            out, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            msg = out + err
            if msg:
                self.logger.error(msg)
                if self.last_state:
                    self.last_state = False
                    self.send_alarm("error")
                    self.logger.error("alarm sent")
            else:
                self.logger.info("ok")
                if not self.last_state:
                    self.send_alarm("ok")
                    self.last_state = True
        except Exception, e:
            self.logger.exception(e)

    def loop(self):
        while self.is_running:
            time.sleep(30)
            self.check()

stop_signal_flag = False

def _main():
    prog = RaidMonitor()

    def exit_sig_handler(sig_num, frm):
        global stop_signal_flag
        if stop_signal_flag:
            return
        stop_signal_flag = True
        prog.stop()
        return
    prog.start()
    signal.signal(signal.SIGTERM, exit_sig_handler)
    signal.signal(signal.SIGINT, exit_sig_handler)
    prog.loop()
    return


def usage():
    print "usage:\t%s star/stop/restart\t#manage forked daemon" % (sys.argv[0])
    print "\t%s run\t\t# run without daemon, for test purpose" % (sys.argv[0])
    os._exit(1)


if __name__ == "__main__":

    logger = Log("daemon", config=conf)  # to ensure log is permitted to write
    pid_file = "raid_mon.pid"
    mon_pid_file = "raid_mon_mon.pid"

    if len(sys.argv) <= 1:
        usage()
    else:
        action = sys.argv[1]
        daemon.cmd_wrapper(action, _main, usage, logger,
                           conf.log_dir, "/tmp", pid_file, mon_pid_file)





# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

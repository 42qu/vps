#!/usr/bin/env python
# coding:utf-8

import os
import sys
import conf
from lib.log import Log
import lib.daemon as daemon
from lib.job_queue import JobQueue
from lib.alarm import EmailAlarm, AlarmJob
import time
import signal
from ops.saas_rpc import SAAS_Client, CMD
import socket

# you need to checkout https://bitbucket.org/zsp042/private.git into conf/

class SaasMonitor (object):

    def __init__ (self):
        self.is_running = False
        self.hostname = socket.gethostname ()
        self.logger = Log ("saas_mon", config=conf)
        self.recover_thres = conf.SAAS_RECOVER_THRESHOLD or (30 * 5)
        self.bad_thres = conf.SAAS_BAD_THRESHOLD or 5
        self.alarm_q = JobQueue (self.logger)
        self.emailalarm = EmailAlarm (self.logger)
        self.last_state = True

    def start (self):
        if self.is_running:
            return
        self.is_running = True
        self.alarm_q.start_worker (1)
        self.logger.info ("started")

    def stop (self):
        if not self.is_running:
            return
        self.is_running = False
        self.alarm_q.stop ()
        self.logger.info ("stopped")

    def check (self):
        vps = None
        try:
            rpc = SAAS_Client (self.logger)
            rpc.connect ()
            try:
                _id = rpc.todo (0, CMD.MONITOR)
            finally:
                rpc.close ()
            self.logger.info ("ok")
            return True
        except Exception, e:
            self.logger.exception (e)
            return False

    def _alarm_enqueue (self, state, bad_count=0):
        t = "%Y-%m-%d %H:%M:%S"
        ts = "[%s]" % (time.strftime (t, time.localtime()))
        text = None
        if state:
            text = "from %s to saas server recovered" % (self.hostname)
        else:
            text = "from %s to saas server bad (try %s)" % (self.hostname, bad_count)
        job = AlarmJob (self.emailalarm, ts + text)
        self.alarm_q.put_job (job)

        
    def loop (self):
        bad_count = 0
        recover_count = 0
        while self.is_running:
            time.sleep(2)
            if self.check (): 
                if self.last_state:
                    bad_count = 0
                    recover_count = 0
                else:
                    bad_count += 1
                    recover_count += 1
            else:
                bad_count += 1
                recover_count = 0
            if recover_count > 0 and recover_count == self.recover_thres:
                bad_count = 0
                self.last_state = True
                self._alarm_enqueue (True)
            elif bad_count > 0 and bad_count == self.bad_thres:
                self.last_state = False
                self._alarm_enqueue (False, bad_count)
        
            

stop_signal_flag = False

def _main():
    prog = SaasMonitor ()

    def exit_sig_handler (sig_num, frm):
        global stop_signal_flag
        if stop_signal_flag:
            return
        stop_signal_flag = True
        prog.stop ()
        return
    prog.start ()
    signal.signal (signal.SIGTERM, exit_sig_handler)
    signal.signal (signal.SIGINT, exit_sig_handler)
    prog.loop ()
    return

def usage ():
    print "usage:\t%s star/stop/restart\t#manage forked daemon" % (sys.argv[0])
    print "\t%s run\t\t# run without daemon, for test purpose" % (sys.argv[0])
    os._exit (1)


if __name__ == "__main__":

    logger = Log ("daemon", config=conf) # to ensure log is permitted to write
    pid_file = "saas_mon.pid"
    mon_pid_file = "saas_mon_mon.pid"

    if len (sys.argv) <= 1:
        usage ()
    else:
        action = sys.argv[1]
        daemon.cmd_wrapper (action, _main, usage, logger, conf.log_dir, "/tmp", pid_file, mon_pid_file)




# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

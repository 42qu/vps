#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

import sys
import os
import signal
from ops.migrate import MigrateServer
import lib.daemon as daemon
from lib.log import Log
import conf

stop_signal_flag = False

def main():
    logger = Log ("migrate", config=conf)
    migsvr = MigrateServer (logger)
    def exit_sig_handler (sig_num, frm):
        global stop_signal_flag
        if stop_signal_flag:
            return
        stop_signal_flag = True
        migsvr.stop ()
        return

    migsvr.start ()
    signal.signal (signal.SIGTERM, exit_sig_handler)
    signal.signal (signal.SIGINT, exit_sig_handler)
    migsvr.loop ()
    return

def usage ():
    print "usage:\t%s star/stop/restart\t#manage forked daemon" % (sys.argv[0])
    print "\t%s run\t\t# run without daemon, for test purpose" % (sys.argv[0])
    os._exit (1)



if "__main__" == __name__:
    if len (sys.argv) <= 1:
        usage ()
    else:
        logger = Log ("daemon", config=conf) # to ensure log is permitted to write
        pid_file = "migrate_svr.pid"
        mon_pid_file = "migrate_svr_mon.pid"
        action = sys.argv[1]
        daemon.cmd_wrapper (action, main, usage, logger, conf.log_dir, conf.RUN_DIR, pid_file, mon_pid_file)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import _env
import conf
from vps_mgr import VPSMgr
from saas.ttypes import Cmd
from lib.log import Log
import time
from zkit.ip import int2ip 

def vps_open_mock (self, vps):
    print self.dump_vps_info (vps)
    if int (time.time ()) % 2:
        print "true"
        self.done_task (Cmd.OPEN, vps.id, True)
    else:
        print "false"
        self.done_task (Cmd.OPEN, vps.id, False)

def main ():
    log_dir = conf.log_dir
    if not os.path.exists (log_dir):
        os.makedirs (log_dir, 0700)
    run_dir = conf.run_dir
    if not os.path.exists (run_dir):
        os.makedirs (run_dir, 0700)
    os.chdir (run_dir)
    vps = VPSMgr ()
    vps.handlers = dict ()
    vps.handlers[Cmd.OPEN] = vps_open_mock
    vps.start ()
    vps.loop ()

    
if "__main__" == __name__:
    main ()


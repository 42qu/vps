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

def vps_open_mock (self, task, vps):
    print "id", vps.id, "os", vps.os, "cpu", vps.cpu, "ram", vps.ram, "hd", vps.hd, \
        "ip", int2ip (vps.ipv4), "netmask", int2ip (vps.ipv4_netmask), "gateway", int2ip (vps.ipv4_gateway), \
        "pw", vps.password
    if int (time.time ()) % 2:
        print "true"
        self.done_task (task, True)
    else:
        print "false"
        self.done_task (task, False)

def main ():
    log_dir = conf.log_dir
    if not os.path.exists (log_dir):
        os.makedirs (log_dir, 0700)
    run_dir = conf.run_dir
    if not os.path.exists (run_dir):
        os.makedirs (run_dir, 0700)
    logger = Log ("vps_mgr", config=conf)
    os.chdir (run_dir)
    vps = VPSMgr ()
    vps.handler[Cmd.OPEN] = vps_open_mock
    vps.run_once ()

    
if "__main__" == __name__:
    main ()


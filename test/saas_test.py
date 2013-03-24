#!/usr/bin/env python

import os
import sys
import _env
import conf
from vps_mgr import VPSMgr
import time
from ops.saas_rpc import SAAS_Client, CMD
import unittest
import conf

class TestSAASClient (unittest.TestCase):

    def setUp (self):
        self.m = VPSMgr ()
        self.rpc = SAAS_Client (self.m.logger)

    def test_invalid (self):
        self.rpc.connect ()
        print "connected"
        try:
            vps = self.rpc.vps (0)
            print VPSMgr.dump_vps_info (vps)
            self.assert_ (not VPSMgr.vps_is_valid (vps))
            vps = self.rpc.vps (100000000)
            print VPSMgr.dump_vps_info (vps)
            self.assert_ (not VPSMgr.vps_is_valid (vps))
        finally:
            self.rpc.close ()

    def test_done (self):
        m = VPSMgr ()
        m.done_task (CMD.OPEN, 4, True)

    def test_migrate_task (self):
        m = VPSMgr ()
        task = m.query_migrate_task (1030)
        print task
#        print task.id, task.to_host_ip, task.to_host_id , task.speed, task.bandwidth

if __name__ == '__main__':
    runner = unittest.TextTestRunner ()
#    runner.run (TestSAASClient ("test_invalid"))
    #runner.run (TestSAASClient ("test_state"))
    runner.run (TestSAASClient ("test_migrate_task"))
    #runner.run (TestSAASClient ("test_done"))
    #runner.run (TestSAASClient ("test_netflow"))

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

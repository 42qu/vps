#!/usr/bin/env python
# coding:utf-8
import _env
import unittest
from ops.carbon_client import CarbonPayload, send_data
import time

class TestCarbonClient (unittest.TestCase):

    def test_1 (self):
        payload = CarbonPayload ()
        payload.append ("vps.netflow.%d.in"%(1), time.time (), 1*1024 * 1024)
        send_data (("127.0.0.1", 2004), payload.serialize ())

if __name__ == '__main__':
    unittest.main ()


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

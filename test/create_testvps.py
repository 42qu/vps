#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import _env
import conf
from ops.vps import XenVPS
from ops.vps_ops import VPSOps
import ops.os_image as os_image
import unittest
from lib.log import Log

class TestVPSCreate (unittest.TestCase):

    def test_find_image (self):
        image_path, os_type, version = os_image.find_os_image (50001)
        self.assert_ (os.path.exists (image_path))

    def test_mem_too_big (self):
        vps = XenVPS (0)
        logger = Log ("test", config=conf)
        vps.setup (os_id=50001, vcpu=1, mem_m=500000, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
        try:
            vps.check_resource_avail ()
        except Exception, e:
            logger.exception (e)
            print "exception caught", type (e), str(e)
            return
        self.fail ("expected exception not thrown")


    def test_vps0 (self):
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        vps = XenVPS (0)
        vps.setup (os_id=50002, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
        print vps.gen_xenpv_config ()
        vpsops.create_vps (vps)

    def test_delete_vps0 (self):
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        vps = XenVPS (0)
        vpsops.delete_vps (vps)

def main():
    runner = unittest.TextTestRunner ()
#    runner.run (TestVPSCreate ("test_find_image"))
#    runner.run (TestVPSCreate ("test_mem_too_big"))
#    runner.run (TestVPSCreate ("test_vps0"))
    runner.run (TestVPSCreate ("test_delete_vps0"))


    



if "__main__" == __name__:
    main()



#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import _env
import conf
from ops.vps import XenVPS
from ops.vps_ops import VPSOps
import ops.os_image as os_image
import ops.vps_common as vps_common
import unittest
from lib.log import Log
import time

class TestVPSCreate (unittest.TestCase):

    def test_find_image (self):
        image_path, os_type, version = os_image.find_os_image (50001)
        self.assert_ (os.path.exists (image_path))

    def test_create_vps0 (self):
        print "create vps00"
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        vps = XenVPS (0)
        try:
            vps.setup (os_id=20001, vcpu=1, mem_m=512, disk_g=7, root_pw="fdfdfdsss", gateway="113.11.199.1")
            vps.add_netinf_ext ({"113.11.199.18": "255.255.255.0"})
            vps.add_netinf_int ({"10.10.2.20": '255.255.255.0'})
            #vps.add_extra_storage (disk_id=1, size_g=1, fs_type='ext3')
            #vps.add_extra_storage (disk_id=2, size_g=0.5, fs_type='ext4')
            #vps.setup (os_id=10001, vcpu=1, mem_m=512, disk_g=7, root_pw="fdfdfd")
            #vps.setup (os_id=10002, vcpu=1, mem_m=512, disk_g=7, root_pw="fdfdfd")
            #vps.setup (os_id=30001, vcpu=1, mem_m=512, disk_g=7, root_pw="root")
            #vps.setup (os_id=1, vcpu=1, mem_m=512, disk_g=7,  root_pw="fdfdfd")
            #vps.setup (os_id=10000, vcpu=1, mem_m=512, disk_g=7, root_pw="fdfdfd")
            #vps.setup (os_id=20001, vcpu=1, mem_m=512, disk_g=7, root_pw="fdfdfd")
            #vps.setup (os_id=10003, vcpu=1, mem_m=512, disk_g=7, root_pw="fdfdfd")
            #vps.setup (os_id=20001, vcpu=1, mem_m=512, disk_g=7, root_pw="fdfdfd")

            print vps.gen_xenpv_config ()
            #vpsops.create_vps (vps, vps_image='/data/vps/images/arch-2011.08.19-i386-fs-ext3.tar.gz')
            vpsops.create_vps (vps)
        except Exception, e:
            print str(e)
            logger.exception (e)
            raise e
        self.assert_ (vps.is_running ())
        print "vps00 started"


    def test_ssh (self):
        from ops.vps_common import call_cmd_via_ssh
        status, out, err = call_cmd_via_ssh ("10.10.2.2", user="root", password="fdfdfd", cmd="free|grep Swap")
        self.assertEqual(status, 0)
        print out
#
#
#    def test_multiple (self):
#        print "create vps00"
#        logger = Log ("test", config=conf)
#        vpsops = VPSOps (logger)
#        for i in xrange (1, 33):
#            vps = XenVPS (i)
#            try:
#                vps.setup (os_id=50001, vcpu=1, mem_m=1024, disk_g=7, root_pw="fdfdfd", gateway="113.11.199.1")
#                vps.add_netinf_ext ({"113.11.199.%d" % (i + 20) : "255.255.255.0"})
#                print vps.gen_xenpv_config ()
#                vpsops.create_vps (vps)
#            except Exception, e:
#                print str(e)
#                logger.exception (e)
#                raise e
#            self.assert_ (vps.is_running ())

#    def test_destroy_multiple (self):
#        print "destory multiple"
#        logger = Log ("test", config=conf)
#        vpsops = VPSOps (logger)
#        for i in xrange (1,33):
#            vps = XenVPS (i)
#            vpsops.delete_vps (vps)
#        print "done"
        



def main():
    runner = unittest.TextTestRunner ()
#    runner.run (TestVPSCreate ("test_find_image"))
    runner.run (TestVPSCreate ("test_create_vps0"))
#    runner.run (TestVPSCreate ("test_reboot00"))
#    runner.run (TestVPSCreate ("test_multiple"))
#    runner.run (TestVPSCreate ("test_destroy_multiple"))
#    runner.run (TestVPSCreate ("test_ssh"))
    

    



if "__main__" == __name__:
    main()



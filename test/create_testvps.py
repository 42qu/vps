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

#    def test_vps08 (self): 
#        logger = Log ("test", config=conf)
#        vpsops = VPSOps (logger)
#        vps = XenVPS (8)
#        vps.setup (os_id=50001, vcpu=2, mem_m=2048, disk_g=50, ip="113.11.199.20", netmask="255.255.255.0", gateway="113.11.199.1", root_pw="fda")
#        vpsops.alloc_space_n_config (vps)
        
    def test_create_vps0 (self):
        print "create vps00"
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        vps = XenVPS (0)
        try:
            vps.setup (os_id=10003, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.add_extra_storage (disk_id=1, size_g=1, fs_type='ext3')
            #vps.add_extra_storage (disk_id=2, size_g=0.5, fs_type='ext4')
            #vps.setup (os_id=10001, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=10002, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=30001, vcpu=1, mem_m=512, disk_g=7, ip="10.10.2.2", netmask="255.255.255.0", gateway="10.10.2.1", root_pw="root")
            #vps.setup (os_id=1, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=10000, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=20001, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=10003, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=20001, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")

            print vps.gen_xenpv_config ()
            #vpsops.create_vps (vps, vps_image='/data/vps/images/arch-2011.08.19-i386-fs-ext3.tar.gz')
            vpsops.create_vps (vps)
        except Exception, e:
            print str(e)
            logger.exception (e)
            raise e
        self.assert_ (vps.is_running ())
        print "vps00 started"


    def test_vps0 (self):
        print "create vps00"
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        vps = XenVPS (0)
        try:
            #vps.setup (os_id=50001, vcpu=1, mem_m=512, disk_g=7, ip="113.11.199.3", netmask="255.255.255.0", gateway="113.11.199.1", root_pw="fdfdfd")
            vps.setup (os_id=10001, vcpu=1, mem_m=512, disk_g=7, ip="10.10.2.2", netmask="255.255.255.0", gateway="10.10.2.1", root_pw="fdfdfd")
            vps.add_extra_storage (disk_id=1, size_g=1, fs_type='ext3')
            #vps.setup (os_id=10002, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=2, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=1, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=10000, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=20001, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=10003, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            #vps.setup (os_id=20001, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")
            print vps.gen_xenpv_config ()
            vpsops.create_vps (vps)
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (vps.is_running ())
        print "vps00 started"
        try:
            print "test check resources again, expect ip not available"
            vps.check_resource_avail ()
        except Exception, e:
            print "expected exception caught: %s" % (e)
        print  "now test shutting it down"
        vps.stop ()
        self.assert_ (not vps.is_running ())

        try:
            print "test reopen without moving to trash"
            vpsops.reopen_vps (vps)
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (vps.is_running ())
        try:
            print "close vps0"
            vpsops.close_vps (vps)
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (not vps.is_running ())
        self.assert_ (vps.root_store.trash_exists ())
        self.assert_ (vps.data_disks['xvdc1'].trash_exists ())
        self.assert_ (not vps.root_store.exists ())
        try:
            print "reopen vps0"
            vpsops.reopen_vps (vps)
            status, out, err = vps_common.call_cmd_via_ssh (vps.ip, user="root", password=vps.root_pw, cmd="free|grep Swap")
            if status == 0:
                if vps.swap_store.size_g > 0:
                    swap_size = int (out.split ()[1])
                    if swap_size == 0:
                        raise Exception ("it seems swap has not properly configured, please check") 
            else:
                self.fail ("ssh test failed %s, %s" % (out, err))
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (vps.is_running ())
        self.assert_ (vps.root_store.exists ())
        self.assert_ (vps.data_disks['xvdc1'].exists ())
        try:
            print "delete vps0"
            vpsops.delete_vps (vps)
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (not vps.root_store.exists ())
        self.assert_ (not os.path.exists (vps.config_path))
        self.assert_ (not os.path.exists (vps.auto_config_path))
        self.assert_ (not vps.data_disks['xvdc1'].exists ())
        try:
            print "reopen vps0 == create vps0"
            vpsops.reopen_vps (vps)
            self.assert_ (vps.is_running ())
            self.assert_ (vps.root_store.exists ())
            self.assert_ (vps.data_disks['xvdc1'].exists ())
            print "close vps0"
            vpsops.close_vps (vps)
            print "delete vps0"
            vpsops.delete_vps (vps)
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (not vps.root_store.exists ())
        self.assert_ (not os.path.exists (vps.config_path))
        self.assert_ (not os.path.exists (vps.auto_config_path))


    def test_closevps0 (self):
        print "test_closevps0"
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        vps = XenVPS (0)
        vpsops.close_vps (vps)
    
    def test_reopen0 (self):
        print "test reopen"
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        vps = XenVPS (0)
        vps.setup (os_id=10001, vcpu=1, mem_m=512, disk_g=7, ip="10.10.1.2", netmask="255.255.255.0", gateway="10.10.1.1", root_pw="fdfdfd")



    def test_delete_vps0 (self):
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        vps = XenVPS (0)
        print "going to delete %s in 10 sec" % (vps.name)
        time.sleep(10)
        vpsops.delete_vps (vps)

    def test_ssh (self):
        from ops.vps_common import call_cmd_via_ssh
        status, out, err = call_cmd_via_ssh ("10.10.1.2", user="root", password="fdfdfd", cmd="free|grep Swap")
        self.assertEqual(status, 0)
        print out

    def test_reboot00 (self):
        print "test reboot vps00"
        logger = Log ("test", config=conf)
        vps = XenVPS (0)
        vps.setup (os_id=10003, vcpu=1, mem_m=512, disk_g=7, ip="113.11.199.3", netmask="255.255.255.0", gateway="113.11.199.1", root_pw="fdfdfd")
        vpsops = VPSOps (logger)
        vpsops.reboot_vps (vps)
        print "reboot ok"

#    def test_multiple (self):
#        print "create vps00"
#        logger = Log ("test", config=conf)
#        vpsops = VPSOps (logger)
#        for i in xrange (1, 33):
#            vps = XenVPS (i)
#            try:
#                vps.setup (os_id=50001, vcpu=1, mem_m=1024, disk_g=7, ip="113.11.199.%d" % (i + 20), netmask="255.255.255.0", gateway="113.11.199.1", root_pw="fdfdfd")
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
#    runner.run (TestVPSCreate ("test_mem_too_big"))
#    runner.run (TestVPSCreate ("test_vps0"))
    runner.run (TestVPSCreate ("test_create_vps0"))
#    runner.run (TestVPSCreate ("test_closevps0"))
#    runner.run (TestVPSCreate ("test_reopen0"))
#    runner.run (TestVPSCreate ("test_reboot00"))
#    runner.run (TestVPSCreate ("test_multiple"))
#    runner.run (TestVPSCreate ("test_destroy_multiple"))
#    runner.run (TestVPSCreate ("test_delete_vps0"))
#    runner.run (TestVPSCreate ("test_ssh"))
    

    



if "__main__" == __name__:
    main()



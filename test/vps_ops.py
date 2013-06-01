#!/usr/bin/env python

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
import datetime

class TestVPSOPS (unittest.TestCase):

    def test_meta (self):
        print "test vps meta"
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        vps = XenVPS (0)
        vps.setup (os_id=50001, vcpu=1, mem_m=500000, disk_g=7, root_pw="fdfdfd", gateway="10.10.1.1")
        vps.add_extra_storage (disk_id=1, size_g=1, fs_type='ext3')
        vps.add_netinf_ext ({"10.10.1.2": "255.255.255.0"})
        vps.add_netinf_int ({"10.10.3.2": '255.255.255.0'})
#        vps.data_disks['xvdc1']._set_expire_days (1)
#        print "trash_date", vps.data_disks['xvdc1'].trash_date
#        print "expire_date", vps.data_disks['xvdc1'].expire_date
        vpsops.save_vps_meta (vps)
        _vps = vpsops.load_vps_meta (0)
        self.assertEqual (_vps.vps_id, vps.vps_id)
        self.assertEqual (_vps.os_id, vps.os_id)
        self.assertEqual (_vps.vcpu, vps.vcpu)
        self.assertEqual (_vps.mem_m, vps.mem_m)
        self.assertEqual (_vps.ip, vps.ip)
        self.assertEqual (_vps.netmask, vps.netmask)
        self.assertEqual (_vps.gateway, vps.gateway)
        self.assertEqual (_vps.root_store.size_g, vps.root_store.size_g)
        self.assertEqual (_vps.swap_store.size_g, vps.swap_store.size_g)
        self.assertEqual (_vps.data_disks['xvdc1'].size_g, 1)
        self.assertEqual (_vps.data_disks['xvdc1'].fs_type, 'ext3')
        self.assertEqual (_vps.data_disks['xvdc1'].mount_point, '/mnt/data1')
        self.assertEqual (_vps.data_disks['xvdc1'].xen_dev, 'xvdc1')
#        self.assertEqual (_vps.data_disks['xvdc1'].trash_date, vps.data_disks['xvdc1'].trash_date)
#        self.assertEqual (_vps.data_disks['xvdc1'].expire_date, vps.data_disks['xvdc1'].expire_date)
        print _vps.data_disks['xvdc1'].__class__.__name__
        self.assertEqual (len (_vps.vifs.values ()), 2)
        self.assertEqual (_vps.vifs['vps00int'].ip_dict, {'10.10.3.2': '255.255.255.0'})
        self.assertEqual (_vps.vifs['vps00int'].mac, vps.vifs['vps00int'].mac)
        self.assertEqual (_vps.vifs['vps00int'].mac, vps.vif_int.mac)
        self.assertEqual (_vps.vifs['vps00'].mac, vps.vif_ext.mac)
#        print "test trash expire date None"
#        vps.data_disks['xvdc1']._set_expire_days (None)
#        self.assertEqual (vps.data_disks['xvdc1'].trash_date, None)
#        self.assertEqual (vps.data_disks['xvdc1'].expire_date, None)
#        vpsops.save_vps_meta (vps)
#        _vps = vpsops.load_vps_meta (0)
#        self.assertEqual (_vps.data_disks['xvdc1'].trash_date, None)
#        self.assertEqual (_vps.data_disks['xvdc1'].expire_date, None)


    def test_mem_too_big (self):
        print "test mem too big"
        vps = XenVPS (0)
        logger = Log ("test", config=conf)
        vps.setup (os_id=50001, vcpu=1, mem_m=500000, disk_g=7, root_pw="fdfdfd", gateway="10.10.1.1")
        vps.add_netinf_ext ({"10.10.1.2": "255.255.255.0"})
        try:
            vps.check_resource_avail ()
        except Exception, e:
            logger.exception (e)
            print "exception caught", type (e), str(e)
            return
        self.fail ("expected exception not thrown")

    def test_vps0 (self):
        print "create vps00"
        logger = Log ("test", config=conf)
        vpsops = VPSOps (logger)
        xv = XenVPS (0)
        try:
            xv.setup (os_id=10001, vcpu=1, mem_m=512, disk_g=7, root_pw="fdfdfd", gateway="10.10.2.1")
            xv.add_extra_storage (disk_id=1, size_g=1, fs_type='ext3')
            xv.add_netinf_ext ({"10.10.2.2": "255.255.255.0"})
            print xv.gen_xenpv_config ()
            vpsops.create_vps (xv)
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (xv.is_running ())
        self.assert_ (xv.root_store.trash_date is None)
        try:
            logger.debug ("test check resources again, expect ip not available")
            xv.check_resource_avail ()
        except Exception, e:
            logger.debug ("expected exception caught: %s" % (e))
        try:
            logger.debug ("close vps0")
            vpsops.close_vps (xv.vps_id, xv)
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (not xv.is_running ())
        self.assert_ (xv.root_store.trash_exists ())
        self.assert_ (xv.data_disks['xvdc1'].trash_exists ())
        self.assert_ (not xv.root_store.exists ())
        self.assert_ (vpsops.is_trash_exists (xv.vps_id))
        try:
            logger.debug ("reopen vps0")
            vpsops.reopen_vps (xv.vps_id, xv)
            status, out, err = vps_common.call_cmd_via_ssh (xv.ip, user="root", password=xv.root_pw, cmd="free|grep Swap")
            if status == 0:
                if xv.swap_store.size_g > 0:
                    swap_size = int (out.split ()[1])
                    if swap_size == 0:
                        raise Exception ("it seems swap has not properly configured, please check") 
            else:
                self.fail ("ssh test failed %s, %s" % (out, err))
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (xv.is_running ())
        self.assert_ (xv.root_store.exists ())
        self.assert_ (xv.data_disks['xvdc1'].exists ())
        logger.debug ("shutting it down")
        xv.stop ()
        self.assert_ (not xv.is_running ())

        try:
            logger.debug ("test is_normal_exists without moving to trash")
            self.assert_ (vpsops.is_normal_exists (xv.vps_id))
        except Exception, e:
            logger.exception (e)
            raise e
        try:
            logger.debug ("delete vps0")
            vpsops.delete_vps (xv.vps_id, xv)
        except Exception, e:
            logger.exception (e)
            raise e
        self.assert_ (not xv.root_store.exists ())
        self.assert_ (not os.path.exists (xv.config_path))
        self.assert_ (not os.path.exists (xv.auto_config_path))
        self.assert_ (not xv.data_disks['xvdc1'].exists ())


def main():
    runner = unittest.TextTestRunner ()
    runner.run (TestVPSOPS ("test_meta"))
#    runner.run (TestVPSOPS ("test_mem_too_big"))
    runner.run (TestVPSOPS ("test_vps0"))


if "__main__" == __name__:
    main()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

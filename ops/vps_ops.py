#!/usr/bin/env python

import _env
import conf
assert conf.mkfs_cmd

import os
import re

import vps_common
from vps import XenVPS

from os_init import os_init

class VPSOps (object):

    def __init__ (self, logger):
        self.logger = logger

    def loginfo (self, vps, msg):
        message = "[%s] %s" % (vps.name, msg)
        if not self.logger:
            print message
        else:
            self.logger.info (message)

    def create_vps (self, vps):

        assert isinstance (vps, XenVPS)
        assert vps.has_all_attr
        vps.check_resource_avail ()

        self.loginfo (vps, "begin to create image")
        vps_common.create_raw_image (vps.img_path, vps.disk_g, conf.mkfs_cmd)
        self.loginfo (vps, "image %s created" % (vps.img_path))

        vps_common.create_raw_image (vps.swp_path, vps.swp_g, "/sbin/mkswap")
        self.loginfo (vps, "swap image %s created" % (vps.swp_path))
        
        vps_mountpoint = vps_common.mount_loop_tmp (vps.img_path)
        self.loginfo (vps, "mounted vps image %s" % (vps.img_path))

        try:
            if re.match (r'.*\.img$', vps.template_image):
                vps_common.sync_img (vps_mountpoint, vps.template_image)
            else:
                vps_common.unpack_tarball (vps_mountpoint, vps.template_image)
            self.loginfo (vps, "syned vps os to %s" % (vps.img_path))
            
            self.loginfo (vps, "begin to init os")
            os_init (vps, vps_mountpoint)
            self.loginfo (vps, "done init os")
        finally:
            vps_common.umount_tmp (vps_mountpoint)
        xen_config = vps.gen_xenpv_config ()
        f = open (vps.config_path, 'w')
        try:
            f.write (xen_config)
        finally:
            f.close ()
        self.loginfo ("%s created" % (vps.config_path))
        #TODO make link to xen auto 

    def delete_vps (self, vps):
        raise NotImplementedError ()
        


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

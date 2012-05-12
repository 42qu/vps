#!/usr/bin/env python

import os
import vps_common
import conf
assert conf.MKFS_CMD

class VPSStoreBase (object):

    xen_path = None

    def create (self, disk_g):
        raise NotImplementedError ()

    def delete (self):
        raise NotImplementedError ()

    def exists (self):
        raise NotImplementedError ()

    def mount_tmp (self, readonly=False):
        """ return mountpoint """
        raise NotImplementedError ()


class VPSStoreFile (VPSStoreBase):

    filepath = None

    def __init__ (self, filepath):
        self.filepath = filepath
        self.xen_path = "file:" + filepath

    def __str__ (self):
        return self.filepath

    def exists (self):
        return os.path.isfile (self.filepath)

    def delete (self):
        #TODO check whether in use !!!!!!!!!
        os.remove (self.filepath)

    def mount_tmp (self, readonly=False):
        return vps_common.mount_loop_tmp (self.filepath, readonly)


class VPSStoreLV (VPSStoreBase):

    dev = None

    def __init__ (self, vg_name, lv_name):
        self.lv_name = lv_name
        self.vg_name = vg_name
        self.dev = "/dev/%s/%s" % (self.vg_name, self.lv_name)
        self.xen_path = "phy:" + self.dev

    def __str__ (self):
        return self.dev
        
    def exists (self):
        return os.path.exists (self.dev)

    def delete (self):
        #TODO check whether in use !!!!!!!!!
        vps_common.lv_delete (self.dev)

    def mount_tmp (self, readonly=False):
        return vps_common.mount_partition_tmp (self.dev, readonly)


    
class VPSRootImage (VPSStoreFile):

    def __init__ (self, img_dir, vps_name):
        VPSStoreFile.__init__ (self, os.path.join (img_dir, vps_name + ".img"))

    def create (self, disk_g):
        vps_common.create_raw_image (self.filepath, disk_g, conf.MKFS_CMD, sparse=True)

class VPSSwapImage (VPSStoreFile):

    def __init__ (self, swap_dir, vps_name):
        VPSStoreFile.__init__ (self, os.path.join (swap_dir, vps_name + ".img"))

    def create (self, swap_g):
        vps_common.create_raw_image (self.filepath, swap_g, "/sbin/mkswap")


class VPSRootLV (VPSStoreLV):

    def __init__ (self, vg_name, vps_name):
        VPSStoreLV.__init__ (self, vg_name, "%s_root" % (vps_name))

    def create (self, size_g):
        vps_common.lv_create (self.vg_name, self.lv_name, size_g, conf.MKFS_CMD)

class VPSSwapLV (VPSStoreLV):

    def __init__ (self, vg_name, vps_name):
        VPSStoreLV.__init__ (self, vg_name, "%s_swap" % (vps_name))

    def create (self, size_g):
        vps_common.lv_create (self.vg_name, self.lv_name, size_g, "/sbin/mkswap")




# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

#!/usr/bin/env python

import os
import vps_common
import shutil

class VPSStoreBase (object):

    xen_dev = None
    size_g = None
    xen_path = None
    fs_type = None
    
    def __init__ (self, xen_dev, xen_path, fs_type, mount_point, size_g):
        self.size_g = size_g
        self.fs_type = fs_type
        self.xen_dev = xen_dev
        self.xen_path = xen_path
        self.mount_point = mount_point


    def create (self, fs_type=None):
        raise NotImplementedError ()

    def delete (self):
        raise NotImplementedError ()

    def exists (self):
        raise NotImplementedError ()

    def mount_tmp (self, readonly=False):
        """ return mountpoint """
        raise NotImplementedError ()

    def dump_trash (self):
        raise NotImplementedError ()

    def restore_from_trash (self):
        raise NotImplementedError ()

    
class VPSStoreImage (VPSStoreBase):

    file_path = None
    trash_path = None

    def __init__ (self, xen_dev, img_dir, trash_dir, img_name, fs_type=None, mount_point=None, size_g=None):
        self.file_path = os.path.join (img_dir, img_name)
        self.trash_path = os.path.join (trash_dir, img_name)
        xen_path = "file:" + self.file_path
        VPSStoreBase.__init__ (self, xen_dev, xen_path, fs_type, mount_point, size_g)

    def __str__ (self):
        return self.file_path


    def exists (self):
        return os.path.isfile (self.file_path)

    def trash_exists (self):
        return os.path.isfile (self.trash_path)


    def create (self, fs_type=None):
        if not self.size_g:
            return
        vps_common.create_raw_image (self.file_path, self.size_g, sparse=True)
        if not self.fs_type:
            self.fs_type = fs_type
        assert self.fs_type
        vps_common.format_fs (self.fs_type, self.file_path)


    def delete (self):
        #TODO check whether in use !!!!!!!!!
        if os.path.exists (self.file_path):
            os.remove (self.file_path)
        if os.path.exists (self.trash_path):
            os.remove (self.trash_path)

    def mount_tmp (self, readonly=False):
        return vps_common.mount_loop_tmp (self.file_path, readonly)

    def dump_trash (self):
        if not os.path.exists (self.file_path):
            return
        if os.path.exists (self.trash_path):
            os.remove (self.trash_path)
        shutil.move (self.file_path, self.trash_path)

    def restore_from_trash (self):
        shutil.move (self.trash_path, self.file_path)



class VPSStoreLV (VPSStoreBase):

    dev = None
    trash_dev = None
    lv_name = None
    vg_name = None

    def __init__ (self, xen_dev, vg_name, lv_name, fs_type=None, mount_point=None, size_g=None):
        self.lv_name = lv_name
        self.vg_name = vg_name
        self.fs_type = fs_type
        self.dev = "/dev/%s/%s" % (self.vg_name, self.lv_name)
        self.trash_dev = "/dev/%s/trash_%s" % (self.vg_name, self.lv_name)
        xen_path = "phy:" + self.dev
        VPSStoreBase.__init__ (self, xen_dev, xen_path, fs_type, mount_point, size_g)

    def __str__ (self):
        return self.dev

    def create (self, fs_type=None):
        if not self.size_g:
            return
        vps_common.lv_create (self.vg_name, self.lv_name, self.size_g)
        if not self.fs_type:
            self.fs_type = fs_type
        assert self.fs_type
        vps_common.format_fs (self.fs_type, self.dev)
        
    def exists (self):
        return os.path.exists (self.dev)

    def trash_exists (self):
        return os.path.exists (self.trash_dev)

    def dump_trash (self):
        if not os.path.exists (self.dev):
            return
        if os.path.exists (self.trash_dev):
            vps_common.lv_delete (self.trash_dev)
        vps_common.lv_rename (self.dev, self.trash_dev)

    def restore_from_trash (self):
        vps_common.lv_rename (self.trash_dev, self.dev)


    def delete (self):
        #TODO check whether in use !!!!!!!!!
        if os.path.exists (self.dev):
            vps_common.lv_delete (self.dev)
        if os.path.exists (self.trash_dev):
            vps_common.lv_delete (self.trash_dev)

    def mount_tmp (self, readonly=False):
        return vps_common.mount_partition_tmp (self.dev, readonly)






# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

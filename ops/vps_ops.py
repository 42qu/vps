#!/usr/bin/env python

import _env

import os
import re
import time

import vps_common
from vps import XenVPS
import conf
assert conf.DEFAULT_FS_TYPE
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

    def _create_xen_config (self, vps):
        """ will override config """
        xen_config = vps.gen_xenpv_config ()
        f = open (vps.config_path, 'w')
        try:
            f.write (xen_config)
            self.loginfo (vps, "%s created" % (vps.config_path))
        finally:
            f.close ()
        vps.create_autolink ()
        self.loginfo (vps, "created link to xen auto")
    
    def _boot_and_test (self, vps, is_new=True):
        self.loginfo (vps, "booting")
        status = None
        out = None
        err = None
        vps.start ()
        if not vps.wait_until_reachable (60):
            raise Exception ("the vps started, seems not reachable")
        if is_new:
            self.loginfo (vps, "started and reachable, wait for ssh connection")
            time.sleep (5)
            status, out, err = vps_common.call_cmd_via_ssh (vps.ip, user="root", password=vps.root_pw, cmd="free|grep Swap")
            self.loginfo (vps, "ssh login ok")
            if status == 0:
                if vps.swp_g > 0:
                    swap_size = int (out.split ()[1])
                    if swap_size == 0:
                        raise Exception ("it seems swap has not properly configured, please check") 
                    self.loginfo (vps, "checked swap size is %d" % (swap_size))
            else:
                raise Exception ("cmd 'free' on via returns %s %s" % (out, err))
        else: # if it's recoverd os, passwd is likely to be changed by user
            self.loginfo (vps, "started and reachable")


    def create_vps (self, vps, vps_image=None, is_new=True):
        """ check resources, create vps, wait for ip reachable, check ssh loging and check swap of vps.
            on error raise Exception, the caller should log exception """
        assert isinstance (vps, XenVPS)
        assert vps.has_all_attr
        
        if vps_image:
            vps.template_image = vps_image
        vps.check_resource_avail ()

        #fs_type is tied to the image
        fs_type = vps_common.get_fs_from_tarball_name (vps.template_image)
        if not fs_type:
            fs_type = conf.DEFAULT_FS_TYPE
        
        self.loginfo (vps, "begin to create image")
        vps.root_store.create (vps.disk_g, fs_type)
        self.loginfo (vps, "%s created" % (str(vps.root_store)))
        
        if vps.swp_g > 0:
            vps.swap_store.create (vps.swp_g, 'swap')
            self.loginfo (vps, "swap image %s created" % (str(vps.swap_store)))

        self._create_xen_config (vps)

        vps_mountpoint = vps.root_store.mount_tmp ()
        self.loginfo (vps, "mounted vps image %s" % (str(vps.root_store)))
    
        try:
            if re.match (r'.*\.img$', vps.template_image):
                vps_common.sync_img (vps_mountpoint, vps.template_image)
            else:
                vps_common.unpack_tarball (vps_mountpoint, vps.template_image)
            self.loginfo (vps, "synced vps os to %s" % (str(vps.root_store)))
            
            self.loginfo (vps, "begin to init os")
            os_init (vps, vps_mountpoint, to_init_passwd=is_new)
            self.loginfo (vps, "done init os")
        finally:
            vps_common.umount_tmp (vps_mountpoint)
        
        self._boot_and_test (vps, is_new=is_new)
        self.loginfo (vps, "done vps creation")

    def close_vps (self, vps):
        if vps.stop ():
            self.loginfo (vps, "vps stopped, going to move data to trash")
        else:
            vps.destroy ()
            self.loginfo (vps, "vps cannot shutdown, destroyed it, going to delete data")
        if vps.root_store.exists ():
            vps.root_store.dump_trash ()
            self.loginfo (vps, "%s moved to trash" % (str(vps.root_store)))
        if vps.swap_store.exists ():
            vps.swap_store.delete ()
            self.loginfo (vps, "deleted %s" % (str(vps.swap_store)))
        if os.path.exists (vps.config_path):
            os.remove (vps.config_path)
            self.loginfo (vps, "deleted %s" % (vps.config_path))
        if os.path.exists (vps.auto_config_path):
            os.remove (vps.auto_config_path)
            self.loginfo (vps, "deleted %s" % (vps.auto_config_path))


    def reopen_vps (self, vps):
        assert isinstance (vps, XenVPS)
        assert vps.has_all_attr
        if not vps.root_store.trash_exists () and not vps.root_store.exists ():
            self.loginfo (vps, "not trash found for root partition, cleanup first and create it")
            self.delete_vps (vps)
            return self.create_vps (vps)
        else:
            vps.check_resource_avail (ignore_trash=True) 
            # TODO if resource not available on this host, we must allow moving the vps elsewhere
            if vps.root_store.trash_exists ():
                vps.root_store.restore_from_trash ()
                self.loginfo (vps, "%s restored from trash" % (str (vps.root_store))) 
            else:
                assert vps.root_store.exists ()
            if vps.swap_store.exists ():
                pass
            elif vps.swap_store.trash_exists ():
                vps.swap_store.restore_from_trash () 
                self.loginfo (vps, "%s restored from trash" % (str (vps.swap_store)))
            elif vps.swp_g > 0:
                vps.swap_store.create (vps.swp_g, 'swap')
                self.loginfo (vps, "swap image %s created" % (str(vps.swap_store)))
            self._create_xen_config (vps)
            self._boot_and_test (vps, is_new=False)
            self.loginfo (vps, "done vps creation")




    def delete_vps (self, vps):
        if vps.stop ():
            self.loginfo (vps, "vps stopped, going to delete data")
        else:
            vps.destroy ()
            self.loginfo (vps, "vps cannot shutdown, destroyed it, going to delete data")
        if vps.root_store.exists ():
            vps.root_store.delete ()
            self.loginfo (vps, "deleted %s" % (str(vps.root_store)))
        if vps.swap_store.exists ():
            vps.swap_store.delete ()
            self.loginfo (vps, "deleted %s" % (str(vps.swap_store)))
        if os.path.exists (vps.config_path):
            os.remove (vps.config_path)
            self.loginfo (vps, "deleted %s" % (vps.config_path))
        if os.path.exists (vps.auto_config_path):
            os.remove (vps.auto_config_path)
            self.loginfo (vps, "deleted %s" % (vps.auto_config_path))
        self.loginfo (vps, "deleted")

    def reboot_vps (self, vps):
        if vps.stop ():
            self.loginfo (vps, "stopped")
        else:
            vps.destroy ()
            self.loginfo (vps, "force destroy")
        vps.start ()
        if not vps.wait_until_reachable (60):
            raise Exception ("the vps started, seems not reachable")
        self.loginfo (vps, "started")





# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

#!/usr/bin/env python


import os
import re
import time
import socket
try:
    import json
except ImportError:
    import simplejson as json
import ops.vps_common as vps_common
import ops.os_image as os_image
from ops.vps import XenVPS
import ops.os_init as os_init

import ops._env
import conf
from lib.command import call_cmd

assert conf.DEFAULT_FS_TYPE
assert conf.VPS_METADATA_DIR
assert conf.CLOSE_EXPIRE_DAYS


class VPSOps (object):

    def __init__ (self, logger):
        self.logger = logger

    def loginfo (self, vps, msg):
        message = "[%s] %s" % (vps.name, msg)
        if not self.logger:
            print message
        else:
            self.logger.info (message)

    def create_xen_config (self, vps):
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

    @staticmethod
    def _meta_path (vps_id, is_trash=False, is_deleted=False):
        if not os.path.isdir (conf.VPS_METADATA_DIR):
            raise Exception ("directory %s is not exists" % (conf.VPS_METADATA_DIR))
        filename = "vps%d.json" % (vps_id)
        if is_trash:
            filename += ".trash"
        if is_deleted:
            filename += ".delete"
        return os.path.join (conf.VPS_METADATA_DIR, filename)

    def _load_vps_meta (self, meta_path):
        f = open (meta_path, "r")
        data = None
        try:
            data = json.load (f)
        finally:
            f.close ()
        xv = XenVPS.from_meta (data)
        return xv

    def load_vps_meta (self, vps_id, is_trash=False):
        meta_path = self._meta_path (vps_id, is_trash=is_trash)
        return self._load_vps_meta (meta_path)

    def save_vps_meta (self, vps, is_trash=False, is_deleted=False, override=True):
        assert isinstance (vps, XenVPS)
        data = vps.to_meta ()
        if data is None:
            raise Exception ("error in XenVPS.to_meta ()")
        meta_path = self._meta_path (vps.vps_id, is_trash=is_trash, is_deleted=is_deleted)
        if os.path.exists (meta_path) and override is False:
            return
        f = open (meta_path, "w")
        try:
            json.dump (data, f, indent=2, sort_keys=True)
        finally:
            f.close ()
        self.loginfo (vps, "meta saved to %s" % (meta_path))
        
    
    def _boot_and_test (self, vps, is_new=True):
        assert isinstance (vps, XenVPS)
        self.loginfo (vps, "booting")
        status = None
        out = None
        err = None
        vps.start ()
        if not vps.wait_until_reachable (60):
            raise Exception ("the vps started, seems not reachable")
        if is_new:
            _e = None
            for i in xrange (0, 5):
                self.loginfo (vps, "started and reachable, wait for ssh connection")
                time.sleep (5)
                try:
                    status, out, err = vps_common.call_cmd_via_ssh (vps.ip, user="root", password=vps.root_pw, cmd="free|grep Swap")
                    self.loginfo (vps, "ssh login ok")
                    if status == 0:
                        if vps.swap_store.size_g > 0:
                            swap_size = int (out.split ()[1])
                            if swap_size == 0:
                                raise Exception ("it seems swap has not properly configured, please check") 
                            self.loginfo (vps, "checked swap size is %d" % (swap_size))
                    else:
                        raise Exception ("cmd 'free' on via returns %s %s" % (out, err))
                    return
                except socket.error, e:
                    _e = e
                    continue
            if _e:
                raise _e
        else: # if it's recoverd os, passwd is likely to be changed by user
            self.loginfo (vps, "started and reachable")


    def create_vps (self, vps, vps_image=None, is_new=True):
        """ check resources, create vps, wait for ip reachable, check ssh loging and check swap of vps.
            on error raise Exception, the caller should log exception """
        assert isinstance (vps, XenVPS)
        assert vps.has_all_attr
        
        _vps_image, os_type, os_version = os_image.find_os_image (vps.os_id)
        if not vps_image:
            vps_image = _vps_image
        if not vps_image:
            raise Exception ("no template image configured for os_type=%s, os_id=%s" % (os_type, vps.os_id))
        if not os.path.exists (vps_image):
            raise Exception ("image %s not exists" % (vps_image))

        vps.check_resource_avail ()

        #fs_type is tied to the image
        fs_type = vps_common.get_fs_from_tarball_name (vps_image)
        if not fs_type:
            fs_type = conf.DEFAULT_FS_TYPE

        self.loginfo (vps, "begin to create image")
        if vps.swap_store.size_g > 0:
            vps.swap_store.create ()
        vps.root_store.fs_type = fs_type
        for disk in vps.data_disks.values ():
            disk.create ()
            self.loginfo (vps, "%s created" % (str(disk)))

        self.create_xen_config (vps)

        vps_mountpoint = vps.root_store.mount_tmp ()
        self.loginfo (vps, "mounted vps image %s" % (str(vps.root_store)))
    
        try:
            if re.match (r'.*\.img$', vps_image):
                vps_common.sync_img (vps_mountpoint, vps_image)
            else:
                vps_common.unpack_tarball (vps_mountpoint, vps_image)
            self.loginfo (vps, "synced vps os to %s" % (str(vps.root_store)))
            
            self.loginfo (vps, "begin to init os")
            os_init.os_init (vps, vps_mountpoint, os_type, os_version, to_init_passwd=is_new)
            self.loginfo (vps, "done init os")
        finally:
            vps_common.umount_tmp (vps_mountpoint)
        
        self.save_vps_meta (vps)
        self._boot_and_test (vps, is_new=is_new)
        self.loginfo (vps, "done vps creation")

    def close_vps (self, vps_id, _vps=None):
        meta_path = self._meta_path (vps_id, is_trash=False)
        if os.path.exists (meta_path):
            vps = self._load_vps_meta (meta_path)
            self.loginfo (vps, "loaded %s" % (meta_path))
        elif _vps:
            vps = _vps
        else:
            raise Exception ("missing metadata or backend data")
        if vps.stop ():
            self.loginfo (vps, "vps stopped")
        else:
            vps.destroy ()
            self.loginfo (vps, "vps cannot shutdown, destroyed it")
        for disk in vps.data_disks.values ():
            if disk.exists ():
                disk.dump_trash (conf.CLOSE_EXPIRE_DAYS)
                self.loginfo (vps, "%s moved to trash" % (str(disk)))
        if vps.swap_store.exists ():
            vps.swap_store.delete ()
            self.loginfo (vps, "deleted %s" % (str(vps.swap_store)))
        if os.path.islink (vps.auto_config_path): 
            os.remove (vps.auto_config_path)
            self.loginfo (vps, "deleted %s" % (vps.auto_config_path))
        if os.path.exists (vps.config_path):
            os.remove (vps.config_path)
            self.loginfo (vps, "deleted %s" % (vps.config_path))
        if os.path.exists (meta_path):
            os.remove (meta_path)
            self.loginfo (vps, "removed %s" % (meta_path))
        self.save_vps_meta (vps, is_trash=True)
        self.loginfo (vps, "closed")


    def reopen_vps (self, vps_id, _vps=None):
        meta_path = self._meta_path (vps_id)
        trash_meta_path = self._meta_path (vps_id, is_trash=True)
        if os.path.exists (trash_meta_path):
            vps = self._load_vps_meta (trash_meta_path)
            self.loginfo (vps, "loaded %s" % (trash_meta_path))
        elif os.path.exists (meta_path):
            vps = self._load_vps_meta (meta_path)
            self.loginfo (vps, "seems vps was not closed")
            vps.check_storage_integrity ()
            vps.check_xen_config ()
            if not vps.is_running ():
                self._boot_and_test (vps, is_new=False)
            return
        elif _vps:
            vps = _vps
        else:
            raise Exception ("missing metadata or backend data")

        vps.check_resource_avail (ignore_trash=True)
        # TODO if resource not available on this host, we must allow moving the vps elsewhere
        for disk in vps.data_disks.values ():
            if disk.trash_exists ():
                disk.restore_from_trash ()
                self.loginfo (vps, "%s restored from trash" % (str(disk)))
            elif not disk.exists ():
                raise Exception ("%s missing" % (str(disk)))
        if vps.swap_store.trash_exists ():
            vps.swap_store.restore_from_trash ()
            self.loginfo (vps, "%s restored from trash" % (str (vps.swap_store)))
        elif vps.swap_store.size_g > 0:
            vps.swap_store.create ()
            self.loginfo (vps, "swap image %s created" % (str(vps.swap_store)))

        vps.check_storage_integrity ()
        self.create_xen_config (vps)

        if os.path.exists (trash_meta_path):
            os.remove (trash_meta_path)
            self.loginfo (vps, "removed %s" % (trash_meta_path))
        self.save_vps_meta (vps)

        self._boot_and_test (vps, is_new=False)

        self.loginfo (vps, "done vps creation")

        
    def delete_vps (self, vps_id, _vps=None):
        meta_path = self._meta_path (vps_id)
        trash_meta_path = self._meta_path (vps_id, is_trash=True)
        if os.path.exists (meta_path):
            vps = self._load_vps_meta (meta_path)
            self.loginfo (vps, "loaded %s" % (meta_path))
        elif os.path.exists (trash_meta_path):
            vps = self._load_vps_meta (trash_meta_path)
            self.loginfo (vps, "loaded %s" % (trash_meta_path))
        elif _vps:
            vps = _vps
        else:
            raise Exception ("missing metadata or backend data")
        if vps.stop ():
            self.loginfo (vps, "vps stopped, going to delete data")
        else:
            vps.destroy ()
            self.loginfo (vps, "vps cannot shutdown, destroyed it, going to delete data")
        for disk in vps.data_disks.values ():
            disk.delete ()
            self.loginfo (vps, "deleted %s" % (str(disk)))
        for disk in vps.trash_disks.values ():
            disk.delete ()
            self.loginfo (vps, "deleted %s" % (str(disk)))
        vps.swap_store.delete ()
        self.loginfo (vps, "deleted %s" % (str(vps.swap_store)))
        if os.path.exists (vps.config_path):
            os.remove (vps.config_path)
            self.loginfo (vps, "deleted %s" % (vps.config_path))
        if os.path.exists (vps.auto_config_path):
            os.remove (vps.auto_config_path)
            self.loginfo (vps, "deleted %s" % (vps.auto_config_path))
        if os.path.exists (meta_path):
            os.remove (meta_path)
            self.loginfo (vps, "removed %s" % (meta_path))
        if os.path.exists (trash_meta_path):
            os.remove (trash_meta_path)
            self.loginfo (vps, "removed %s" % (trash_meta_path))
            self.save_vps_meta (vps, is_trash=True, is_deleted=True)
        else:
            self.save_vps_meta (vps, is_trash=False, is_deleted=True)
        self.loginfo (vps, "deleted")

    def reboot_vps (self, vps):
        assert vps.has_all_attr
        if vps.stop ():
            self.loginfo (vps, "stopped")
        else:
            vps.destroy ()
            self.loginfo (vps, "force destroy")
        vps.start ()
        if not vps.wait_until_reachable (60):
            raise Exception ("the vps started, seems not reachable")
        self.loginfo (vps, "started")

    def upgrade_vps (self, vps_new):
        assert vps_new.has_all_attr
        vps_id = vps_new.vps_id
        meta_path = self._meta_path (vps_id, is_trash=False)
        vps = self._load_vps_meta (meta_path)

        vps.os_id = vps_new.os_id
        _vps_image, os_type, os_version = os_image.find_os_image (vps_new.os_id)
        vps.vcpu = vps_new.vcpu
        vps.mem_m = vps_new.mem_m

        if vps.stop ():
            self.loginfo (vps, "stopped")
        else:
            vps.destroy ()
            self.loginfo (vps, "force destroy")
        root_store_trash = vps.root_store
        if vps.ip != vps_new.ip:
            # just in case when ip changed
            vps.add_netinf (vps.name, vps_new.ip, vps_new.netmask, vps.xen_bridge)
        
        vps.renew_root_storage (new_size=vps_new.root_store.size_g)

        vps_mountpoint_bak = root_store_trash.mount_trash_temp ()
        self.loginfo (vps, "mounted vps old root %s" % (str(root_store_trash)))
        try:
            fs_type = vps_common.get_partition_fs_type (mount_point=vps_mountpoint_bak)
            vps.root_store.create (fs_type)
            self.loginfo (vps, "create new root")
            vps_mountpoint = vps.root_store.mount_tmp ()
            self.loginfo (vps, "mounted vps new root %s" % (str(vps.root_store)))
        
            try:
                call_cmd ("rsync -a '%s/' '%s/'" % (vps_mountpoint_bak, vps_mountpoint))
                self.loginfo (vps, "synced old root to new root")
                # TODO:  uncomment this when os_init can deal with multiple net address
                #self.loginfo (vps, "begin to init os")
                #os_init.os_init (vps, vps_mountpoint, os_type, os_version, to_init_passwd=False)
                #self.loginfo (vps, "done init os")
            finally:
                vps_common.umount_tmp (vps_mountpoint)
        finally:
            vps_common.umount_tmp (vps_mountpoint_bak)
        
        self.save_vps_meta (vps)
        self.create_xen_config (vps)
        self._boot_and_test (vps, is_new=False)
        self.loginfo (vps, "done vps upgrade")



    def reinstall_os (self, vps_id, _vps=None, os_id=None, vps_image=None):
        meta_path = self._meta_path (vps_id, is_trash=False)
        vps = None
        if os.path.exists (meta_path):
            vps = self._load_vps_meta (meta_path)
            if _vps: 
                vps.os_id = _vps.os_id
            elif os_id:
                vps.os_id = os_id
            else:
                raise Exception ("missing os_id")
        else:
            raise Exception ("missing vps metadata")
        _vps_image, os_type, os_version = os_image.find_os_image (vps.os_id)
        if not vps_image:
            vps_image = _vps_image
        if not vps_image:
            raise Exception ("no template image configured for os_type=%s, os_id=%s" % (os_type, vps.os_id))
        if not os.path.exists (vps_image):
            raise Exception ("image %s not exists" % (vps_image))
        #fs_type is tied to the image
        fs_type = vps_common.get_fs_from_tarball_name (vps_image)
        if not fs_type:
            fs_type = conf.DEFAULT_FS_TYPE

        assert vps.has_all_attr
        if vps.stop ():
            self.loginfo (vps, "stopped")
        else:
            vps.destroy ()
            self.loginfo (vps, "force destroy")
        root_store_trash = vps.root_store
        vps.renew_root_storage (5)
        vps.root_store.create (fs_type)
        self.loginfo (vps, "create new root")

        vps_mountpoint_bak = root_store_trash.mount_trash_temp ()
        try:
            vps_mountpoint = vps.root_store.mount_tmp ()
            self.loginfo (vps, "mounted vps image %s" % (str(vps.root_store)))
        
            try:
                if re.match (r'.*\.img$', vps_image):
                    vps_common.sync_img (vps_mountpoint, vps_image)
                else:
                    vps_common.unpack_tarball (vps_mountpoint, vps_image)
                self.loginfo (vps, "synced vps os to %s" % (str(vps.root_store)))
                
                for sync_dir in ['home', 'root']:
                    dir_org = os.path.join (vps_mountpoint_bak, sync_dir)
                    dir_now = os.path.join (vps_mountpoint, sync_dir)
                    if os.path.exists (dir_org):
                        call_cmd ("rsync -a --exclude='.bash*'  '%s/' '%s/'" % (dir_org, dir_now))
                        self.loginfo (vps, "sync dir /%s to new os" % (sync_dir))

                self.loginfo (vps, "begin to init os")
                if _vps:
                    vps.root_pw = _vps.root_pw
                    os_init.os_init (vps, vps_mountpoint, os_type, os_version, to_init_passwd=True)
                else: # if no user data provided from backend
                    os_init.os_init (vps, vps_mountpoint, os_type, os_version, to_init_passwd=False)
                    os_init.migrate_users (vps, vps_mountpoint, vps_mountpoint_bak)
                self.loginfo (vps, "done init os")
            finally:
                vps_common.umount_tmp (vps_mountpoint)
        finally:
            vps_common.umount_tmp (vps_mountpoint_bak)
        
        self.save_vps_meta (vps)
        self._boot_and_test (vps, is_new=False)
        self.loginfo (vps, "done vps reinstall")

    def set_vif_int (self, vps_id, ip, netmask):
        # if run again, vif's MAC is the same with previous one
        meta_path = self._meta_path (vps_id, is_trash=False)
        vps = None
        if os.path.exists (meta_path):
            vps = self._load_vps_meta (meta_path)
        else:
            raise Exception ("cannot find meta data for vps %s" % (vps_id))
        vifname = "%sint" % (vps.name)
        mac = None
        is_ip_available = not vps_common.ping (ip)
        if vps.has_netinf (vifname):
            self.loginfo (vps, "removing existing vif %s" % (vifname))
            mac = vps.vifs[vifname].mac
            p_ip = vps.vifs[vifname].mac
            if p_ip == ip and not is_ip_available:
                self.loginfo (vps, "no need to change vif %s, ip is the same" % (vifname))
                return False
            if not is_ip_available:
                raise Exception ("ip %s is in use" % (ip))
            vps_common.xm_network_detach (vps.name, mac)
            vps.del_netinf (vifname)
        elif not is_ip_available:
            raise Exception ("ip %s is in use" % (ip))

        vif = vps.add_netinf_int (vifname, ip, netmask, mac)
        vps_common.xm_network_attach (vps.name, vifname, vif.mac, ip, vif.bridge)
        self.save_vps_meta (vps)
        self.create_xen_config (vps)
        self.loginfo (vps, "added internal vif ip=%s" % (ip))
        return True



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

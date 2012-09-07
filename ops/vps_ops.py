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

    def loginfo (self, xv, msg):
        message = "[%s] %s" % (xv.name, msg)
        if not self.logger:
            print message
        else:
            self.logger.info (message)

    def create_xen_config (self, xv):
        """ will override config """
        xen_config = xv.gen_xenpv_config ()
        f = open (xv.config_path, 'w')
        try:
            f.write (xen_config)
            self.loginfo (xv, "%s created" % (xv.config_path))
        finally:
            f.close ()
        xv.create_autolink ()
        self.loginfo (xv, "created link to xen auto")

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
        try:
            xv = XenVPS.from_meta (data)
            return xv
        except Exception, e:
            raise Exception ("file=%s, %s" % (meta_path, str(e)))

    def load_vps_meta (self, vps_id, is_trash=False):
        meta_path = self._meta_path (vps_id, is_trash=is_trash)
        return self._load_vps_meta (meta_path)

    def save_vps_meta (self, xv, is_trash=False, is_deleted=False, override=True):
        assert isinstance (xv, XenVPS)
        data = xv.to_meta ()
        if data is None:
            raise Exception ("error in XenVPS.to_meta ()")
        meta_path = self._meta_path (xv.vps_id, is_trash=is_trash, is_deleted=is_deleted)
        if os.path.exists (meta_path) and override is False:
            return
        f = open (meta_path, "w")
        try:
            json.dump (data, f, indent=2, sort_keys=True)
        finally:
            f.close ()
        self.loginfo (xv, "meta saved to %s" % (meta_path))
        
    
    def _boot_and_test (self, xv, is_new=True):
        assert isinstance (xv, XenVPS)
        self.loginfo (xv, "booting")
        status = None
        out = None
        err = None
        xv.start ()
        if not xv.wait_until_reachable (120):
            raise Exception ("the vps started, seems not reachable")
        if is_new:
            _e = None
            for i in xrange (0, 5):
                self.loginfo (xv, "started and reachable, wait for ssh connection")
                time.sleep (5)
                try:
                    status, out, err = vps_common.call_cmd_via_ssh (xv.ip, user="root", password=xv.root_pw, cmd="free|grep Swap")
                    self.loginfo (xv, "ssh login ok")
                    if status == 0:
                        if xv.swap_store.size_g > 0:
                            swap_size = int (out.split ()[1])
                            if swap_size == 0:
                                raise Exception ("it seems swap has not properly configured, please check") 
                            self.loginfo (xv, "checked swap size is %d" % (swap_size))
                    else:
                        raise Exception ("cmd 'free' on via returns %s %s" % (out, err))
                    return
                except socket.error, e:
                    _e = e
                    continue
            if _e:
                raise Exception(_e)
        else: # if it's recoverd os, passwd is likely to be changed by user
            self.loginfo (xv, "started and reachable")


    def create_vps (self, xv, vps_image=None, is_new=True):
        """ check resources, create vps, wait for ip reachable, check ssh loging and check swap of vps.
            on error raise Exception, the caller should log exception """
        assert isinstance (xv, XenVPS)
        assert xv.has_all_attr
        
        _vps_image, os_type, os_version = os_image.find_os_image (xv.os_id)
        if not vps_image:
            vps_image = _vps_image
        if not vps_image:
            raise Exception ("no template image configured for os_type=%s, os_id=%s" % (os_type, xv.os_id))
        if not os.path.exists (vps_image):
            raise Exception ("image %s not exists" % (vps_image))

        xv.check_resource_avail ()

        #fs_type is tied to the image
        fs_type = vps_common.get_fs_from_tarball_name (vps_image)
        if not fs_type:
            fs_type = conf.DEFAULT_FS_TYPE

        self.loginfo (xv, "begin to create image")
        if xv.swap_store.size_g > 0:
            xv.swap_store.create ()
        xv.root_store.fs_type = fs_type
        for disk in xv.data_disks.values ():
            disk.create ()
            self.loginfo (xv, "%s created" % (str(disk)))

        self.create_xen_config (xv)

        vps_mountpoint = xv.root_store.mount_tmp ()
        self.loginfo (xv, "mounted vps image %s" % (str(xv.root_store)))
    
        try:
            if re.match (r'.*\.img$', vps_image):
                vps_common.sync_img (vps_mountpoint, vps_image)
            else:
                vps_common.unpack_tarball (vps_mountpoint, vps_image)
            self.loginfo (xv, "synced vps os to %s" % (str(xv.root_store)))
            
            self.loginfo (xv, "begin to init os")
            os_init.os_init (xv, vps_mountpoint, os_type, os_version, to_init_passwd=is_new)
            self.loginfo (xv, "done init os")
        finally:
            vps_common.umount_tmp (vps_mountpoint)
        
        self.save_vps_meta (xv)
        self._boot_and_test (xv, is_new=is_new)
        self.loginfo (xv, "done vps creation")

    def close_vps (self, vps_id, _xv=None):
        meta_path = self._meta_path (vps_id, is_trash=False)
        if os.path.exists (meta_path):
            xv = self._load_vps_meta (meta_path)
            self.loginfo (xv, "loaded %s" % (meta_path))
        elif _xv:
            xv = _xv
        else:
            raise Exception ("missing metadata or backend data")
        if xv.stop ():
            self.loginfo (xv, "vps stopped")
        else:
            xv.destroy ()
            self.loginfo (xv, "vps cannot shutdown, destroyed it")
        self._close_vps (xv)
        return

    def _close_vps (self, xv):
        for disk in xv.data_disks.values ():
            if disk.exists ():
                disk.dump_trash (conf.CLOSE_EXPIRE_DAYS)
                self.loginfo (xv, "%s moved to trash" % (str(disk)))
        if xv.swap_store.exists ():
            xv.swap_store.delete ()
            self.loginfo (xv, "deleted %s" % (str(xv.swap_store)))
        if os.path.islink (xv.auto_config_path): 
            os.remove (xv.auto_config_path)
            self.loginfo (xv, "deleted %s" % (xv.auto_config_path))
        if os.path.exists (xv.config_path):
            os.remove (xv.config_path)
            self.loginfo (xv, "deleted %s" % (xv.config_path))

        meta_path = self._meta_path (xv.vps_id, is_trash=False)
        if os.path.exists (meta_path):
            os.remove (meta_path)
            self.loginfo (xv, "removed %s" % (meta_path))
        self.save_vps_meta (xv, is_trash=True)
        self.loginfo (xv, "closed")


    def _clear_nonexisting_trash (self, xv):
        trash = xv.get_nonexisting_trash ()
        for disk in trash:
            xv.delete_trash (disk)
            self.loginfo (xv, "delete nonexisting trash %s from meta" % disk.trash_str ())

    def is_trash_exists (self, vps_id):
        trash_meta_path = self._meta_path (vps_id, is_trash=True)
        if os.path.exists (trash_meta_path):
            xv = self._load_vps_meta (trash_meta_path)
            for disk in xv.data_disks.values ():
                if not disk.trash_exists ():
                    return False
            return True
        return False

    def is_normal_exists (self, vps_id):
        meta_path = self._meta_path (vps_id)
        if os.path.exists (meta_path):
            xv = self._load_vps_meta (meta_path)
            for disk in xv.data_disks.values ():
                if not disk.exists ():
                    return False
            return True
        return False

    def reopen_vps (self, vps_id, _xv=None):
        meta_path = self._meta_path (vps_id)
        trash_meta_path = self._meta_path (vps_id, is_trash=True)
        if os.path.exists (trash_meta_path):
            xv = self._load_vps_meta (trash_meta_path)
            self.loginfo (xv, "loaded %s" % (trash_meta_path))
        elif _xv:
            xv = _xv
        else:
            raise Exception ("missing metadata or backend data")

        xv.check_resource_avail (ignore_trash=True)
        # TODO if resource not available on this host, we must allow moving the vps elsewhere
        for disk in xv.data_disks.values ():
            if disk.trash_exists ():
                disk.restore_from_trash ()
                self.loginfo (xv, "%s restored from trash" % (str(disk)))
            elif not disk.exists ():
                raise Exception ("%s missing" % (str(disk)))
        # swap is never keep when vps close
        if xv.swap_store.size_g > 0 and not xv.swap_store.exists ():
            xv.swap_store.create ()
            self.loginfo (xv, "swap image %s created" % (str(xv.swap_store)))

        xv.check_storage_integrity ()
        self._clear_nonexisting_trash (xv)

        self.create_xen_config (xv)

        if os.path.exists (trash_meta_path):
            os.remove (trash_meta_path)
            self.loginfo (xv, "removed %s" % (trash_meta_path))
        self.save_vps_meta (xv)

        self._boot_and_test (xv, is_new=False)

        self.loginfo (xv, "done vps creation")

    def _delete_disk (self, xv, disk):
        if disk.exists ():
            disk.delete ()
            self.loginfo (xv, "deleted %s" % (str(disk)))
        if disk.trash_exists ():
            self.loginfo (xv, "deleted %s" % (disk.trash_str ()))

        
    def delete_vps (self, vps_id, _xv=None):
        meta_path = self._meta_path (vps_id)
        trash_meta_path = self._meta_path (vps_id, is_trash=True)
        if os.path.exists (meta_path):
            xv = self._load_vps_meta (meta_path)
            self.loginfo (xv, "loaded %s" % (meta_path))
        elif os.path.exists (trash_meta_path):
            xv = self._load_vps_meta (trash_meta_path)
            self.loginfo (xv, "loaded %s" % (trash_meta_path))
        elif _xv:
            xv = _xv
        else:
            raise Exception ("missing metadata or backend data")
        if xv.stop ():
            self.loginfo (xv, "vps stopped, going to delete data")
        else:
            xv.destroy ()
            self.loginfo (xv, "vps cannot shutdown, destroyed it, going to delete data")
        for disk in xv.data_disks.values ():
            self._delete_disk (xv, disk)
        for disk in xv.trash_disks.values ():
            self._delete_disk (xv, disk)
        xv.swap_store.delete ()
        self.loginfo (xv, "deleted %s" % (str(xv.swap_store)))
        if os.path.exists (xv.config_path):
            os.remove (xv.config_path)
            self.loginfo (xv, "deleted %s" % (xv.config_path))
        if os.path.islink (xv.auto_config_path):
            os.remove (xv.auto_config_path)
            self.loginfo (xv, "deleted %s" % (xv.auto_config_path))
        if os.path.exists (meta_path):
            os.remove (meta_path)
            self.loginfo (xv, "removed %s" % (meta_path))
        if os.path.exists (trash_meta_path):
            os.remove (trash_meta_path)
            self.loginfo (xv, "removed %s" % (trash_meta_path))
            self.save_vps_meta (xv, is_trash=True, is_deleted=True)
        else:
            self.save_vps_meta (xv, is_trash=False, is_deleted=True)
        self.loginfo (xv, "deleted")

    def reboot_vps (self, xv):
        assert xv.has_all_attr
        if xv.stop ():
            self.loginfo (xv, "stopped")
        else:
            xv.destroy ()
            self.loginfo (xv, "force destroy")
        xv.start ()
        if not xv.wait_until_reachable (60):
            raise Exception ("the vps started, seems not reachable")
        self.loginfo (xv, "started")

    def upgrade_vps (self, xv_new):
        assert xv_new.has_all_attr
        meta_path = self._meta_path (xv_new.vps_id, is_trash=False)
        xv_old = self._load_vps_meta (meta_path)

        _vps_image, os_type, os_version = os_image.find_os_image (xv_new.os_id)
        fs_type = vps_common.get_fs_from_tarball_name (_vps_image)
        if not fs_type:
            fs_type = conf.DEFAULT_FS_TYPE

        if xv_old.stop ():
            self.loginfo (xv_old, "stopped")
        else:
            xv_old.destroy ()
            self.loginfo (xv_old, "force destroy")
        for xen_dev, new_disk in xv_new.data_disks.iteritems ():
            old_disk = xv_old.data_disks.get (xen_dev)
            if not new_disk.exists ():
                new_disk.create (fs_type)
            else:
                if old_disk and old_disk.size_g != new_disk.size_g:
                    old_disk, new_disk = xv_new.renew_storage (xen_dev)
                    vps_mountpoint_bak = old_disk.mount_trash_temp ()
                    self.loginfo (xv_new, "mounted vps old root %s" % (old_disk.trash_str ()))
                    try:
                        fs_type = vps_common.get_partition_fs_type (mount_point=vps_mountpoint_bak)
                        new_disk.create (fs_type)
                        self.loginfo (xv_new, "create new %s" % (str(new_disk)))
                        vps_mountpoint = new_disk.mount_tmp ()
                        self.loginfo (xv_new, "mounted vps new %s" % (str(new_disk)))
                        try:
                            call_cmd ("rsync -a '%s/' '%s/'" % (vps_mountpoint_bak, vps_mountpoint))
                            self.loginfo (xv_new, "synced old %s to new one" % (str(new_disk)))
                            # TODO:  uncomment this when os_init can deal with multiple net address
                        finally:
                            vps_common.umount_tmp (vps_mountpoint)
                    finally:
                        vps_common.umount_tmp (vps_mountpoint_bak)
                else: 
                    # we have to know fs_type for fstab generation
                    vps_mountpoint = new_disk.mount_tmp ()
                    try:
                        fs_type = vps_common.get_partition_fs_type (mount_point=vps_mountpoint)
                        new_disk.fs_type = fs_type
                    finally:
                        vps_common.umount_tmp (vps_mountpoint)

        for xen_dev, old_disk in xv_old.data_disks.iteritems ():
            if not xv_new.data_disks.has_key (xen_dev):
                xv_new.data_disks[xen_dev] = old_disk
                xv_new.dump_storage_to_trash (old_disk)
        self.save_vps_meta (xv_new)
        self.create_xen_config (xv_new)
        self.loginfo (xv_new, "begin to init os")
        vps_mountpoint = xv_new.root_store.mount_tmp ()
        try:
            os_init.os_init (xv_new, vps_mountpoint, os_type, os_version, to_init_passwd=False)
            self.loginfo (xv_new, "done init os")
        finally:
            vps_common.umount_tmp (vps_mountpoint)
        self._boot_and_test (xv_new, is_new=False)
        self.loginfo (xv_new, "done vps upgrade")

    def reinstall_os (self, vps_id, _xv=None, os_id=None, vps_image=None):
        meta_path = self._meta_path (vps_id, is_trash=False)
        xv = None
        if _xv:
            xv = _xv
            if os_id:
                xv.os_id = os_id
        else:
            if os.path.exists (meta_path):
                xv = self._load_vps_meta (meta_path)
                if os_id:
                    xv.os_id = os_id
                elif _xv: 
                    xv.os_id = _xv.os_id
                else:
                    raise Exception ("missing os_id")
            else:
                raise Exception ("missing vps metadata")
        _vps_image, os_type, os_version = os_image.find_os_image (xv.os_id)
        if not vps_image:
            vps_image = _vps_image
        if not vps_image:
            raise Exception ("no template image configured for os_type=%s, os_id=%s" % (os_type, xv.os_id))
        if not os.path.exists (vps_image):
            raise Exception ("image %s not exists" % (vps_image))
        #fs_type is tied to the image
        fs_type = vps_common.get_fs_from_tarball_name (vps_image)
        if not fs_type:
            fs_type = conf.DEFAULT_FS_TYPE

        assert xv.has_all_attr
        if xv.stop ():
            self.loginfo (xv, "stopped")
        else:
            xv.destroy ()
            self.loginfo (xv, "force destroy")
        root_store_trash, root_store = xv.renew_storage (xv.root_store.xen_dev, 5)
        xv.root_store.create (fs_type)
        self.loginfo (xv, "create new root")

        # we have to know fs_type for fstab generation
        for xen_dev, disk in xv.data_disks.iteritems ():
            if xen_dev == xv.root_store.xen_dev:
                continue
            if disk.exists ():
                vps_mountpoint = disk.mount_tmp ()
                try:
                    fs_type = vps_common.get_partition_fs_type (mount_point=vps_mountpoint)
                    disk.fs_type = fs_type
                finally:
                    vps_common.umount_tmp (vps_mountpoint)
            else:
                disk.create (fs_type)

        vps_mountpoint_bak = root_store_trash.mount_trash_temp ()
        try:
            vps_mountpoint = xv.root_store.mount_tmp ()
            self.loginfo (xv, "mounted vps image %s" % (str(xv.root_store)))
        
            try:
                if re.match (r'.*\.img$', vps_image):
                    vps_common.sync_img (vps_mountpoint, vps_image)
                else:
                    vps_common.unpack_tarball (vps_mountpoint, vps_image)
                self.loginfo (xv, "synced vps os to %s" % (str(xv.root_store)))
                
                for sync_dir in ['home', 'root']:
                    dir_org = os.path.join (vps_mountpoint_bak, sync_dir)
                    dir_now = os.path.join (vps_mountpoint, sync_dir)
                    if os.path.exists (dir_org):
                        call_cmd ("rsync -a --exclude='.bash*'  '%s/' '%s/'" % (dir_org, dir_now))
                        self.loginfo (xv, "sync dir /%s to new os" % (sync_dir))

                self.loginfo (xv, "begin to init os")
                if _xv:
                    xv.root_pw = _xv.root_pw
                    os_init.os_init (xv, vps_mountpoint, os_type, os_version, to_init_passwd=True)
                else: # if no user data provided from backend
                    os_init.os_init (xv, vps_mountpoint, os_type, os_version, to_init_passwd=False)
                    os_init.migrate_users (xv, vps_mountpoint, vps_mountpoint_bak)
                self.loginfo (xv, "done init os")
            finally:
                vps_common.umount_tmp (vps_mountpoint)
        finally:
            vps_common.umount_tmp (vps_mountpoint_bak)

        self.create_xen_config (xv)
        self.save_vps_meta (xv)
        self._boot_and_test (xv, is_new=False)
        self.loginfo (xv, "done vps reinstall")

    def set_vif_int (self, vps_id, ip, netmask):
        # if run again, vif's MAC is the same with previous one
        meta_path = self._meta_path (vps_id, is_trash=False)
        xv = None
        if os.path.exists (meta_path):
            xv = self._load_vps_meta (meta_path)
        else:
            raise Exception ("cannot find meta data for vps %s" % (vps_id))
        vifname = "%sint" % (xv.name)
        mac = None
        is_ip_available = not vps_common.ping (ip)
        if xv.has_netinf (vifname):
            self.loginfo (xv, "removing existing vif %s" % (vifname))
            mac = xv.vifs[vifname].mac
            p_ip = xv.vifs[vifname].mac
            if p_ip == ip and not is_ip_available:
                self.loginfo (xv, "no need to change vif %s, ip is the same" % (vifname))
                return False
            if not is_ip_available:
                raise Exception ("ip %s is in use" % (ip))
            vps_common.xm_network_detach (xv.name, mac)
            xv.del_netinf (vifname)
        elif not is_ip_available:
            raise Exception ("ip %s is in use" % (ip))

        vif = xv.add_netinf_int ({ip : netmask}, mac)
        vps_common.xm_network_attach (xv.name, vifname, vif.mac, ip, vif.bridge)
        self.save_vps_meta (xv)
        self.create_xen_config (xv)
        self.loginfo (xv, "added internal vif ip=%s" % (ip))
        return True

    def create_from_migrate (self, xv):
        xv.check_resource_avail (ignore_trash=True)
        if xv.swap_store.size_g > 0 and not xv.swap_store.exists ():
            xv.swap_store.create ()
            self.loginfo (xv, "swap image %s created" % (str(xv.swap_store)))
        xv.check_storage_integrity ()
        self._clear_nonexisting_trash (xv)
        self.create_xen_config (xv)
        self.save_vps_meta (xv)
        self._boot_and_test (xv, is_new=False)
        self.loginfo (xv, "done vps creation")


    def migrate_vps (self, migclient, vps_id, dest_ip):
        xv = self.load_vps_meta (vps_id)
        if xv.stop ():
            self.loginfo (xv, "vps stopped")
        else:
            xv.destroy ()
            self.loginfo (xv, "vps cannot shutdown, destroyed it")
        self.loginfo (xv, "going to be migrated to %s" % (dest_ip))
        if conf.USE_LVM:
            for disk in xv.data_disks.values ():
                migclient.sync_partition (disk.dev)
        else:
            migclient.sync_partition (xv.root_store.file_path)
            for disk in xv.data_disks.values ():
                migclient.sync_partition (disk.file_path)
        self.loginfo (xv, "partition synced, going to boot vps remotely")
        migclient.create_vps (xv)
        self.loginfo (xv, "remote vps started, going to close local vps")
        self._close_vps (xv)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

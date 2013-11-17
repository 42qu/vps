#!/usr/bin/env python


import os
import re
import time
import socket
import threading
try:
    import json
except ImportError:
    import simplejson as json
import ops.vps_common as vps_common
import ops.os_image as os_image
from ops.vps import XenVPS
import ops.os_init as os_init
from ops.vps_netinf import VPSNet, VPSNetExt, VPSNetInt

import ops._env
import conf
from lib.command import call_cmd
from vps_scan import scan_port_open

if conf.USE_OVS:
    from ops.openvswitch import OVSOps
assert conf.DEFAULT_FS_TYPE
assert conf.VPS_METADATA_DIR
assert conf.CLOSE_EXPIRE_DAYS


class VPSOps(object):

    def __init__(self, logger):
        self.logger = logger

    def loginfo(self, xv, msg):
        message = "[%s] %s" % (xv.name, msg)
        if not self.logger:
            print message
        else:
            self.logger.info(message)

    def create_xen_config(self, xv):
        """ will override config """
        xen_config = xv.gen_xenpv_config()
        f = open(xv.config_path, 'w')
        try:
            f.write(xen_config)
            self.loginfo(xv, "%s created" % (xv.config_path))
        finally:
            f.close()
        xv.create_autolink()
        self.loginfo(xv, "created link to xen auto")
        self.save_vps_meta(xv)

    @staticmethod
    def _meta_path(vps_id, is_trash=False, is_deleted=False):
        if not os.path.isdir(conf.VPS_METADATA_DIR):
            raise Exception("directory %s is not exists" % (conf.VPS_METADATA_DIR))
        filename = "vps%d.json" % (vps_id)
        if is_trash:
            filename += ".trash"
        if is_deleted:
            filename += ".delete"
        return os.path.join(conf.VPS_METADATA_DIR, filename)

    def _load_vps_meta(self, meta_path):
        f = open(meta_path, "r")
        data = None
        try:
            data = json.load(f)
        finally:
            f.close()
        try:
            xv = XenVPS.from_meta(data)
            return xv
        except Exception, e:
            raise Exception("file=%s, %s" % (meta_path, str(e)))

    def load_vps_meta(self, vps_id, is_trash=False):
        meta_path = self._meta_path(vps_id, is_trash=is_trash)
        return self._load_vps_meta(meta_path)

    def save_vps_meta(self, xv, is_trash=False, is_deleted=False, override=True):
        assert isinstance(xv, XenVPS)
        data = xv.to_meta()
        if data is None:
            raise Exception("error in XenVPS.to_meta()")
        meta_path = self._meta_path(xv.vps_id, is_trash=is_trash, is_deleted=is_deleted)
        if os.path.exists(meta_path) and override is False:
            return
        f = open(meta_path, "w")
        try:
            json.dump(data, f, indent=2, sort_keys=True)
        finally:
            f.close()
        self.loginfo(xv, "meta saved to %s" % (meta_path))
        
    
    def _boot_and_test(self, xv, is_new=True):
        assert isinstance(xv, XenVPS)
        self.loginfo(xv, "booting")
        status = None
        out = None
        err = None
        xv.start()
        if not xv.wait_until_reachable(120):
            if not is_new:
                if not scan_port_open(xv.vif_ext.ip or xv.vif_int.ip):
                    raise Exception("the vps started, seems not reachable")
            else:
                raise Exception("the vps started, seems not reachable")
        if is_new:
            _e = None
            for i in xrange(0, 5):
                self.loginfo(xv, "started and reachable, wait for ssh connection")
                time.sleep(5)
                try:
                    status, out, err = vps_common.call_cmd_via_ssh(xv.ip, user="root", password=xv.root_pw, cmd="free|grep Swap")
                    self.loginfo(xv, "ssh login ok")
                    if status == 0:
                        if xv.swap_store.size_g > 0:
                            swap_size = int(out.split()[1])
                            if swap_size == 0:
                                raise Exception("it seems swap has not properly configured, please check") 
                            self.loginfo(xv, "checked swap size is %d" % (swap_size))
                    else:
                        raise Exception("cmd 'free' on via returns %s %s" % (out, err))
                    return
                except socket.error, e:
                    _e = e
                    continue
            if _e:
                raise Exception(_e)
        else: # if it's recoverd os, passwd is likely to be changed by user
            self.loginfo(xv, "started and reachable")


    def create_vps(self, xv, vps_image=None, is_new=True):
        """ check resources, create vps, wait for ip reachable, check ssh loging and check swap of vps.
            on error raise Exception, the caller should log exception """
        assert isinstance(xv, XenVPS)
        assert xv.has_all_attr
        
        _vps_image, os_type, os_version = os_image.find_os_image(xv.os_id)
        if not vps_image:
            vps_image = _vps_image
        if not vps_image:
            raise Exception("no template image configured for os_type=%s, os_id=%s" % (os_type, xv.os_id))
        if not os.path.exists(vps_image):
            raise Exception("image %s not exists" % (vps_image))

        xv.check_resource_avail()

        #fs_type is tied to the image
        fs_type = vps_common.get_fs_from_tarball_name(vps_image)
        if not fs_type:
            fs_type = conf.DEFAULT_FS_TYPE

        self.loginfo(xv, "begin to create image")
        if xv.swap_store.size_g > 0:
            xv.swap_store.create()
        xv.root_store.fs_type = fs_type
        for disk in xv.data_disks.values():
            disk.create()
            self.loginfo(xv, "%s created" % (str(disk)))

        vps_mountpoint = xv.root_store.mount_tmp()
        self.loginfo(xv, "mounted vps image %s" % (str(xv.root_store)))
        try:
            xv.root_store.destroy_limit()
            if re.match(r'.*\.img$', vps_image):
                vps_common.sync_img(vps_mountpoint, vps_image)
            else:
                vps_common.unpack_tarball(vps_mountpoint, vps_image)
            self.loginfo(xv, "synced vps os to %s" % (str(xv.root_store)))
            
            self.loginfo(xv, "begin to init os")
            os_init.os_init(xv, vps_mountpoint, os_type, os_version, is_new=is_new, to_init_passwd=is_new, to_init_fstab=True)
            self.loginfo(xv, "done init os")
            xv.root_store.create_limit()
        finally:
            vps_common.umount_tmp(vps_mountpoint)
        
        self.create_xen_config(xv)
        self._boot_and_test(xv, is_new=is_new)
        self.loginfo(xv, "done vps creation")

    def close_vps(self, vps_id, _xv=None):
        meta_path = self._meta_path(vps_id, is_trash=False)
        if os.path.exists(meta_path):
            xv = self._load_vps_meta(meta_path)
            self.loginfo(xv, "loaded %s" % (meta_path))
        elif _xv:
            xv = _xv
        else:
            raise Exception("missing metadata or backend data")
        if xv.stop():
            self.loginfo(xv, "vps stopped")
        else:
            xv.destroy()
            self.loginfo(xv, "vps cannot shutdown, destroyed it")
        time.sleep(3)
        self._close_vps(xv)
        return

    def _close_vps(self, xv):
        for disk in xv.data_disks.values():
            if disk.exists():
                disk.dump_trash()
                self.loginfo(xv, "%s moved to trash" % (str(disk)))
        if xv.swap_store.exists():
            xv.swap_store.delete()
            self.loginfo(xv, "deleted %s" % (str(xv.swap_store)))
        if os.path.islink(xv.auto_config_path): 
            os.remove(xv.auto_config_path)
            self.loginfo(xv, "deleted %s" % (xv.auto_config_path))
        if os.path.exists(xv.config_path):
            os.remove(xv.config_path)
            self.loginfo(xv, "deleted %s" % (xv.config_path))

        meta_path = self._meta_path(xv.vps_id, is_trash=False)
        if os.path.exists(meta_path):
            os.remove(meta_path)
            self.loginfo(xv, "removed %s" % (meta_path))
        self.save_vps_meta(xv, is_trash=True)
        self.loginfo(xv, "closed")


    def _clear_nonexisting_trash(self, xv):
        trash = xv.get_nonexisting_trash()
        for disk in trash:
            xv.delete_trash(disk)
            self.loginfo(xv, "delete nonexisting trash %s from meta" % disk.trash_str())

    def is_trash_exists(self, vps_id):
        trash_meta_path = self._meta_path(vps_id, is_trash=True)
        if os.path.exists(trash_meta_path):
            xv = self._load_vps_meta(trash_meta_path)
            for disk in xv.data_disks.values():
                if not disk.trash_exists():
                    return False
            return True
        return False

    def is_normal_exists(self, vps_id):
        meta_path = self._meta_path(vps_id)
        if os.path.exists(meta_path):
            xv = self._load_vps_meta(meta_path)
            for disk in xv.data_disks.values():
                if not disk.exists():
                    return False
            return True
        return False

    def reopen_vps(self, vps_id, _xv=None):
        meta_path = self._meta_path(vps_id)
        trash_meta_path = self._meta_path(vps_id, is_trash=True)
        xv_old = None
        if os.path.exists(trash_meta_path):
            xv_old = self._load_vps_meta(trash_meta_path)
            self.loginfo(xv_old, "loaded %s" % (trash_meta_path))
            if _xv:
                xv = _xv
            else:
                xv = xv_old
        elif _xv:
            xv = _xv
        else:
            raise Exception("missing metadata or backend data")

        xv.check_resource_avail(ignore_trash=True)
        for disk in xv.data_disks.values():
            if disk.trash_exists():
                disk.restore_from_trash()
                self.loginfo(xv, "%s restored from trash" % (str(disk)))
            elif not disk.exists():
                raise Exception("%s missing" % (str(disk)))
        # swap is never keep when vps close
        if xv.swap_store.size_g > 0 and not xv.swap_store.exists():
            xv.swap_store.create()
            self.loginfo(xv, "swap image %s created" % (str(xv.swap_store)))

        xv.check_storage_integrity()

        if xv_old:
            # renew storage size
            self._upgrade(xv, xv_old)
            self._clear_nonexisting_trash(xv_old)
            os.remove(trash_meta_path)
            self.loginfo(xv, "removed %s" % (trash_meta_path))
        else:
            self.create_xen_config(xv)

        self._boot_and_test(xv, is_new=False)
        self.loginfo(xv, "done vps creation")


    def _delete_disk(self, xv, disk):
        if disk.exists():
            disk.delete()
            self.loginfo(xv, "deleted %s" % (str(disk)))
        if disk.trash_exists():
            disk.delete_trash()
            self.loginfo(xv, "deleted %s" % (disk.trash_str()))

        
    def delete_vps(self, vps_id, _xv=None, check_date=False):
        meta_path = self._meta_path(vps_id)
        trash_meta_path = self._meta_path(vps_id, is_trash=True)
        if os.path.exists(meta_path):
            if check_date:
                raise Exception("check_date not pass, you should manually delete it")
            xv = self._load_vps_meta(meta_path)
            self.loginfo(xv, "loaded %s" % (meta_path))
        elif os.path.exists(trash_meta_path):
            if check_date:
                st = os.stat(trash_meta_path)
                if time.time() - st.st_ctime < 3600 * 24 * conf.CLOSE_EXPIRE_DAYS:
                    raise Exception("check_date not pass, you should manually delete it")
            xv = self._load_vps_meta(trash_meta_path)
            self.loginfo(xv, "loaded %s" % (trash_meta_path))
        elif _xv:
            if check_date:
                self.loginfo(_xv, "missing metadata, skip")
                return
            xv = _xv
        else:
            raise Exception("missing metadata or backend data")
        if xv.stop():
            self.loginfo(xv, "vps stopped, going to delete data")
        else:
            xv.destroy()
            self.loginfo(xv, "vps cannot shutdown, destroyed it, going to delete data")
        time.sleep(3)
        for disk in xv.data_disks.values():
            self._delete_disk(xv, disk)
        for disk in xv.trash_disks.values():
            self._delete_disk(xv, disk)
        xv.swap_store.delete()
        self.loginfo(xv, "deleted %s" % (str(xv.swap_store)))
        if os.path.exists(xv.config_path):
            os.remove(xv.config_path)
            self.loginfo(xv, "deleted %s" % (xv.config_path))
        if os.path.islink(xv.auto_config_path):
            os.remove(xv.auto_config_path)
            self.loginfo(xv, "deleted %s" % (xv.auto_config_path))
        if os.path.exists(meta_path):
            os.remove(meta_path)
            self.loginfo(xv, "removed %s" % (meta_path))
        if os.path.exists(trash_meta_path):
            os.remove(trash_meta_path)
            self.loginfo(xv, "removed %s" % (trash_meta_path))
            self.save_vps_meta(xv, is_trash=True, is_deleted=True)
        else:
            self.save_vps_meta(xv, is_trash=False, is_deleted=True)
        self.loginfo(xv, "deleted")

    def reboot_vps(self, xv):
        assert xv.has_all_attr
        if xv.stop():
            self.loginfo(xv, "stopped")
        else:
            xv.destroy()
            self.loginfo(xv, "force destroy")
        xv.start()
        if not xv.wait_until_reachable(60):
            raise Exception("the vps started, seems not reachable")
        self.loginfo(xv, "started")

    def upgrade_vps(self, xv_new):
        assert xv_new.has_all_attr
        meta_path = self._meta_path(xv_new.vps_id, is_trash=False)
        xv_old = self._load_vps_meta(meta_path)
        if xv_old.is_running:
            if xv_old.stop():
                self.loginfo(xv_old, "stopped")
            else:
                xv_old.destroy()
            self.loginfo(xv_old, "force destroy")
        time.sleep(3)
        self._upgrade(xv_new, xv_old)
        self._boot_and_test(xv_new, is_new=False)
        self.loginfo(xv_new, "done vps upgrade")


    def _upgrade(self, xv_new, xv_old):
        # TODO: check hard disk downgrade size
        _vps_image, os_type, os_version = os_image.find_os_image(xv_new.os_id)
        fs_type = vps_common.get_fs_from_tarball_name(_vps_image)
        if not fs_type:
            fs_type = conf.DEFAULT_FS_TYPE

        for xen_dev, new_disk in xv_new.data_disks.iteritems():
            old_disk = xv_old.data_disks.get(xen_dev)
            if not new_disk.exists():
                new_disk.create(fs_type)
                self.loginfo(xv_new, "create %s" % (str(new_disk)))
            else:
                assert new_disk.size_g
                if old_disk:
                    old_size = old_disk.get_size()
                    new_size = new_disk.size_g
                    if old_size == new_size:
                        pass
                    elif old_size == new_size:
                        pass
                    elif old_size < new_size and new_disk.can_resize():
                        new_disk.destroy_limit()
                        new_disk.resize(new_disk.size_g)
                        new_disk.create_limit()
                        self.loginfo(xv_new, "resized %s from %s to %s" % (str(new_disk), old_size, new_size))
                    else:
                        old_disk, new_disk = xv_new.renew_storage(xen_dev, new_size=new_disk.size_g)
                        vps_mountpoint_bak = old_disk.mount_trash_temp()
                        self.loginfo(xv_new, "mounted %s" % (old_disk.trash_str()))
                        try:
                            fs_type = vps_common.get_mounted_fs_type(mount_point=vps_mountpoint_bak)
                            new_disk.create(fs_type)
                            new_disk.destroy_limit()
                            self.loginfo(xv_new, "create new %s" % (str(new_disk)))
                            vps_mountpoint = new_disk.mount_tmp()
                            self.loginfo(xv_new, "mounted %s" % (str(new_disk)))
                            try:
                                call_cmd("rsync -a '%s/' '%s/'" % (vps_mountpoint_bak, vps_mountpoint))
                                self.loginfo(xv_new, "synced old %s to new one" % (str(new_disk)))
                            finally:
                                vps_common.umount_tmp(vps_mountpoint)
                            new_disk.create_limit()
                        finally:
                            vps_common.umount_tmp(vps_mountpoint_bak)

        for xen_dev, old_disk in xv_old.data_disks.iteritems():
            if not xv_new.data_disks.has_key(xen_dev):
                xv_new.data_disks[xen_dev] = old_disk
                xv_new.dump_storage_to_trash(old_disk)
                self.loginfo(xv_new, "%s dump to trash" % (str(old_disk)))
        self.create_xen_config(xv_new)
        self.loginfo(xv_new, "begin to init os")
        vps_mountpoint = xv_new.root_store.mount_tmp()
        try:
            os_init.os_init(xv_new, vps_mountpoint, os_type, os_version, is_new=False, to_init_passwd=False, to_init_fstab=True)
            self.loginfo(xv_new, "done init os")
        finally:
            vps_common.umount_tmp(vps_mountpoint)


    def reset_pw(self, xv):
        if not xv.root_pw:
            raise Exception("orz, root passwd is empty")
        if xv.stop():
            self.loginfo(xv, "stopped")
        else:
            xv.destroy()
            self.loginfo(xv, "force destroy")
        vps_mountpoint = xv.root_store.mount_tmp()
        try:
            os_init.set_root_passwd_2(xv, vps_mountpoint)
        finally:
            vps_common.umount_tmp(vps_mountpoint)
        self._boot_and_test(xv, is_new=True)
        self.loginfo(xv, "done vps reset passwd")


    def reinstall_os(self, vps_id, _xv=None, os_id=None, vps_image=None):
        meta_path = self._meta_path(vps_id, is_trash=False)
        xv = None
        if os.path.exists(meta_path):
            xv = self._load_vps_meta(meta_path)
            if os_id:
                xv.os_id = os_id
            elif _xv: 
                xv.os_id = _xv.os_id
                self._update_vif_setting(xv, _xv)
            else:
                raise Exception("missing os_id")
        elif _xv:
            xv = _xv
            if os_id:
                xv.os_id = os_id
            raise Exception("missing vps metadata")
        _vps_image, os_type, os_version = os_image.find_os_image(xv.os_id)
        if not vps_image:
            vps_image = _vps_image
        if not vps_image:
            raise Exception("no template image configured for os_type=%s, os_id=%s" % (os_type, xv.os_id))
        if not os.path.exists(vps_image):
            raise Exception("image %s not exists" % (vps_image))
        #fs_type is tied to the image
        fs_type = vps_common.get_fs_from_tarball_name(vps_image)
        if not fs_type:
            fs_type = conf.DEFAULT_FS_TYPE

        assert xv.has_all_attr
        if xv.stop():
            self.loginfo(xv, "stopped")
        else:
            xv.destroy()
            self.loginfo(xv, "force destroy")
        time.sleep(3)
        root_store_trash, root_store = xv.renew_storage(xv.root_store.xen_dev, 5)
        xv.root_store.create(fs_type)
        self.loginfo(xv, "create new root")

        # we have to know fs_type for fstab generation
        for xen_dev, disk in xv.data_disks.iteritems():
            if xen_dev == xv.root_store.xen_dev:
                continue
            if disk.exists():
                pass
            else:
                disk.create(fs_type)

        vps_mountpoint_bak = root_store_trash.mount_trash_temp()
        try:
            vps_mountpoint = xv.root_store.mount_tmp()
            self.loginfo(xv, "mounted vps image %s" % (str(xv.root_store)))
        
            try:
                xv.root_store.destroy_limit()
                if re.match(r'.*\.img$', vps_image):
                    vps_common.sync_img(vps_mountpoint, vps_image)
                else:
                    vps_common.unpack_tarball(vps_mountpoint, vps_image)
                self.loginfo(xv, "synced vps os to %s" % (str(xv.root_store)))
                
                for sync_dir in ['home', 'root']:
                    dir_org = os.path.join(vps_mountpoint_bak, sync_dir)
                    dir_now = os.path.join(vps_mountpoint, sync_dir)
                    if os.path.exists(dir_org):
                        call_cmd("rsync -a --exclude='.bash*'  '%s/' '%s/'" % (dir_org, dir_now))
                        self.loginfo(xv, "sync dir /%s to new os" % (sync_dir))

                self.loginfo(xv, "begin to init os")
                if _xv:
                    xv.root_pw = _xv.root_pw
                    os_init.os_init(xv, vps_mountpoint, os_type, os_version, is_new=True, to_init_passwd=True, to_init_fstab=True)
                else: # if no user data provided from backend
                    os_init.os_init(xv, vps_mountpoint, os_type, os_version, is_new=True, to_init_passwd=False, to_init_fstab=True,)
                    os_init.migrate_users(xv, vps_mountpoint, vps_mountpoint_bak)
                self.loginfo(xv, "done init os")
                xv.root_store.create_limit()
            finally:
                vps_common.umount_tmp(vps_mountpoint)
        finally:
            vps_common.umount_tmp(vps_mountpoint_bak)

        self.create_xen_config(xv)
        self._boot_and_test(xv, is_new=False)
        self.loginfo(xv, "done vps reinstall")

    def set_vif_int(self, vps_id, ip, netmask):
        # if run again, vif's MAC is the same with previous one
        meta_path = self._meta_path(vps_id, is_trash=False)
        xv = None
        if os.path.exists(meta_path):
            xv = self._load_vps_meta(meta_path)
        else:
            raise Exception("cannot find meta data for vps %s" % (vps_id))
        vifname = "%sint" % (xv.name)
        mac = None
        is_ip_available = not vps_common.ping(ip)
        if xv.has_netinf(vifname):
            mac = xv.vifs[vifname].mac
            if ip in xv.vifs[vifname].ip_dict.keys():
                self.loginfo(xv, "no need to change vif %s, ip is the same" % (vifname))
                return False
            if not is_ip_available:
                raise Exception("ip %s is in use" % (ip))
            self.loginfo(xv, "removing existing vif %s" % (vifname))
            vps_common.xm_network_detach(xv.name, mac)
            xv.del_netinf(vifname)
        elif not is_ip_available:
            raise Exception("ip %s is in use" % (ip))

        vif = xv.add_netinf_int({ip : netmask}, mac)
        vps_common.xm_network_attach(xv.name, vifname, vif.mac, ip, vif.bridge)
        self.create_xen_config(xv)
        self.loginfo(xv, "added internal vif ip=%s" % (ip))
        return True


    def change_qos(self, _xv):
        meta_path = self._meta_path(_xv.vps_id)
        if not os.path.exists(meta_path):
            xv = self.load_vps_meta(_xv.vps_id, is_trash=True)
            xv.vif_ext.bandwidth = _xv.vif_ext.bandwidth
            bandwidth = float(_xv.vif_ext.bandwidth or 0)
            vif_name = xv.vif_ext.ifname
            self.save_vps_meta(xv, is_trash=True)
        else:
            xv = self._load_vps_meta(meta_path)
            if not _xv.vif_ext or not xv.vif_ext:
                return
            xv.vif_ext.bandwidth = _xv.vif_ext.bandwidth
            bandwidth = float(_xv.vif_ext.bandwidth or 0)
            vif_name = xv.vif_ext.ifname
            self.save_vps_meta(xv)
            if conf.USE_OVS:
                if xv.is_running():
                    ovsops = OVSOps()
                    ovsops.unset_traffic_limit(vif_name)
                    ovsops.set_traffic_limit(vif_name, int(bandwidth * 1000))
                    self.loginfo(xv, "updated vif=%s bandwidth to %s Mbps" % (vif_name, bandwidth))
                    if not xv.wait_until_reachable(5):
                        raise Exception("ip unreachable!")
            else:
#               if xv.stop():
#                   self.loginfo(xv, "vps stopped")
#               else:
#                   xv.destroy()
#                   self.loginfo(xv, "vps cannot shutdown, destroyed it")
                self.create_xen_config(xv)

    def _update_vif_setting(self, xv, _xv):
        xv.vifs = dict()
        xv.gateway = _xv.gateway
        for vif in _xv.vifs.values():
            if isinstance(vif, VPSNetExt):
                xv.add_netinf_ext(vif.ip_dict, vif.mac, vif.bandwidth)
            else:
                xv.add_netinf_int(vif.ip_dict, vif.mac, vif.bandwidth)

    def change_ip(self, _xv):
        xv = self.load_vps_meta(_xv.vps_id)
        self._update_vif_setting(xv, _xv)
        _vps_image, os_type, os_version = os_image.find_os_image(xv.os_id)
        if xv.stop():
            self.loginfo(xv, "vps stopped")
        else:
            xv.destroy()
            self.loginfo(xv, "vps cannot shutdown, destroyed it")
        time.sleep(3)
        vps_mountpoint = xv.root_store.mount_tmp()
        self.loginfo(xv, "mounted vps image %s" % (str(xv.root_store)))
        try:
            self.loginfo(xv, "begin to init os")
            os_init.os_init(xv, vps_mountpoint, os_type, os_version, is_new=False, to_init_passwd=False, to_init_fstab=False)
            self.loginfo(xv, "done init os")
        finally:
            vps_common.umount_tmp(vps_mountpoint)
        self.create_xen_config(xv)
        self._boot_and_test(xv, is_new=False)
        self.loginfo(xv, "done vps change ip")
      

#    def create_from_hot_migrate(self, xv):
#        """ server side """
#        xv.check_storage_integrity()
#        self._clear_nonexisting_trash(xv)
#        self.create_xen_config(xv)
#        # test
#        xv.restore()
#        if not xv.wait_until_reachable(120):
#            raise Exception("the vps started, seems not reachable")
#        os.remove(xv.save_path)
#        self.loginfo(xv, "removed %s" % (xv.save_path))
#        self.loginfo(xv, "done vps hot immigrate")

#    def _send_swap(self, migclient, xv, remote_path, result):
#        assert isinstance(result, dict)
#        if not xv.swap_store or xv.swap_store.size_g <= 0:
#            return
#        try:
#            self.logger.info("going to send %s" % (xv.swap_store.file_path))
#            migclient.sendfile(xv.swap_store.file_path, remote_path, block_size=5 * 1024 * 1024)
#            result["swap"] = (0, "")
#            self.logger.info("sent %s" % (xv.swap_store.file_path))
#        except Exception, e:
#            self.logger.exception(e)
#            result["swap"] = (1, str(e))
#        return result

#    def _send_savefile(self, migclient, xv, result):
#        assert isinstance(result, dict)
#        self.logger.info("going to send %s" % (xv.save_path))
#        ret, err = migclient.rsync(xv.save_path, use_zip=True)
#        result["savefile"] = (ret, err)
#        if ret == 0:
#            self.logger.info("sent %s" % (xv.save_path))
#        else:
#            self.logger.error("sending %s error: %s" % (xv.save_path, err))
#        return result


#    def migrate_vps_hot(self, migclient, vps_id, dest_ip, speed=None):
#        """client size"""
#        xv = self.load_vps_meta(vps_id)
#        xv.save()
#        try:
#            swap_path = migclient.prepare_immigrate(xv)
#            result = dict()
#            th1 = threading.Thread(target=self._send_swap, args=(migclient, xv, swap_path, result,))
#            th1.setDaemon(1)
#            th1.start()
#            th2 = threading.Thread(target=self._send_savefile, args=(migclient, xv, result,))
#            th2.setDaemon(1)
#            th2.start()
#            for disk in xv.data_disks.values():
#                migclient.sync_partition(disk.file_path, partition_name=disk.partition_name, speed=speed)
#            self.loginfo(xv, "partition synced")
#            th1.join()
#            th2.join()
#            swap_result = result.get("swap")
#            savefile_result = result.get("savefile")
#            if swap_result and swap_result[0] == 0 and savefile_result and savefile_result[0] == 0:
#                migclient.vps_hot_immigrate(xv)
#                self.loginfo(xv, "emigrated to %s" % (dest_ip))
#                print "ok"
#                # ok
#                return
#            else:
#                if swap_result and swap_result[0] != 0:
#                    print "sending swap error: ", swap_result[1]
#                if savefile_result and savefile_result[0] != 0:
#                    print "sending savefile error:", savefile_result[1]
#        except Exception, e:
#            self.logger.exception(e)
#            print "error %s" % (e)
#        # error
#        print "going to restore vps %s" % (xv.vps_id)
#        xv.restore()
#        msg = "vps %s restored" % (xv.vps_id)
#        print msg
#        self.logger.info(msg)
#        os.remove(xv.save_path)
#        return False
        

    def create_from_migrate(self, xv):
        """ server side """
        xv.check_resource_avail(ignore_trash=True)
        if xv.swap_store.size_g > 0 and not xv.swap_store.exists():
            xv.swap_store.create()
            self.loginfo(xv, "swap image %s created" % (str(xv.swap_store)))

        for disk in xv.data_disks.values():
            disk.create_limit()
        xv.check_storage_integrity()
        self._clear_nonexisting_trash(xv)
        vps_mountpoint = xv.root_store.mount_tmp()
        self.loginfo(xv, "mounted vps image %s" % (str(xv.root_store)))
        try:
            _vps_image, os_type, os_version = os_image.find_os_image(xv.os_id)
            self.loginfo(xv, "begin to init os")
            os_init.os_init(xv, vps_mountpoint, os_type, os_version, is_new=False, to_init_passwd=False, to_init_fstab=True)
            self.loginfo(xv, "done init os")
        finally:
            vps_common.umount_tmp(vps_mountpoint)

        self.create_xen_config(xv)
        self._boot_and_test(xv, is_new=False)
        self.loginfo(xv, "done vps creation")
       

    def migrate_vps(self, migclient, vps_id, dest_ip, xv=None, speed=None):
        """client side """
        if not xv:
            xv = self.load_vps_meta(vps_id)
        if xv.stop():
            self.loginfo(xv, "vps stopped")
        else:
            xv.destroy()
            self.loginfo(xv, "vps cannot shutdown, destroyed it")
        self.loginfo(xv, "going to be migrated to %s" % (dest_ip))
        for disk in xv.data_disks.values():
            migclient.sync_partition(disk.file_path, partition_name=disk.partition_name, speed=speed)
        self.loginfo(xv, "partition synced, going to boot vps remotely")
        migclient.create_vps(xv)
        self.loginfo(xv, "remote vps started, going to close local vps")
        self.close_vps(vps_id)

    def migrate_closed_vps(self, migclient, vps_id, dest_ip, speed=None, _xv=None):
        """client side """
        xv = self.load_vps_meta(vps_id, is_trash=True)
        if xv.is_running():
            raise Exception("vps %s is still running" % (vps_id))
        self.loginfo(xv, "going to be move to %s" % (dest_ip))
        for disk in xv.data_disks.values():
            migclient.sync_partition(disk.trash_path, partition_name="trash_%s" % (disk.partition_name), speed=speed)
        migclient.save_closed_vps(xv)
        self.loginfo(xv, "done")



    def hotsync_vps(self, migclient, vps_id, dest_ip, speed=None):
        if not conf.USE_LVM:
            raise Exception("only lvm host support hotsync")
        xv = self.load_vps_meta(vps_id)
        for disk in xv.data_disks.values():
            migclient.snapshot_sync(disk.dev, speed=speed)
        

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

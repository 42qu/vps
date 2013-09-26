#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import re
import traceback
import time
import socket
import ops._env
from ops.sync_server import SyncServerBase, SyncClientBase
from ops.vps_store import vps_store_new
from ops.vps import XenVPS
from ops.vps_ops import VPSOps
import ops.vps_common as vps_common
import conf
import threading
assert conf.RSYNC_CONF_PATH
assert conf.RSYNC_PORT
assert conf.MOUNT_POINT_DIR
try:
    from conf.private.migrate_svr import CLIENT_KEYS
except ImportError:
    CLIENT_KEYS = None

class MigrateServer(SyncServerBase):

    def __init__(self, logger):
        SyncServerBase.__init__(self, logger, CLIENT_KEYS)
        self._partition_jobs = dict()
        self._lock = threading.Lock()
        self._rsync_running = False
        self.server.add_handle(self.alloc_partition)
        self.server.add_handle(self.umount)
        self.server.add_handle(self.create_vps)
        self.server.add_handle(self.save_closed_vps)

    def _start_rsync(self, name):
        self._lock.acquire()
        if not self._rsync_running:
            self.start_rsync()
            self._rsync_running = True
        self._partition_jobs[name] = 1
        self._lock.release()

    def _stop_rsync(self, name):
        self._lock.acquire()
        if self._partition_jobs.has_key(name):
            del self._partition_jobs[name]
        if len(self._partition_jobs.keys()) == 0 and  self._rsync_running:
            self.stop_rsync()
            self._rsync_running = False
        self._lock.release()
        
#    def poll(self):
#        SyncServerBase.poll()
#        returncode = self._rsync_popen.poll()
#        if returncode is not None:
#            if self.is_running:
#                #err = "\n".join(self._rsync_popen.stderr.readlines())
#                returncode, out, err = self._rsync_popen.get_result()
#                self.logger.error("returncode=%d, error=%s" % (returncode, err)) 
#                #self._rsync_popen.stderr.close()
#                self.logger.error("rsync daemon exited, restart it")
#                self.start_rsync()
#

    def alloc_partition(self, partition_name, size_g, fs_type):
        try:
            storage = vps_store_new(partition_name, None, fs_type, None, size_g)
            if not storage.exists():
                if storage.trash_exists():
                    storage.restore_from_trash()
                    self.logger.info("%s restored from trash" % (str(storage)))
                else:
                    storage.create()
                    self.logger.info("%s created" % (str(storage)))
            storage.destroy_limit()
            mount_point = storage.get_mounted_dir()
            if not mount_point:
                mount_point = storage.mount_tmp()
                self.logger.info("%s mounted on %s" % (str(storage), mount_point))
            else:
                self.logger.info("%s already mounted on %s" % (str(storage), mount_point))
            mount_point_name = os.path.basename(mount_point)
            self._start_rsync(mount_point_name)
            return mount_point_name
        except Exception, e:
            self.logger.exception(e)
            raise


    def umount(self, mount_point):
        mount_point_path = os.path.join(conf.MOUNT_POINT_DIR, mount_point)
        try:
            vps_common.umount_tmp(mount_point_path)
            self.logger.info("%s umounted" % (mount_point_path))
            self._stop_rsync(mount_point)
        except Exception, e:
            self.logger.exception(e)
            raise


    def create_vps(self, meta, origin_host_id):
        try:
            xv = XenVPS.from_meta(meta)
            self.logger.info("vps %s immigrate from host=%s" % (xv.vps_id, origin_host_id))
            vpsops = VPSOps(self.logger)
            vpsops.create_from_migrate(xv.clone())  # some setting various between different hosts
        except Exception, e:
            self.logger.exception(e)
            raise

    def save_closed_vps(self, meta, origin_host_id):
        try:
            xv = XenVPS.from_meta(meta)
            self.logger.info("closed vps %s immigrate from host=%s" % (xv.vps_id, origin_host_id))
            vpsops = VPSOps(self.logger)
            vpsops.save_vps_meta(xv, is_trash=True)
        except Exception, e:
            self.logger.exception(e)
            raise


class MigrateClient(SyncClientBase):

    def __init__(self, logger, server_ip):
        SyncClientBase.__init__(self, logger, server_ip)


    def snapshot_sync(self, dev, speed=None):
        snapshot_name = "sync_%s" % (os.path.basename(dev))
        snapshot_dev = "/dev/%s/%s" % (conf.VPS_LVM_VGNAME, snapshot_name)
        if not os.path.exists(snapshot_dev):
            vps_common.lv_snapshot(dev, snapshot_name, conf.VPS_LVM_VGNAME)
        self.logger.info("made snapshot %s for %s" % (snapshot_dev, dev))
        try:
            self.sync_partition(snapshot_dev, partition_name=os.path.basename(dev), speed=speed)
        finally:
            vps_common.lv_delete(snapshot_dev)
            self.logger.info("delete snapshot %s" % (snapshot_dev))

    def _load_image(self, file_path):
        file_path = os.path.abspath(file_path)
        file_name = os.path.basename(file_path)
        om = re.match(r'(\w+)\.img', file_name)
        assert om is not None
        partition_name = om.group(1) 
        if partition_name.find("data") < 0:
            partition_name += "_root"
        s = os.stat(file_path)
        size_g = s.st_size / 1024 / 1024 / 1024
        mount_point = vps_common.get_mountpoint(file_path) 
        if mount_point:
            self.logger.info("%s already mounted on %s" % (file_path, mount_point))
        else:
            mount_point = vps_common.mount_loop_tmp(file_path, readonly=True, temp_dir=conf.MOUNT_POINT_DIR)
            self.logger.info("%s mounted on %s" % (file_path, mount_point))
        return mount_point, size_g, partition_name


    def _load_lvm(self, dev):
        #return partition_name, size_g, mount_point
        arr = dev.split("/")
        partition_name = arr[-1]
        size_g = vps_common.lv_getsize(dev)
        mount_point = vps_common.lv_get_mountpoint(dev)
        if mount_point:
            self.logger.info("%s already mounted on %s" % (dev, mount_point))
        else:
            mount_point = vps_common.mount_partition_tmp(dev, readonly=True, temp_dir=conf.MOUNT_POINT_DIR)
            self.logger.info("%s mounted on %s" % (dev, mount_point))
        return mount_point, size_g, partition_name


    def sync_partition(self, dev, partition_name=None, speed=None):
        """ when you sync a snapshot lv to remote, you'll need to specify partition_name
        """
        arr = dev.split("/")
        if arr[0] == "" and arr[1] == 'dev' and len(arr) == 4:
            mount_point, size_g, _partition_name = self._load_lvm(dev)
        else:
            mount_point, size_g, _partition_name = self._load_image(dev)
        if not partition_name:
            partition_name = _partition_name
        try:
            fs_type = vps_common.get_fs_type(dev)
            mig = self.connect(timeout=size_g / 2 + 5)
            remote_mount_point = self.rpc.call("alloc_partition", partition_name, size_g, fs_type)
            self.logger.info("remote(%s) mounted" % (remote_mount_point))
            ret, err = self.rsync(mount_point, remote_mount_point, speed=speed)
            if ret == 0:
                print "rsync ok"
                self.logger.info("rsync %s to %s ok" % (dev, self.server_ip))
            else:
                print "rsync failed", err
                self.logger.info("rsync %s to %s error, ret=%s, err=%s" % (dev, self.server_ip, ret, err))
            time.sleep(3)
            self.rpc.call("umount", remote_mount_point)
            print "remote umounted %s" % (partition_name)
            self.logger.info("remote(%s) umounted" % (remote_mount_point))
        finally:
            vps_common.umount_tmp(mount_point) # probably not work when keyboard cancel
            self.close()
            
    def create_vps(self, xv):
        meta = xv.to_meta()
        try:
            self.connect(timeout=120)
            self.rpc.call("create_vps", meta, origin_host_id=conf.HOST_ID)
        finally:
            self.close()

    def save_closed_vps(self, xv):
        meta = xv.to_meta()
        try:
            self.connect(timeout=120)
            self.rpc.call("save_closed_vps", meta, origin_host_id=conf.HOST_ID)
        finally:
            self.close()



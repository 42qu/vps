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
assert conf.RSYNC_CONF_PATH
assert conf.RSYNC_PORT
assert conf.MOUNT_POINT_DIR

class MigrateServer (SyncServerBase):

    def __init__ (self, logger):
        SyncServerBase.__init__ (self, logger)
        self._handlers["alloc_partition"] = self._handler_alloc_partition
        self._handlers["umount"] = self._handler_umount
        self._handlers["create_vps"] = self._handler_create_vps

    def _handler_alloc_partition (self, conn, cmd, data):
        try:
            size_g = self._get_req_attr (data, 'size')
            partition_name = self._get_req_attr (data, 'part_name')
            fs_type = self._get_req_attr (data, 'fs_type')
            storage = vps_store_new (partition_name, None, fs_type, None, size_g)
            if not storage.exists ():
                storage.create ()
                self.logger.info ("%s created" % (str(storage)))
            mount_point = storage.get_mounted_dir ()
            if not mount_point:
                mount_point = storage.mount_tmp ()
                self.logger.info ("%s mounted on %s" % (str(storage), mount_point))
            else:
                self.logger.info ("%s already mounted on %s" % (str(storage), mount_point))
            mount_point_name = os.path.basename (mount_point)
            self._send_response (conn, 0, {"mount_point": mount_point_name})
        except socket.error, e:
            raise e
        except Exception, e:
            self.logger.exception (e)
            self._send_response (conn, 1, str(e))


    def _handler_umount (self, conn, cmd, data):
        mount_point = self._get_req_attr (data, "mount_point")
        mount_point_path = os.path.join (conf.MOUNT_POINT_DIR, mount_point)
        try:
            vps_common.umount_tmp (mount_point_path)
            self.logger.info ("%s umounted" % (mount_point_path))
            self._send_response (conn, 0, "")
        except socket.error, e:
            raise e
        except Exception, e:
            self.logger.exception (e)
            self._send_response (conn, 1, str(e))

    def _handler_create_vps (self, conn, cmd, data):
        meta = self._get_req_attr (data, "meta")
        origin_host_id = self._get_req_attr (data, "origin_host_id")
        try:
            xv = XenVPS.from_meta (meta)
            self.logger.info ("vps %s immigrate from host=%s" % (xv.vps_id, origin_host_id))
            vpsops = VPSOps (self.logger)
            vpsops.create_from_migrate (xv.clone ())  # some setting various between different hosts
            self._send_response (conn, 0, "")
        except socket.error, e:
            raise e
        except Exception, e:
            self.logger.exception (e)
            self._send_response (conn, 1, str(e))


class MigrateClient (SyncClientBase):

    def __init__ (self, logger, server_ip):
        SyncClientBase.__init__ (self, logger, server_ip)


    def snapshot_sync (self, dev, speed=None):
        snapshot_dev = vps_common.lv_snapshot (dev, "sync_%s" % (os.path.basename(dev)) , conf.VPS_LVM_VGNAME)
        self.logger.info ("made snapshot %s for %s" % (snapshot_dev, dev))
        try:
            self.sync_partition (snapshot_dev, partition_name=os.path.basename(dev), speed=speed)
        finally:
            vps_common.lv_delete (snapshot_dev)
            self.logger.info ("delete snapshot %s" % (snapshot_dev))

    def _load_image (self, file_path):
        file_path = os.path.abspath (file_path)
        file_name = os.path.basename (file_path)
        om = re.match (r'(\w+)\.img', file_name)
        assert om is not None
        partition_name = om.group (1)
        s = os.stat (file_path)
        size_g = s.st_size / 1024 / 1024 / 1024
        mount_point = vps_common.get_mountpoint (file_path) 
        if mount_point:
            self.logger.info ("%s already mounted on %s" % (file_path, mount_point))
        else:
            mount_point = vps_common.mount_loop_tmp (file_path, readonly=True, temp_dir=conf.MOUNT_POINT_DIR)
            self.logger.info ("%s mounted on %s" % (file_path, mount_point))
        return mount_point, size_g, partition_name


    def _load_lvm (self, dev):
        #return partition_name, size_g, mount_point
        arr = dev.split ("/")
        partition_name = arr[-1]
        size_g = vps_common.lv_getsize (dev)
        mount_point = vps_common.lv_get_mountpoint (dev)
        if mount_point:
            self.logger.info ("%s already mounted on %s" % (dev, mount_point))
        else:
            mount_point = vps_common.mount_partition_tmp (dev, readonly=True, temp_dir=conf.MOUNT_POINT_DIR)
            self.logger.info ("%s mounted on %s" % (dev, mount_point))
        return mount_point, size_g, partition_name


    def sync_partition (self, dev, partition_name=None, speed=None):
        """ when you sync a snapshot lv to remote, you'll need to specify partition_name
        """
        arr = dev.split ("/")
        if arr[0] == "" and arr[1] == 'dev' and len (arr) == 4:
            mount_point, size_g, _partition_name = self._load_lvm (dev)
        else:
            mount_point, size_g, _partition_name = self._load_image (dev)
        if not partition_name:
            partition_name = _partition_name
        fs_type = vps_common.get_fs_type (dev)
        sock = None
        try:
            sock = self.connect (timeout=5)
            self._send_msg (sock, "alloc_partition", {
                'part_name': partition_name,
                'size': size_g,
                'fs_type': fs_type,
                })
            sock.settimeout (size_g / 2 + 5)
            msg = self._recv_response (sock)
            sock.settimeout (10)
            remote_mount_point =  msg['mount_point']
            self.logger.info ("remote(%s) mounted" % (remote_mount_point))
            ret, err = self.rsync (mount_point, remote_mount_point, speed=speed)
            if ret == 0:
                print "rsync ok"
                self.logger.info ("rsync %s to %s ok" % (dev, self.server_ip))
            else:
                print "rsync failed", err
                self.logger.info ("rsync %s to %s error, ret=%s, err=%s" % (dev, self.server_ip, ret, err))
            time.sleep (3)
            self._send_msg (sock, "umount", {
                'mount_point': remote_mount_point,
                })
            sock.settimeout (size_g / 2 + 5)
            self._recv_response (sock)
            sock.settimeout (10)
            print "remote umounted %s" % (partition_name)
            self.logger.info ("remote(%s) umounted" % (remote_mount_point))
        finally:
            if sock:
                sock.close ()
            vps_common.umount_tmp (mount_point)
            time.sleep (1)
            
    def create_vps (self, xv):
        meta = xv.to_meta ()
        sock = None
        try:
            sock = self.connect (timeout=120)
            self._send_msg (sock, "create_vps", {
                    'meta': meta,
                    'origin_host_id': conf.HOST_ID,
                })
            msg = self._recv_response (sock)
        finally:
            if sock:
                sock.close ()


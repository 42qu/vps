#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import time
import signal
import socket
import threading

try: 
    import json
except ImportError:
    import simplejson as json

import ops._env
from ops.vps_ops import VPSOps
from ops.vps_store import VPSStoreImage, VPSStoreLV
from lib.job_queue import JobQueue, Job
from lib.socket_engine import TCPSocketEngine, Connection
from lib.net_io import NetHead
import ops.vps_common as vps_common
import lib.io_poll as io_poll
import conf
assert conf.RSYNC_CONF_PATH
assert conf.RSYNC_PORT
assert conf.MOUNT_POINT_DIR

class InteractJob (Job):

    def __init__ (self, migsvr, conn, cmd, msg_data):
        self.migsvr = migsvr
        self.conn = conn
        self.msg_data = msg_data
        self.cmd = cmd
        Job.__init__ (self)

    def do (self):
        cmd = self.cmd
        cb = self.migsvr._handlers[cmd]
        conn = self.conn
        if callable (cb):
            try:
                cb (conn, cmd, self.msg_data)
                self.migsvr.engine.watch_conn (conn)
            except Exception, e:
                self.migsvr.logger.exception (e)
                self.migsvr.engine.close_conn (conn)
            

class _BaseServer (object):


    def __init__ (self, logger):
        self.logger = logger
        self.host_id = conf.HOST_ID
        self.vpsops = VPSOps (self.logger)
        self._rsync_popen = None
        self.is_running = False
        self.listen_ip = "0.0.0.0"
        self.inf_addr = (self.listen_ip, conf.INF_PORT)
        self.rsync_port = conf.RSYNC_PORT
        self.engine = TCPSocketEngine (io_poll.Poll())
        self.engine.set_logger (logger)
        self.engine.set_timeout (10, 10, 1800)
        self.inf_sock = None
        self.jobqueue = JobQueue (logger)
        self._handlers = dict ()

    def loop (self):
        while self.is_running:
            self.poll ()
            time.sleep (1)

    def poll (self):
        if self.is_running:
            self.engine.poll ()
            returncode = self._rsync_popen.poll ()
            if returncode is not None:
                #TODO log the returncode 
                self.logger.error ("rsync daemon exited, restart it")
                self.start_rsync ()

    def _server_handler (self, conn):
        sock = conn.sock
        data = None
        try:
            head = NetHead.read_head (sock)
            if head.body_len == 0:
                self.logger.error ("from peer: %s, zero len head received" % (conn.peer))
                self.engine.close_conn (conn)
                return 
            buf = head.read_data (sock)
            data = json.loads (buf)
        except socket.error, e:
            self.logger.exception ("from peer: %s, %s" % (conn.peer, e))
            self.engine.close_conn (conn)
            return
        except ValueError, e:
            self.logger.exception ("from peer: %s, bad msg data received, %s" % (conn.peer, e))
            self.engine.close_conn (conn)
            return
        except Exception, e:
            self.logger.exception (e)
            self.engine.close_conn (conn)
            return
        try:
            cmd = data.get ("cmd")
            if not cmd or not self._handlers.has_key (cmd):
                self.logger.error ("from peer: %s, no handler for cmd: %s" % (conn.peer, cmd))
                self.engine.close_conn (conn)
                return
            job = InteractJob (self, conn, cmd, data)
            self.engine.remove_conn (conn)
            self.jobqueue.put_job (job)
        except Exception, e:
            self.logger.exception (e)
            self.engine.close_conn (conn)
            return


    def start (self):
        if self.is_running:
            return
        self.is_running = True
        self.start_rsync ()
        self.jobqueue.start_worker (5)
        self.logger.info ("job_queue started")
        self.inf_sock = self.engine.listen_addr (self.inf_addr, readable_cb=self._server_handler)
        self.logger.info ("server started")

    def stop (self):
        if not self.is_running:
            return
        self.is_running = False
        self.engine.unlisten (self.inf_sock)
        self.logger.info ("server stopped")
        self.jobqueue.stop ()
        self.logger.info ("job_queue stopped")
        self.stop_rsync ()

    def start_rsync (self):
        rsync_conf = """
uid=root
gid=root
use chroot=yes
[sync_server]
    path=%s
    read only=no
    write only=yes
""" % (conf.MOUNT_POINT_DIR)

        f = open (conf.RSYNC_CONF_PATH, "w")
        try:
            f.write (rsync_conf)
        finally:
            f.close ()
        rsync_cmd = ["rsync", "--daemon", "--config=%s" % (conf.RSYNC_CONF_PATH), "--no-detach"]
        rsync_cmd.append ("--address=%s" % (self.listen_ip))
        rsync_cmd.append ("--port=%s" % (self.rsync_port))
        self._rsync_popen = subprocess.Popen (rsync_cmd, stderr=subprocess.PIPE, close_fds=True)
        self.logger.info ("started rsync, pid=%s" % (self._rsync_popen.pid))
        time.sleep (1)

    def stop_rsync (self):
        assert self._rsync_popen is not None
        self.logger.info ("stopping rsync")
        os.kill (self._rsync_popen.pid, signal.SIGTERM)
        self._rsync_popen.wait ()
        self.logger.info ("rsync stopped")

    def _send_msg (self, conn, msg):
        head = NetHead ()
        head.write_msg (conn.sock, json.dumps (msg))

    def _send_response (self, conn, res, msg):
        return self._send_msg (conn, {'res': res, 'msg': msg})

    def _get_req_attr (self, data, key):
        if data.has_key (key):
            return data[key]
        raise Exception ("invalid request, missing key %s" % (key))

class MigrateServer (_BaseServer):

    def __init__ (self, logger):
        _BaseServer.__init__ (self, logger)
        self._handlers["alloc_partition"] = self._handler_alloc_partition

    def _handler_alloc_partition (self, conn, cmd, data):
        size_g = self._get_req_attr (data, 'size')
        partition_name = self._get_req_attr (data, 'part_time')
        fs_type = self._get_req_attr (data, 'fs_type')
        storage = None
        if conf.USE_LVM:
            storage = VPSStoreLV (None, conf.VPS_LVM_VGNAME, partition_name , fs_type, None, size_g)
        else:
            storage = VPSStoreImage (None, conf.VPS_IMAGE_DIR, conf.VPS_TRASH_DIR, "%s.img" % partition_name, fs_type, None, size_g)
        if not storage.exists ():
            storage.create ()
        #TODO check whether is mounted
        mount_point = storage.mount_tmp ()
        self.logger.info ("mounted %s on %s" % (str(storage), mount_point))
        self._send_response (conn, 0, {"mount_point": mount_point})

class _BaseClient (object):

    def __init__ (self, logger, server_ip):
        self.server_ip = server_ip
        self.logger = logger
        self.vpsops = VPSOps (self.logger)

    def connect (self, timeout=10):
        addr = (self.server_ip, conf.INF_PORT)
        sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout (timeout)
        sock.connect (addr)
        return sock

    def _send_msg (self, sock, cmd, data):
        buf = json.dumps ({'cmd': cmd, 'data': data})
        head = NetHead ()
        head.write_msg (sock, buf)

    def _recv_msg (self, sock):
        head = NetHead.read_head (sock)
        if head.body_len == 0:
            return None
        buf = head.read_data (sock)
        return json.loads (buf)

    def _recv_response (self, sock):
        data = self._recv_msg (sock)
        res = None
        msg = None
        try:
            res = data['res']
            msg = data['msg']
        except KeyError, e:
            raise Exception ("invalid response, %s" % str(e))
        if str(res) != '0':
            raise Exception ("remote error: %s" % (msg))
        return msg


class MigrateClient (_BaseClient):

    def __init__ (self, logger, server):
        _BaseClient.__init__ (self, logger, server)

    def migrate_sync (self, vps_id):
        xv = self.vpsops.load_vps_meta (vps_id)

    def sync_partition (self, dev):
        # assert dev is lvm
        arr = dev.split ("/")
        partition_name = arr[-1]
        size_g = vps_common.lv_getsize (dev)
        mountpoint = vps_common.mount_partition_tmp (dev, readonly=True, temp_dir=conf.MOUNT_POINT_DIR)
        fs_type = vps_common.get_partition_fs_type (mount_point=mountpoint)

        sock = self.connect (timeout=20)
        self._send_msg (sock, "alloc_partition", {
            'part_name': partition_name,
            'size': size_g,
            'fs_type': fs_type,
            })
        msg = self._recv_response (sock)
        mount_point =  msg['mount_point']
        print mount_point


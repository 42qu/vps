#!/usr/bin/env python

import os
import socket
import subprocess
import time
import signal
try: 
    import json
except ImportError:
    import simplejson as json


import ops._env
from lib.job_queue import JobQueue, Job
from lib.socket_engine import TCPSocketEngine, Connection
import lib.io_poll as io_poll
from lib.net_io import NetHead
import conf
            
RSYNC_SERVER_NAME = "sync_server"


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
                self.migsvr.logger.info ("peer %s, cmd %s" % (conn.peer, cmd))
                cb (conn, cmd, self.msg_data)
                self.migsvr.engine.watch_conn (conn)
            except Exception, e:
                self.migsvr.logger.exception ("peer %s, uncaught exception: %s" % (conn.peer, str(e)))
                self.migsvr.engine.close_conn (conn)


class SyncServerBase (object):


    def __init__ (self, logger):
        self.logger = logger
        self.host_id = conf.HOST_ID
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

    def poll (self):
        self.engine.poll ()
        returncode = self._rsync_popen.poll ()
        if returncode is not None:
            if self.is_running:
                err = "\n".join (self._rsync_popen.stderr.readlines ())
                self.logger.error ("returncode=%d, error=%s" % (returncode, err)) 
                self._rsync_popen.stderr.close ()
                self.logger.error ("rsync daemon exited, restart it")
                self.start_rsync ()

    def _server_handler (self, conn):
        sock = conn.sock
        data = None
        head = None
        try:
            head = NetHead.read_head (sock)
        except socket.error:
            self.engine.close_conn (conn)
            return
        try:
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
            job = InteractJob (self, conn, cmd, data.get ("data"))
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
[%s]
    path=%s
    read only=no
    write only=yes
""" % (RSYNC_SERVER_NAME, conf.MOUNT_POINT_DIR)

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



class SyncClientBase (object):

    def __init__ (self, logger, server_ip):
        self.server_ip = server_ip
        self.logger = logger

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


    def rsync (self, mount_point, remote_mount_point):
        cmd = ("rsync", "-avz", "--delete", "%s/" % (mount_point), 
                "rsync://%s:%s/%s/%s/" % (self.server_ip, conf.RSYNC_PORT, RSYNC_SERVER_NAME, remote_mount_point)
                )
        p = subprocess.Popen (cmd, stderr=subprocess.PIPE, close_fds=True)
        retcode = p.wait ()
        if retcode:
            stderr = "\n".join (p.stderr.readlines ())
        else:
            stderr = None
        p.stderr.close ()
        return retcode, stderr

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

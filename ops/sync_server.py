#!/usr/bin/env python

import os
import socket
import ssl
import subprocess
from lib.command import Command, search_path

import time
import signal
try: 
    import json
except ImportError:
    import simplejson as json


import ops.vps_common as vps_common
import ops._env
from lib.job_queue import JobQueue, Job
from lib.socket_engine_ssl import SSLSocketEngine, Connection
import lib.io_poll as io_poll
from lib.net_io import NetHead
import conf
assert conf.RSYNC_CONF_PATH
assert conf.RSYNC_PORT
assert conf.MOUNT_POINT_DIR


            
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
                if not cb (conn, cmd, self.msg_data):
                    self.migsvr.engine.watch_conn (conn)
            except Exception, e:
                self.migsvr.logger.exception ("peer %s, uncaught exception: %s" % (conn.peer, str(e)))
                self.migsvr.engine.close_conn (conn)


class SyncServerBase (object):


    def __init__ (self, logger, allow_ip_dict=None):
        self.logger = logger
        self.allow_ip_dict = allow_ip_dict
        self.host_id = conf.HOST_ID
        self._rsync_popen = None
        self.is_running = False
        self.listen_ip = "0.0.0.0"
        self.inf_addr = (self.listen_ip, conf.INF_PORT)
        self.rsync_port = conf.RSYNC_PORT
        assert conf.SSL_CERT
        self.engine = SSLSocketEngine (io_poll.Poll(), is_blocking=True, cert_file=conf.SSL_CERT)
        self.engine.set_logger (logger)
        self.engine.set_timeout (10, 3600 * 24)
        self.inf_sock = None
        self.jobqueue = JobQueue (logger)
        self._handlers = dict ()
        self._handlers["recv_file"] = self._handler_recv_file
        self._sendfile_svr_dict = dict ()

    def loop (self):
        while self.is_running:
            self.poll ()

    def poll (self):
        self.engine.poll ()

    def _server_handler (self, conn):
        sock = conn.sock
        data = None
        head = None
        try:
            head = NetHead.read_head (sock)
        except socket.error:
            self.engine.close_conn (conn)
            return
        except Exception, e:
            self.logger.exception (e)
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
        #self.start_rsync ()
        self.jobqueue.start_worker (5)
        self.logger.info ("job_queue started")
        self.inf_sock = self.engine.listen_addr (self.inf_addr, readable_cb=self._server_handler, new_conn_cb=self._check_ip)
        self.logger.info ("server started")

    def _check_ip (self, sock, *args):
        peer = sock.getpeername ()
        if len(peer) == 2 and self.allow_ip_dict:
            if self.allow_ip_dict.has_key (peer[0]):
                return sock
            return None
        return sock

    def stop (self):
        if not self.is_running:
            return
        self.is_running = False
        self.engine.unlisten (self.inf_sock)
        self.logger.info ("server stopped")
        self.jobqueue.stop ()
        self.logger.info ("job_queue stopped")
        #self.stop_rsync ()

    def start_rsync (self):
        rsync_conf = """
uid=root
gid=root
use chroot=yes
og file=/dev/null
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
        #self._rsync_popen = subprocess.Popen (rsync_cmd, stderr=subprocess.PIPE, close_fds=True)
        self._rsync_popen = Command (rsync_cmd)
        self._rsync_popen.start ()
        self.logger.info ("started rsync, pid=%s" % (self._rsync_popen.pid))
        time.sleep (1)

    def stop_rsync (self):
        assert self._rsync_popen is not None
        self.logger.info ("stopping rsync")
        os.kill (self._rsync_popen.pid, signal.SIGTERM)
        self._rsync_popen.wait ()
        self.logger.info ("rsync stopped")


    def _handler_recv_file (self, conn, cmd, data):
        size = self._get_req_attr (data, "size")
        filepath = self._get_req_attr (data, "filepath")
        try:
            f = open (filepath, "w")
            head = NetHead ()
            data = json.dumps ({"res": 0, 'msg': ''})
            buf = head.pack (len (data)) + data
            conn.sock.setblocking (False)
            self.engine.write_unblock (conn, buf, self._recv_file_content, self._recv_file_content_error, cb_args=(f, filepath, size))
            return True
        except Exception, e:
            self._send_response (conn, 1, str(e))
            
    def _recv_file_content (self, conn, f, filepath, size):
        def __on_recv_content (conn, *cb_args): 
            buf = conn.get_readbuf ()
            #buf = buf.decode ("zlib")
            f.write (buf)
            _size = size
            if _size is not None:
                _size -= len (buf)
            if _size == 0:
                f.close ()
                self.engine.close_conn (conn)
                self.logger.info ("file %s recv done" % (filepath))
                return
            self._recv_file_content (conn, f, filepath, _size)
            return

        def __on_recv_head (conn, *cb_args):
            head = None
            try:
                head = NetHead.unpack (conn.get_readbuf ())
            except Exception, e:
                self.logger.error ("from peer %s, %s" % (str(conn.peer), str (e)))
                self._recv_file_content_error (conn, f, filepath, size)
                self.engine.close_conn (conn)
                return
            self.engine.read_unblock (conn, head.body_len, __on_recv_content, self._recv_file_content_error, cb_args=(f, filepath, size,))
            return
        self.engine.read_unblock (conn, NetHead.size, __on_recv_head, self._recv_file_content_error, cb_args=(f, filepath, size,))
        return

    def _recv_file_content_error (self, conn, f, filepath, size):
        f.close ()
        self.logger.error ("file: %s, %s bytes left, recv error: %s" % (filepath, size, str(conn.error)))


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
        sock = ssl.wrap_socket (sock)
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

    def sendfile (self, filepath, remote_path, block_size=1*1024*1024):
        assert filepath and remote_path
        sock = None
        filesize = None
        if os.path.islink (filepath):
            filepath = os.path.realpath (filepath)
        if os.path.isfile (filepath):
            st = os.stat (filepath)
            filesize = st.st_size
        elif filepath.find ("/dev") == 0:
            filesize = vps_common.get_blk_size (filepath)
        f = open (filepath, "r")
        head = NetHead ()
        try:
            sock = self.connect ()
            try:
                self._send_msg (sock, "recv_file", {'size': filesize, 'filepath': remote_path})
                self._recv_response (sock)
                while filesize > 0 or filesize is None:
                    buf = f.read (block_size)
                    sent_size = len (buf)
                    if sent_size == 0:
                        break
                    #buf = buf.encode ("zlib")
                    head.write_msg (sock, buf)
                    filesize -= sent_size
            finally:
                sock.close ()
        finally:
            f.close ()
        

    def rsync (self, source, dest=None, speed=None, use_zip=False):
        """ speed is in Mbit/s """
        options = ("-avW", "--inplace", )
        if os.path.isdir (source):
            if source[-1] != "/":
                source += "/"
            if dest and dest[-1] != "/":
                dest += "/"
            if dest:
                options += ("--delete", )
        if not dest:
            dest = ""
        if speed:
            assert isinstance (speed, (int, float))
            options += ("--bwlimit", str(int(speed * 1000 / 8)), )
            use_zip = True
        if use_zip:
            options += ("-z", )
            
        cmd = ("rsync", ) + options + \
                (source, \
                "rsync://%s:%s/%s/%s" % (self.server_ip, conf.RSYNC_PORT, RSYNC_SERVER_NAME, dest)
                )
        print cmd
        p = subprocess.Popen (cmd, stderr=subprocess.PIPE, close_fds=True)
        retcode = p.wait ()
        if retcode:
            stderr = "\n".join (p.stderr.readlines ())
        else:
            stderr = None
        p.stderr.close ()
        return retcode, stderr

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

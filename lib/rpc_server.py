#!/usr/bin/env python
# coding:utf-8


# author: frostyplanet@gmail.com
# rpc server in threaded-pool mode

from job_queue import JobQueue, Job
from rpc import RPC_ServerHandle, RPC_Req, RPC_Resp
from net_io import NetHead
import io_poll
import time
import socket
from socket_engine import TCPSocketEngine
import sys


class InteractJob(Job):
        
    def __init__(self, server, conn, req):
        self.server = server
        self.conn = conn
        self.req = req
        Job.__init__(self)

        
    def do(self):
        rev = None
        err = None
        conn = self.conn
        try:
            start_ts = time.time()
            end_ts = time.time()
            rev = self.server.rpc_handles.call(self.req)
            self.server.logger.info("peer %s, rpc call %s [%s]" % (conn.peer, str(self.req), end_ts - start_ts))
        except Exception, e:
            err = e
            self.server.logger_err.exception("peer %s, rpc call %s failed: %s" % (conn.peer, str(self.req), str(e)))
        resp = RPC_Resp(rev, err)
        self._send(resp)


    def _send(self, resp):
        conn = self.conn
        try:
            NetHead().write_msg(conn.sock, resp.serialize())
            self.server.engine.watch_conn(conn)
        except Exception, e:
            self.server.logger_err.exception("peer %s, send response error: %s" % (conn.peer, str(e)))
            self.server.engine.close_conn(conn)


try:
    from socket_engine_ssl import SSLSocketEngine

    class SSL_RPC_Server(object):

        logger = None

        def __init__(self, cert_file, addr, logger, err_logger=None, timeout=10, idle_timeout=3600, white_list=()):
            self.logger = logger
            self.logger_err = err_logger or self.logger
            self.engine = SSLSocketEngine(io_poll.get_poll(), cert_file=cert_file, is_blocking=True)
            self.engine.set_logger(logger)
            self.engine.set_timeout(rw_timeout=timeout, idle_timeout=idle_timeout)
            self.inf_sock = None
            self.addr = addr
            self.jobqueue = JobQueue(logger)
            self.is_running = False
            self.ip_dict = dict()
            for ip in white_list:
                self.ip_dict[ip] = None
            self.rpc_handles = RPC_ServerHandle()

        def add_handle(self, func):
            self.rpc_handles.add_handle(func)
            self.logger.debug("added handle: %s" % str(func))

        def add_view(self, obj):
            for name in dir(obj):
                method = getattr(obj, name)
                if callable(method) and hasattr(method, 'func_name'):
                    if method.func_name.find("__") == 0:
                        continue
                    self.add_handle(method)


        def start(self, worker_num):
            if self.is_running:
                return
            self.jobqueue.start_worker(worker_num)
            self.logger.info("jq started")
            self.inf_sock = self.engine.listen_addr_ssl(self.addr, readable_cb=self._server_handle, new_conn_cb=self._check_ip)
            self.logger.info("server started")
            self.is_running = True


        def stop(self):
            if not self.is_running:
                return
            self.engine.unlisten(self.inf_sock)
            self.logger.info("server stopped")
            self.jobqueue.stop()
            self.logger.info("job_queue stopped")
            self.is_running = False

        def poll(self, timeout=10):
            self.engine.poll(timeout)

        def loop(self):
            while self.is_running:
                self.poll()

        def _check_ip(self, sock, *args):
            peer = sock.getpeername()
            if len(peer) == 2 and self.ip_dict:
                if self.ip_dict.has_key(peer[0]):
                    return sock
                return None
            return sock

        def _server_handle(self, conn):
            sock = conn.sock
            head = None
            try:
                head = NetHead.read_head(sock)
            except socket.error:
                self.engine.close_conn(conn)
                return
            except Exception, e:
                self.logger_err.exception(e)
                self.engine.close_conn(conn)
                return
            try:
                if head.body_len <= 0: 
                    self.logger.error("from peer: %s, zero len head received" % (conn.peer))
                    self.engine.close_conn(conn)
                    return 
                buf = head.read_data(sock)
                req = RPC_Req.deserialize(buf)
                job = InteractJob(self, conn, req)
                self.engine.remove_conn(conn)
                self.jobqueue.put_job(job)
                self.logger.info("peer %s, new req %s enqueue" % (conn.peer, str(req)))
            except Exception, e:
                self.logger_err.exception(e)
                self.engine.close_conn(conn)
                return

except ImportError, e:
    print >> sys.stderr, e



try:
    from crypter import AESCryptor

    class AESInteractJob(InteractJob):
            
        def __init__(self, server, conn, req, crypter_w):
            InteractJob.__init__(self, server, conn, req)
            self.crypter_w = crypter_w

        def _send(self, resp):
            conn = self.conn
            try:
                NetHead().write_msg(conn.sock, self.crypter_w.encrypt(resp.serialize()))
                self.server.engine.watch_conn(conn)
            except Exception, e:
                self.server.logger_err.exception("peer %s, send response error: %s" % (conn.peer, str(e)))
                self.server.engine.close_conn(conn)


    class AES_RPC_Server(object):

        logger = None

        def __init__(self, addr, client_keys, logger, err_logger=None, timeout=10, idle_timeout=3600, block_size=128):
            """ client_keys :  dict(ip=>key) or str """
            self.logger = logger
            self.logger_err = err_logger or self.logger
            self.engine = TCPSocketEngine(io_poll.get_poll(), is_blocking=True)
            self.engine.set_logger(logger)
            self.engine.set_timeout(rw_timeout=timeout, idle_timeout=idle_timeout)
            assert isinstance(client_keys, dict)
            self.client_keys = client_keys
            self.inf_sock = None
            self.addr = addr
            self.jobqueue = JobQueue(logger)
            self.is_running = False
            self.ip_dict = dict()
            self.block_size = block_size
            self.rpc_handles = RPC_ServerHandle()

        def get_key(self, peer):
            return self.client_keys.get(peer[0])

        def add_handle(self, func):
            self.rpc_handles.add_handle(func)
            self.logger.debug("added handle: %s" % str(func))

        def add_view(self, obj):
            for name in dir(obj):
                method = getattr(obj, name)
                if callable(method) and hasattr(method, 'func_name'):
                    if method.func_name.find("__") == 0:
                        continue
                    self.add_handle(method)

        def start(self, worker_num):
            if self.is_running:
                return
            self.jobqueue.start_worker(worker_num)
            self.logger.info("jq started")
            self.inf_sock = self.engine.listen_addr(self.addr, readable_cb=self._server_handle, new_conn_cb=self._check_ip)
            self.logger.info("server started")
            self.is_running = True


        def stop(self):
            if not self.is_running:
                return
            self.engine.unlisten(self.inf_sock)
            self.logger.info("server stopped")
            self.jobqueue.stop()
            self.logger.info("job_queue stopped")
            self.is_running = False

        def poll(self, timeout=10):
            self.engine.poll(timeout)

        def loop(self):
            while self.is_running:
                self.poll()

        def _check_ip(self, sock, *args):
            peer = sock.getpeername()
            if self.get_key(peer):
                return sock

        def _server_handle(self, conn):
            sock = conn.sock
            head = None
            try:
                head = NetHead.read_head(sock)
            except socket.error:
                self.engine.close_conn(conn)
                return
            except Exception, e:
                self.logger_err.exception(e)
                self.engine.close_conn(conn)
                return
            key = self.get_key(conn.peer)
            try:
                if head.body_len < self.block_size: 
                    self.logger.error("from peer: %s, smaller than block_size head received" % (str(conn.peer)))
                    self.engine.close_conn(conn)
                    return 
                buf = head.read_data(sock)
                iv = buf[0:self.block_size]
                buf = buf[self.block_size:]
                crypter_r = AESCryptor(key, iv, self.block_size)
                crypter_w = AESCryptor(key, iv, self.block_size)
                req = RPC_Req.deserialize(crypter_r.decrypt(buf))
                job = AESInteractJob(self, conn, req, crypter_w)
                self.engine.remove_conn(conn)
                self.jobqueue.put_job(job)
                self.logger.info("peer %s, new req %s enqueue" % (conn.peer, str(req)))
            except Exception, e:
                self.logger_err.exception(e)
                self.engine.close_conn(conn)
                return

except ImportError, e:
    print >> sys.stderr, e



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

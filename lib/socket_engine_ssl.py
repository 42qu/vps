#!/usr/bin/env python
# coding:utf-8

# @author frostyplanet@gmail.com
# @version $Id$
# @ socket engine which support synchronized and asynchronized i/o , with ssl support
#
import ssl
from socket_engine import *

"""
    provides connect_unblock_ssl() and listen_addr_ssl().
    use SSLSocketEngine directly or use patch_ssl_engine with a TCPSocketEngine object.
"""

def patch_ssl_engine(_object, cert_file, ssl_version=ssl.PROTOCOL_SSLv23):
    assert isinstance(_object, TCPSocketEngine)
    _init(_object, cert_file, ssl_version)
    _inject_class(_object.__class__)



def _init(self, cert_file, ssl_version=ssl.PROTOCOL_SSLv23):
    self.cert_file = cert_file
    self.ssl_version = ssl_version
    self._eagain_errno = [errno.EAGAIN, ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE]
    self._error_exceptions = (socket.error, ssl.SSLError, )


class SSLSocketEngine(TCPSocketEngine):

    def __init__(self, poll, cert_file, is_blocking=False, debug=False, ssl_version=ssl.PROTOCOL_SSLv23):
        TCPSocketEngine.__init__(self, poll, is_blocking=is_blocking, debug=debug)
        _init(self, cert_file, ssl_version)

def listen_addr_ssl(self, addr, readable_cb, readable_cb_args=(), idle_timeout_cb=None, 
        new_conn_cb=None, backlog=10, is_blocking=None):

    assert isinstance(addr, tuple) and len(addr) == 2
    assert isinstance(addr[0], str) and isinstance(addr[1], int)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
    except socket.error, e:
        self.log_error("setting TCP_NODELAY " + str(e))
    ip = socket.gethostbyname(addr[0])
    port = addr[1]
    sock.bind((ip, port))
    self.bind_addr = addr
    self.listen(sock, readable_cb=readable_cb, readable_cb_args=readable_cb_args, 
            idle_timeout_cb=idle_timeout_cb,
            new_conn_cb=new_conn_cb, backlog=backlog, accept_cb=self._accept_conn_ssl, is_blocking=is_blocking)
    return sock

def _do_handshake_server(self, csock, readable_cb, readable_cb_args, idle_timeout_cb, is_blocking=None):
    try:
        csock.do_handshake()
        #TODO: cleanup stalked socket fds during handshake
        if is_blocking is None:
            is_blocking = self.is_blocking
        if is_blocking:
            csock.setblocking(1)  # from non block to block
        self.put_sock(csock, readable_cb=readable_cb, readable_cb_args=readable_cb_args, 
                idle_timeout_cb=idle_timeout_cb, stack=False)
        return
    except(ssl.SSLError), e:
        if e.args[0] == ssl.SSL_ERROR_WANT_READ:
            self._poll.register(csock.fileno(), 'r', self._do_handshake_server, (csock, readable_cb, readable_cb_args, 
                idle_timeout_cb, is_blocking))
        elif e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
            self._poll.register(csock.fileno(), 'w', self._do_handshake_server, (csock, readable_cb, readable_cb_args,
                idle_timeout_cb, is_blocking))
        else:
            self.log_error("peer(%s) do_handshake exception %s, %s" % (csock.getpeername(), type(e), str(e)))
            csock.close()
    except(socket.error), e:
        self.log_error("peer(%s) do_handshake exception %s, %s" % (csock.getpeername(), type(e), str(e)))
        csock.close()

def _do_handshake_client(self, csock, ok_cb, err_cb, cb_args, stack, is_cb=True):
    try:
        csock.do_handshake()
        if is_cb:
            self._poll.unregister(csock.fileno(), 'all')
        self._exec_callback(ok_cb, (csock, ) + cb_args, stack)
        return
    except(ssl.SSLError), e:
        if e.args[0] == ssl.SSL_ERROR_WANT_READ:
            fd = csock.fileno()
            self._poll.register(csock.fileno(), 'r', self._do_handshake_client, 
                    (csock, ok_cb, err_cb, cb_args, stack, True))
        elif e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
            fd = csock.fileno()
            self._poll.register(csock.fileno(), 'w', self._do_handshake_client, 
                    (csock, ok_cb, err_cb, cb_args, stack, True))
        else:
            csock.close()
            if callable(err_cb):
                err_cb(ConnectNonblockError(e), *cb_args)
    except(socket.error), e:
        csock.close()
        if callable(err_cb):
            err_cb(ConnectNonblockError(e), *cb_args)


def _accept_conn_ssl(self, sock, readable_cb, readable_cb_args, idle_timeout_cb, new_conn_cb, is_blocking=None):
    """ socket will set FD_CLOEXEC upon accepted """
    _accept = sock.accept
    while True: 
    # have to make sure the socket is non-block, so we can accept multiple connection
        try:
            (csock, addr) = _accept()
            csock.setblocking(0)
            try:
                flags = fcntl.fcntl(csock, fcntl.F_GETFD)
                fcntl.fcntl(csock, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
            except IOError, e:
                self.log_error("cannot set FD_CLOEXEC on accepted socket fd, %s" % (str(e)))

            if callable(new_conn_cb):
                csock = new_conn_cb(csock, *readable_cb_args)
                if not csock:
                    continue
            csock = ssl.wrap_socket(csock, certfile=self.cert_file, server_side=True, ssl_version=self.ssl_version,
                    do_handshake_on_connect=False)
            self._do_handshake_server(csock, readable_cb, readable_cb_args, idle_timeout_cb, is_blocking=is_blocking)
        except(socket.error, ssl.SSLError), e:
            if e[0] in self._eagain_errno:
                return #no more
            if e[0] != errno.EINTR:
                msg = "accept error(unlikely): %s, %s"  % (type(e), str(e))
                self.log_error(msg)
    return



def connect_unblock_ssl(self, addr, ok_cb, err_cb=None, cb_args=(), syn_retry=None):
    stack = self._debug and traceback.extract_stack()[0:-1] or None
    def __on_conn(sock, *args):
        ssl_sock = ssl.wrap_socket(sock, do_handshake_on_connect=False, suppress_ragged_eofs=False)
        self._do_handshake_client(ssl_sock, ok_cb, err_cb, cb_args, stack, is_cb=False)
        return
    self.connect_unblock(addr, __on_conn, err_cb, cb_args, syn_retry=syn_retry)

def _funcToMethod(func,clas,method_name=None):
    """ only works for old type class """
    import new
    method = new.instancemethod(func,None,clas)
    if not method_name: method_name=func.__name__
    clas.__dict__[method_name]=method



def _inject_class(cls):
    _funcToMethod(connect_unblock_ssl, cls)
    _funcToMethod(_accept_conn_ssl, cls)
    _funcToMethod(_do_handshake_server, cls)
    _funcToMethod(_do_handshake_client, cls)
    _funcToMethod(listen_addr_ssl, cls)

_inject_class(SSLSocketEngine)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

#!/usr/bin/env python
# coding:utf-8

# @author frostyplanet@gmail.com
# @version $Id$
# @ socket engine which support synchronized and asynchronized i/o , with ssl support
#
import ssl
from socket_engine import *

class SSLSocketEngine (TCPSocketEngine):

    def __init__ (self, poll, cert_file, is_blocking=False, debug=False, ssl_version=ssl.PROTOCOL_SSLv23):
        TCPSocketEngine.__init__(self, poll, is_blocking=is_blocking, debug=debug)
        self.cert_file = cert_file
        self.ssl_version = ssl_version

    def _do_handshake_server (self, csock, readable_cb, readable_cb_args, idle_timeout_cb):
        try:
            csock.do_handshake ()
            #TODO: cleanup stalked socket fds during handshake
            if self.is_blocking:
                csock.setblocking (1)  # from non block to block
            self._put_sock (csock, readable_cb=readable_cb, readable_cb_args=readable_cb_args, 
                    idle_timeout_cb=idle_timeout_cb, stack=False, lock=False)
            return
        except (ssl.SSLError), e:
            if e.args[0] == ssl.SSL_ERROR_WANT_READ:
                self._poll.register (csock.fileno (), 'r', self._do_handshake_server, (csock, readable_cb, readable_cb_args, 
                    idle_timeout_cb))
            elif e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                self._poll.register (csock.fileno (), 'w', self._do_handshake_server, (csock, readable_cb, readable_cb_args,
                    idle_timeout_cb))
            else:
                self.log_error ("peer (%s) do_handshake exception %s, %s" % (csock.getpeername(), type(e), str(e)))
                csock.close ()
        except (socket.error), e:
            self.log_error ("peer (%s) do_handshake exception %s, %s" % (csock.getpeername(), type(e), str(e)))
            csock.close ()

    def _do_handshake_client (self, csock, ok_cb, err_cb, cb_args, stack, is_cb=True):
        try:
            csock.do_handshake ()
            if is_cb:
                self._poll.unregister (csock.fileno ())
            self._exec_callback (ok_cb, (csock, ) + cb_args, stack)
            return
        except (ssl.SSLError), e:
            if e.args[0] == ssl.SSL_ERROR_WANT_READ:
                self._poll.register (csock.fileno (), 'r', self._do_handshake_client, 
                        (csock, ok_cb, err_cb, cb_args, stack, True))
            elif e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                self._poll.register (csock.fileno (), 'w', self._do_handshake_client, 
                        (csock, ok_cb, err_cb, cb_args, stack, True))
            else:
                csock.close ()
                if callable (err_cb):
                    err_cb (ConnectNonblockError (e), *cb_args)
        except (socket.error), e:
            csock.close ()
            if callable (err_cb):
                err_cb (ConnectNonblockError (e), *cb_args)




    def _accept_conn (self, sock, readable_cb, readable_cb_args, idle_timeout_cb, new_conn_cb):
        """ socket will set FD_CLOEXEC upon accepted """
        _accept = sock.accept
        while True: 
        # have to make sure the socket is non-block, so we can accept multiple connection
            try:
                (csock, addr) = _accept ()
                csock.setblocking (0)
                try:
                    flags = fcntl.fcntl(csock, fcntl.F_GETFD)
                    fcntl.fcntl(csock, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
                except IOError, e:
                    self.log_error ("cannot set FD_CLOEXEC on accepted socket fd, %s" % (str(e)))

                if callable (new_conn_cb):
                    csock = new_conn_cb (csock, *readable_cb_args)
                    if not csock:
                        continue
                csock = ssl.wrap_socket (csock, certfile=self.cert_file, server_side=True, ssl_version=self.ssl_version,
                        do_handshake_on_connect=False)
                
                self._do_handshake_server (csock, readable_cb, readable_cb_args, idle_timeout_cb)
            except (socket.error, ssl.SSLError), e:
                if e[0] == errno.EAGAIN:
                    return #no more
                if e[0] != errno.EINTR:
                    msg = "accept error (unlikely): %s, %s"  % (type(e), str(e))
                    self.log_error (msg)
        return

    def _do_unblock_read (self, conn, ok_cb):
    
        """ return False to indicate need to reg conn into poll.
            return True to indicate no more to read, can be suc or fail.
            """
        if conn.status != ConnState.TOREAD:
            raise Exception ("you must have forgotten to watch_conn() or remove_conn()")
        expect_len = conn.rd_expect_len
        buf = conn.rd_buf
        _recv = conn.sock.recv
        while expect_len:
            try:
                temp = _recv (expect_len)
                _len = len (temp)
                if not _len:
                    conn.error = ReadNonBlockError (0, "peer close")
                    break
                expect_len -= _len
                buf += temp
            except (socket.error, ssl.SSLError), e:
                if e[0] == errno.EAGAIN or e[0] == ssl.SSL_ERROR_WANT_READ: 
                    conn.rd_buf = buf
                    conn.rd_expect_len = expect_len
                    conn.last_ts = self.get_time ()
                    return False#return and wait for next trigger
                elif e[0] == errno.EINTR:
                    continue
                conn.error = ReadNonBlockError (e)
                break
        conn.rd_expect_len = expect_len
        conn.rd_buf = buf
        conn.status = ConnState.USING
        if conn.error is not None:
            if callable(conn.unblock_err_cb): 
                conn.call_cb (conn.unblock_err_cb, (conn, ) + conn.unblock_cb_args, conn.unblock_tb)
                #error callback
            self._close_conn (conn) # NOTICE: we will close the conn after err_cb
        else:
            conn.call_cb (ok_cb, (conn, ) + conn.unblock_cb_args, conn.unblock_tb)
        return True


    def _do_unblock_readline (self, conn, ok_cb, max_len):
        """ return False to indicate need to reg conn into poll.
            return True to indicate no more to read, can be suc or fail.
            """
        if conn.status != ConnState.TOREAD:
            raise Exception ("you must have forgotten to watch_conn() or remove_conn()")
        buf = conn.rd_buf
        _recv = conn.sock.recv
        while True:
            try:
                temp = _recv (1)
                if temp == '':
                    conn.error = ReadNonBlockError (0, "peer close")
                    break
                buf += temp
                if temp == '\n':
                    break
                if len(buf) > max_len:
                    conn.error = ReadNonBlockError (0, "line maxlength exceed")
                    break
            except (socket.error, ssl.SSLError), e:
                if e[0] == errno.EAGAIN or e[0] == SSL.SSL_ERROR_WANT_READ: 
                    conn.rd_buf = buf
                    conn.last_ts = self.get_time ()
                    return False#return and wait for next trigger
                elif e[0] == errno.EINTR:
                    continue
                conn.error = ReadNonBlockError (e)
                break
        conn.rd_buf = buf
        conn.status = ConnState.USING
        if conn.error is not None:
            if callable(conn.unblock_err_cb): 
                conn.call_cb (conn.unblock_err_cb, (conn, ) + conn.unblock_cb_args, conn.unblock_tb)
                #error callback
            self._close_conn (conn) # NOTICE: we will close the conn after err_cb
        else:
            conn.call_cb (ok_cb, (conn, ) + conn.unblock_cb_args, conn.unblock_tb)
        return True


    def _do_unblock_write (self, conn, buf, ok_cb):
        """ return False to indicate need to reg conn into poll.
            return True to indicate no more to read, can be suc or fail.
            """
        if conn.status != ConnState.TOWRITE:
            raise Exception ("you must have forgotten to watch_conn() or remove_conn()")
        _len = len (buf)
        _send = conn.sock.send
        offset = conn.wr_offset
        while offset < _len:
            try:
                res = _send (buffer (buf, offset))
                if not res:
                    conn.error = WriteNonblockError (0, "peer close")
                    break
                offset += res
            except (socket.error, ssl.SSLError), e:
                if e[0] == errno.EAGAIN or e[0] == SSL.SSL_ERROR_WANT_WRITE:
                    conn.wr_offset = offset
                    conn.last_ts = self.get_time ()
                    return False#return and wait for next trigger
                elif e[0] == errno.EINTR:
                    continue
                conn.error = WriteNonblockError(e)
                break
        conn.wr_offset = offset
        conn.status = ConnState.USING
        if conn.error is not None:
            if callable (conn.unblock_err_cb): 
                conn.call_cb (conn.unblock_err_cb, (conn, ) + conn.unblock_cb_args, conn.unblock_tb) #error callback
            self._close_conn (conn) # NOTICE: we will close the conn after err_cb
        else:
            conn.call_cb (ok_cb, (conn, ) + conn.unblock_cb_args, conn.unblock_tb)
        return True



    def connect_unblock_ssl (self, addr, ok_cb, err_cb=None, cb_args=(), syn_retry=None):
        stack = self._debug and traceback.extract_stack()[0:-1] or None
        def __on_conn (sock, *args):
            ssl_sock = ssl.wrap_socket (sock, do_handshake_on_connect=False, suppress_ragged_eofs=False)
            self._do_handshake_client (ssl_sock, ok_cb, err_cb, cb_args, stack, is_cb=False)
            return
        self.connect_unblock (addr, __on_conn, err_cb, cb_args, syn_retry=syn_retry)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

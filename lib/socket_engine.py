#!/usr/bin/env python

#
# @file socket_egine.py 
# @author frostyplanet@gmail.com
# @version $Id$
# @ socket engine which support synchronized and asynchronized i/o , with replacable backend
#

import traceback
import socket
import errno
import threading
import time
from mylist import MyList
import sys
import fcntl

class ConnectNonblockError (socket.error):
    pass

class WriteNonblockError (socket.error):
    pass

class ReadNonBlockError (socket.error):
    pass


class ConnState (object):
    USING = 'u'
    IDLE = 'i' # wait for readable or writeable
    TOREAD = 'r'
    TOWRITE = 'w'
    # only Connection of the above statuses are in SocketEngine's _sock_dict
    EXTENDED_USING = 'eu'
    CLOSED = 'c'

class Connection (object):
    sock = None
    status = ConnState.EXTENDED_USING
    peer = None
    fd = None
    wr_offset = None
    rd_expect_len = None
    rd_buf = ""
    last_ts = None
    unblock_err_cb = None
    unblock_cb_args = None
    unblock_tb = None
    putsock_tb = None
    readable_cb = None
    readable_cb_args = None
    idle_timeout_cb = None
    call_cb = None
    error = None
#    sign = None # can be either 'r' or None, indicate to watch the socket readable/wriable when its idle

    def __init__ (self, sock, readable_cb=None, readable_cb_args=(), idle_timeout_cb=None):
        """ idle_timeout_cb will be callbacked with (engein, conn, *readable_cb_args)
        """
        self.sock = sock
        if callable (readable_cb):
            self.readable_cb = readable_cb
            self.readable_cb_args = readable_cb_args or ()
            self.sign = 'r'
        else:
            self.readable_cb = None
            self.readable_cb_args = ()
        self.idle_timeout_cb = callable (idle_timeout_cb) and idle_timeout_cb or None
        try:
            self.peer = sock.getpeername ()
        except socket.error:
            self.peer = None
        self.fd = sock.fileno()

    def close (self):
        if self.status != ConnState.CLOSED:
            self.status = ConnState.CLOSED
            if self.sock:
                self.sock.close ()
                self.sock = None

    def get_readbuf (self):
        return self.rd_buf


class SocketEngine (object):

    sock = None
    _poll = None
    _lock = None
    _sock_dict = None
    logger = None
    _rw_timeout = 0
    _idle_timeout = 0
    _last_checktimeout = None
    _checktimeout_inv = 0
    
    def __init__ (self, poll, is_blocking=True, debug=True):
        """ 
        sock:   sock to listen
            """
        self._debug = debug
        self._sock_dict = dict ()
        self._locker = threading.Lock ()
        self._lock = self._locker.acquire
        self._unlock = self._locker.release
        self._poll = poll
        self._cbs = MyList () # (handler, handler_args)
        self._pending_fd_ops = MyList () # (handler, conn)
        self._checktimeout_inv = 0
        self.get_time = time.time
        self.is_blocking = is_blocking

    def set_timeout (self, rw_timeout, idle_timeout):
        self._rw_timeout = rw_timeout
        self._idle_timeout = idle_timeout
        self._last_checktimeout = time.time ()
        temp_timeout = []
        if self._rw_timeout:
            temp_timeout.append (self._rw_timeout)
        if self._idle_timeout:
            temp_timeout.append (self._idle_timeout)
        if len(temp_timeout):
            self._checktimeout_inv = float (min (temp_timeout)) / 2
        else:
            self._checktimeout_inv = 0

    def set_logger (self, logger):
        self.logger = logger

    def log_error (self, msg):
        if self.logger:
            self.logger.warning (msg, bt_level=1)

    def put_sock (self, sock, readable_cb, readable_cb_args=(), idle_timeout_cb=None, stack=True):
        self._put_sock (sock, readable_cb, readable_cb_args, idle_timeout_cb, lock=True)

    def _put_sock (self, sock, readable_cb, readable_cb_args=(), idle_timeout_cb=None, stack=True, lock=False):
        conn = Connection (sock,
                readable_cb=readable_cb, readable_cb_args=readable_cb_args, 
                idle_timeout_cb=idle_timeout_cb)
        if stack and self._debug:
            conn.putsock_tb = traceback.extract_stack()[0:-1]
        if lock:
            self.watch_conn (conn)
        else:
            self._watch_conn (conn)
        return conn


    def watch_conn (self, conn):
        """ assume conn is already manage by server, register into poll """
        assert isinstance (conn, Connection)
        self._lock ()
        self._pending_fd_ops.append ((self._watch_conn, conn))
        self._unlock ()

    def _watch_conn (self, conn):
        self._sock_dict[conn.fd] = conn
        conn.last_ts = self.get_time ()
        conn.status = ConnState.IDLE
        if conn.sign == 'r':
            self._poll.register (conn.fd, 'r', conn.readable_cb, (conn, ) + conn.readable_cb_args)


    def remove_conn (self, conn):
        """ remove conntion from server """
        self._lock ()
        self._pending_fd_ops.append ((self._remove_conn, conn))
        self._unlock ()

    def _remove_conn (self, conn):
        conn.status = ConnState.EXTENDED_USING
        fd = conn.fd
        self._poll.unregister (fd)
        try:
            del self._sock_dict[fd]
        except KeyError:
            pass

    def close_conn (self, conn):
        """ remove an close connection """
        self._lock ()
        self._pending_fd_ops.append ((self._close_conn, conn))
        self._unlock ()

    def _close_conn (self, conn):
        fd = conn.fd
        self._poll.unregister (fd)
        try:
            del self._sock_dict[fd]
        except KeyError:
            pass
        conn.close ()

    def _accept_conn (self, sock, readable_cb, readable_cb_args, idle_timeout_cb, new_conn_cb):
        """ socket will set FD_CLOEXEC upon accepted """
        _accept = sock.accept
        _put_sock = self._put_sock
        while True: 
        # have to make sure the socket is non-block, so we can accept multiple connection
            try:
                (csock, addr) = _accept ()
                try:
                    flags = fcntl.fcntl(csock, fcntl.F_GETFD)
                    fcntl.fcntl(csock, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
                except IOError, e:
                    self.log_error ("cannot set FD_CLOEXEC on accepted socket fd, %s" % (str(e)))

                if self.is_blocking:
                    csock.settimeout (self._rw_timeout or None)
                else:
                    csock.setblocking (0)


                if callable (new_conn_cb):
                    csock = new_conn_cb (csock, *readable_cb_args)
                    if not csock:
                        continue
                _put_sock (csock, readable_cb=readable_cb, readable_cb_args=readable_cb_args, 
                        idle_timeout_cb=idle_timeout_cb, stack=False, lock=False)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    return #no more
                if e[0] != errno.EINTR:
                    msg = "accept error (unlikely): " + str(e)
                    self.log_error (msg)
        return

    def listen (self, sock, readable_cb, readable_cb_args=(), 
            idle_timeout_cb=None, new_conn_cb=None, backlog=20):
        """ readable_cb params:  (connObj, ) + readable_cb_args """
        assert isinstance (backlog, int)
        assert not readable_cb or callable (readable_cb)
        assert isinstance (readable_cb_args, tuple)
        assert idle_timeout_cb is None or callable (idle_timeout_cb)
        assert new_conn_cb is None or callable (new_conn_cb)
        assert sock and isinstance (sock, socket.SocketType)
        sock.setblocking (0) # set the main socket to nonblock
        try:
            flags = fcntl.fcntl(sock, fcntl.F_GETFD)
            fcntl.fcntl(sock, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
        except IOError, e:
            self.log_error ("cannot set FD_CLOEXEC on listening socket fd, %s" % (str(e)))
        self._poll.register (sock.fileno (), 'r', self._accept_conn, 
                (sock, readable_cb, readable_cb_args, idle_timeout_cb, new_conn_cb))
        sock.listen (backlog)

    def unlisten (self, sock):
        self._poll.unregister (sock.fileno ())
        sock.close ()


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
            except socket.error, e:
                if e[0] == errno.EAGAIN: 
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
            except socket.error, e:
                if e[0] == errno.EAGAIN: 
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
            except socket.error, e:
                if e[0] == errno.EAGAIN:
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

                
    def read_unblock (self, conn, expect_len, ok_cb, err_cb=None, cb_args=()):
        """ on timeout/error, err_cb will be called, the connection will be close afterward, 
        you must not do it you self, any operation that will lock the server is forbident in err_cb().
            ok_cb/err_cb param: conn, *cb_args
            """
        assert isinstance (conn, Connection)
        assert callable (ok_cb)
        assert not err_cb or callable (err_cb)
        assert expect_len > 0
        assert isinstance (cb_args, tuple)
        conn.error = None
        conn.status = ConnState.TOREAD
        conn.rd_expect_len = expect_len
        conn.rd_buf = ""
        conn.unblock_cb_args = cb_args
        conn.unblock_err_cb = err_cb
        conn.unblock_tb = self._debug and traceback.extract_stack ()[0:-1] or None
        conn.call_cb = self._callback_indirect
        if not self._do_unblock_read (conn, ok_cb):
            conn.last_ts = self.get_time ()
            self._lock ()
            fd = conn.fd
            conn.call_cb = self._exec_callback
            self._sock_dict[fd] = conn
            self._poll.register (fd, 'r', self._do_unblock_read, (conn, ok_cb, ))
            self._unlock ()


    def readline_unblock (self, conn, max_len, ok_cb, err_cb=None, cb_args=()):
        """ on timeout/error, err_cb will be called, the connection will be close afterward, 
            you must not do it yourself, any operation that will lock the server is forbident in err_cb ().
            ok_cb/err_cb param: conn, *cb_args
            """
        assert isinstance (conn, Connection)
        assert callable (ok_cb)
        assert not err_cb or callable (err_cb)
        assert isinstance (cb_args, tuple)
        conn.status = ConnState.TOREAD
        conn.rd_buf = ""
        conn.error = None
        conn.unblock_cb_args = cb_args
        conn.unblock_err_cb = err_cb
        conn.unblock_tb = self._debug and traceback.extract_stack ()[0:-1] or None
        conn.call_cb = self._callback_indirect
        if not self._do_unblock_readline (conn, ok_cb, max_len):
            conn.last_ts = self.get_time ()
            self._lock ()
            fd = conn.fd
            self._sock_dict[fd] = conn
            conn.call_cb = self._exec_callback
            self._poll.register (fd, 'r', self._do_unblock_readline, (conn, ok_cb, max_len))
            self._unlock ()

        
    def write_unblock (self, conn, buf, ok_cb, err_cb=None, cb_args=()):
        """ on timeout/error, err_cb will be called, the connection will be close afterward, 
            you must not do it yourself, any operation that will lock the server is forbident in err_cb ().
            ok_cb/err_cb param: conn, *cb_args
            """
        assert isinstance (conn, Connection)
        assert callable (ok_cb)
        assert not err_cb or callable (err_cb)
        assert isinstance (cb_args, tuple)
        conn.status = ConnState.TOWRITE
        conn.wr_offset = 0
        conn.error = None
        conn.unblock_err_cb = err_cb
        conn.unblock_cb_args = cb_args
        if self._debug:
            conn.unblock_tb = traceback.extract_stack ()[0:-1]
        conn.call_cb = self._callback_indirect
        if not self._do_unblock_write (conn, buf, ok_cb):
            conn.last_ts = self.get_time ()
            self._lock ()
            fd = conn.fd
            self._sock_dict[fd] = conn
            conn.call_cb = self._exec_callback
            self._poll.register (fd, 'w', self._do_unblock_write, (conn, buf, ok_cb))
            self._unlock ()


    def get_poll_size (self):
        """ not including the socket listening """
        res = None
        self._lock ()
        try:
            res = len (self._sock_dict)
        finally:
            self._unlock ()
        return res

    def _check_timeout (self):

        self._lock ()
        conns = self._sock_dict.values ()
        self._unlock ()
        now = self.get_time ()
        #the socking listening is not in _sock_dict, so it'll not be touched
        self._last_checktimeout = now
        def __is_timeout (conn):
            inact_time = now - conn.last_ts
            if conn.status == ConnState.IDLE and self._idle_timeout > 0  and inact_time > self._idle_timeout:
                return True
            elif (conn.status == ConnState.TOREAD or conn.status == ConnState.TOWRITE) \
                    and self._rw_timeout > 0 and inact_time > self._rw_timeout:
                return True
            return False
        timeout_list = filter (__is_timeout, conns)
        for conn in timeout_list:
            if conn.status == ConnState.IDLE:
                if callable (conn.idle_timeout_cb):
                    conn.error = socket.timeout ("idle timeout")
                    conn.idle_timeout_cb (conn, *conn.readable_cb_args)
            elif callable(conn.unblock_err_cb):
                conn.error = socket.timeout ("timeout")
                self._exec_callback (conn.unblock_err_cb, (conn,) + conn.unblock_cb_args, conn.unblock_tb)
            self._close_conn (conn)


    def _exec_callback (self, cb, args, stack=None):
        try:
            cb (*args)
        except Exception, e:
            msg = "uncaught %s exception in %s %s:%s" % (type(e), str(cb), str(args), str(e))
            if stack:
                l_out = stack
                exc_type, exc_value, exc_traceback = sys.exc_info()
                l_in = traceback.extract_tb (exc_traceback)[1:] # 0 is here
                stack_trace = "\n".join (map (lambda f: "in '%s':%d %s() '%s'" % f, l_out + l_in))
                msg += "\nprevious stack trace [%s]" % (stack_trace)
                self.logger.error (msg)
            else:
                self.logger.exception (msg)

    def _callback_indirect (self, cb, args, stack=None):
        self._cbs.append ((cb, args, stack))

    def poll (self, timeout=100):
        """ you need to call this in a loop, return fd numbers polled each time """

        #locking when poll may be prevent other thread to lock, but it's possible poll is not thread-safe, so we do the lazy approach
        __exec_callback = self._exec_callback
        hlist = self._poll.poll (timeout)
        for h in hlist:
            h[1] (*h[2])
        if self._cbs:
            _pop = self._cbs.popleft
            while self._cbs:
                _cb = _pop ()
                __exec_callback (*_cb)

        self._lock ()
        _pop = self._pending_fd_ops.popleft
        while self._pending_fd_ops:
            _cb = _pop ()
            __exec_callback (_cb[0], (_cb[1],))
        self._unlock ()

        if self._checktimeout_inv > 0 and time.time() - self._last_checktimeout > self._checktimeout_inv:
            self._check_timeout ()
        return len (hlist)


class TCPSocketEngine (SocketEngine):

    bind_addr = None

    def __init__ (self, poll, is_blocking=True, debug=False):
        SocketEngine.__init__(self, poll, is_blocking=is_blocking, debug=debug)

    def listen_addr (self, addr, readable_cb, readable_cb_args=(), idle_timeout_cb=None, 
            new_conn_cb=None, backlog=10):

        assert isinstance (addr, tuple) and len (addr) == 2
        assert isinstance (addr[0], str) and isinstance (addr[1], int)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.TCP_NODELAY, 1)
        except socket.error, e:
            self.log_error ("setting TCP_NODELAY " + str (e))
        ip = socket.gethostbyname(addr[0])
        port = addr[1]
        sock.bind ((ip, port))
        self.bind_addr = addr
        self.listen (sock, readable_cb=readable_cb, readable_cb_args=readable_cb_args, 
                idle_timeout_cb=idle_timeout_cb,
                new_conn_cb=new_conn_cb, backlog=backlog)
        return sock

    def connect_unblock (self, addr, ok_cb, err_cb=None, cb_args=(), syn_retry=None):
        """
            it's possible addr cannot be resolved and throw a error
            ok_cb param: sock, ...
            err_cb param: exception, ...
            will set FD_CLOEXEC on connected socket fd.
            """
        assert callable (ok_cb)
        assert err_cb == None or callable (err_cb)
        assert isinstance (cb_args, tuple)
        sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking (0)
        fd = sock.fileno ()
        res = None
        try:
            if syn_retry:
                sock.setsockopt(socket.SOL_TCP, socket.TCP_SYNCNT, syn_retry)
        except socket.error, e:
            self.log_error ("setting TCP_SYNCNT " + str(e))
        try:
            res = sock.connect_ex (addr)
            try:
                flags = fcntl.fcntl(sock, fcntl.F_GETFD)
                fcntl.fcntl(sock, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
            except IOError, e:
                self.log_error ("cannot set FD_CLOEXEC on connecting socket fd, %s" % (str(e)))
        except socket.error, e: # when addr resolve error, connect_ex will raise exception
            sock.close ()
            if callable(err_cb):
                err_cb (ConnectNonblockError (e), *cb_args)
            return

        stack = self._debug and traceback.extract_stack()[0:-1] or None
        def __on_connected (sock):
            res_code = sock.getsockopt (socket.SOL_SOCKET, socket.SO_ERROR)
            self._poll.unregister (fd)
            if res_code == 0:
                self._exec_callback (ok_cb, (sock, ) + cb_args, stack)
            else:
                sock.close ()
                err_msg = errno.errorcode[res_code]
                if callable(err_cb):
                    self._exec_callback (err_cb, (ConnectNonblockError (res_code, err_msg),) +cb_args, stack)
            return
        if res == 0:
            self._callback_indirect (ok_cb, (sock, ) + cb_args, stack)
        elif res == errno.EINPROGRESS:
            self._poll.register (fd, 'w', __on_connected, (sock, ))
        else:
            sock.close ()
            err_msg = errno.errorcode[res]
            if callable(err_cb):
                self._callback_indirect (err_cb, (ConnectNonblockError (res, err_msg), ) + cb_args, stack)
            return False



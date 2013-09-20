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
import thread
import time
import sys
import fcntl

class ConnectNonblockError(socket.error):
    pass

class WriteNonblockError(socket.error):
    pass

class ReadNonBlockError(socket.error):
    pass

class PeerCloseError(ReadNonBlockError):
    
    def __init__(self, *args):
        ReadNonBlockError.__init__(self, 0, "peer close")


class ConnState(object):
    USING = 'u'
    IDLE = 'i' # wait for readable or writeable
    TOREAD = 'r'
    TOWRITE = 'w'
    # only Connection of the above statuses are in SocketEngine's _sock_dict
    EXTENDED_USING = 'eu'
    CLOSED = 'c'

class Connection(object):
    sock = None
    engine = None
    status_rd = ConnState.EXTENDED_USING
    status_wr = None
    wr_offset = None
    rd_expect_len = None
    rd_buf = None
    last_ts = None
    read_err_cb = None
    write_err_cb = None
    read_cb_args = None
    write_cb_args = None
    read_tb = None
    write_tb = None
    putsock_tb = None
    readable_cb = None
    readable_cb_args = None
    idle_timeout_cb = None
    stack_count = 0
    error = None

    def __init__(self, sock, readable_cb=None, readable_cb_args=(), idle_timeout_cb=None):
        """ idle_timeout_cb will be callbacked with(engein, conn, *readable_cb_args)
        """
        self.sock = sock
        self.is_blocking = (sock.gettimeout() != 0)
        self.fd = self.sock.fileno()
        self.rd_ahead_buf = ""
        try:
            self.peer = self.sock.getpeername()
        except socket.error:
            pass

        if callable(readable_cb):
            self.readable_cb = readable_cb
            self.readable_cb_args = readable_cb_args or()
        else:
            self.readable_cb = None
            self.readable_cb_args = ()
        self.idle_timeout_cb = callable(idle_timeout_cb) and idle_timeout_cb or None

    def _close(self):
        if self.status_rd != ConnState.CLOSED:
            self.status_rd = ConnState.CLOSED
            if self.sock:
                self.sock.close()
        return

    def close(self):
        self.engine.close_conn(self)

    def watch(self):
        self.engine.watch_conn(self)

    def is_open(self):
        return self.status_rd != ConnState.CLOSED
    is_open = property(is_open)


    def get_readbuf(self):
        return self.rd_buf


class SocketEngine():

    """
        NOTE: 
            connect_unblock(), watch_conn(), remove_conn(), close_conn() is thread-safe.
            while read_unblock() / readline_unblock() / write_unblock() should be avoid calling in threads other than polling thread, they are not thread-safe,
    """

    sock = None
    _poll = None
    _lock = None
    _sock_dict = None
    logger = None
    _rw_timeout = 0
    _idle_timeout = 0
    _last_checktimeout = None
    _checktimeout_inv = 0
    _poll_tid = None
    _connection_cls = Connection

    STACK_DEPTH = 20  # recursive stack limit
    READAHEAD_LEN = 8 * 1024
    
    def __init__(self, poll, is_blocking=True, debug=True):
        """ 
        sock:   sock to listen
            """
        self._debug = debug
        self._sock_dict = dict()
        self._locker = threading.Lock()
        self._lock = self._locker.acquire
        self._unlock = self._locker.release
        self._poll = poll
        self._cbs = [] # (handler, handler_args)
        self._pending_ops = [] # (handler, conn)
        self._checktimeout_inv = 0
        self.get_time = time.time
        self.is_blocking = is_blocking
        self._eagain_errno = [errno.EAGAIN]
        self._error_exceptions = (socket.error, )

    def set_timeout(self, rw_timeout, idle_timeout):
        self._rw_timeout = rw_timeout
        self._idle_timeout = idle_timeout
        self._last_checktimeout = time.time()
        temp_timeout = []
        if self._rw_timeout:
            temp_timeout.append(self._rw_timeout)
        if self._idle_timeout:
            temp_timeout.append(self._idle_timeout)
        if len(temp_timeout):
            self._checktimeout_inv = float(min(temp_timeout)) / 2
        else:
            self._checktimeout_inv = 0

    def set_logger(self, logger):
        assert logger
        self.logger = logger

    def log_error(self, msg):
        if self.logger:
            self.logger.warning(msg, bt_level=1)
        else:
            print msg

    def log_exception(self, e):
        if self.logger:
            self.logger.exception(e)
        else:
            print e

    def put_sock(self, sock, readable_cb, readable_cb_args=(), idle_timeout_cb=None, stack=True):
        """  setup readable / idle callbacks for a passive socket, and watch for events, return Connection object """
        conn = self._connection_cls(sock,
                readable_cb=readable_cb, readable_cb_args=readable_cb_args, 
                idle_timeout_cb=idle_timeout_cb)
        conn.engine = self
        if stack and self._debug:
            conn.putsock_tb = traceback.extract_stack()[0:-1]
        self.watch_conn(conn)
        return conn


    def watch_conn(self, conn):
        """ register a Connection object and watch for readable event,
            if the socket is readable/error,  readable_cb will be called.
        """
        if not callable(conn.readable_cb):
            return
        if thread.get_ident() == self._poll_tid:
            if not conn.is_blocking and(conn.rd_ahead_buf or conn.error is not None):
#                if not res:
#                    try:
#                        conn.rd_ahead_buf += conn.sock.recv(1)
#                        res = True
#                    except socket.error, e:
#                        if e[0] not in self._eagain_errno:
#                            res = True
                self._poll.replace_read(conn.fd, self._read_ahead, (conn, ))
                self._conn_callback(conn, conn.readable_cb, (conn, ) + conn.readable_cb_args, count=1)
                return
            try:
                self._sock_dict[conn.fd] = conn
                conn.last_ts = self.get_time()
                conn.status_rd = ConnState.IDLE
                conn.stack_count = 0
                if conn.is_blocking:
                    self._poll.register(conn.fd, 'r', conn.readable_cb, (conn, ) + conn.readable_cb_args)
                else:
                    self._poll.register(conn.fd, 'r', self._unblock_readable, (conn, ))
            except Exception, e:
                self.logger.error("peer %s: watch conn error %s" % (conn.peer, str(e)))
        else:
            self._lock()
            self._pending_ops.append((self.watch_conn, conn))
            self._unlock()
            self._poll.wakeup()


    def _unblock_readable(self, conn):
        self._poll.replace_read(conn.fd, self._read_ahead, (conn, ))
        self._exec_callback(conn.readable_cb, (conn,) + conn.readable_cb_args)


    def remove_conn(self, conn):
        """ remove Connection from server, unregister all read events """
        if thread.get_ident() == self._poll_tid:
            conn.status_rd = ConnState.EXTENDED_USING
            fd = conn.fd
            if self._sock_dict.has_key(fd):
                del self._sock_dict[fd]
                try:
                    self._poll.unregister(fd, 'r')  # NOTE: the event is to be reconsider with libev
                except Exception, e:
                    self.logger.exception("peer %s: %s" % (conn.peer, str(e)))
        else:
            self._lock()
            self._pending_ops.append((self.remove_conn, conn))
            self._unlock()
            self._poll.wakeup()

    def close_conn(self, conn):
        """ remove and close connection """
        if thread.get_ident() == self._poll_tid:
            fd = conn.fd
            self._poll.unregister(fd, 'all')
            try:
                del self._sock_dict[fd]
            except KeyError:
                pass
            conn._close()
        else:
            self._lock()
            self._pending_ops.append((self.close_conn, conn))
            self._unlock()
            self._poll.wakeup()


    def _accept_conn(self, sock, readable_cb, readable_cb_args, idle_timeout_cb, new_conn_cb, is_blocking=False):
        """ socket will set FD_CLOEXEC upon accepted """
        _accept = sock.accept
        _put_sock = self.put_sock
        while True: 
        # have to make sure the socket is non-block, so we can accept multiple connection
            try:
                (csock, addr) = _accept()
                try:
                    flags = fcntl.fcntl(csock, fcntl.F_GETFD)
                    fcntl.fcntl(csock, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
                except IOError, e:
                    self.log_error("cannot set FD_CLOEXEC on accepted socket fd, %s" % (str(e)))
                if is_blocking:
                    csock.settimeout(self._rw_timeout or None)
                else:
                    csock.setblocking(0)

                if callable(new_conn_cb):
                    csock = new_conn_cb(csock, *readable_cb_args)
                    if not csock:
                        continue
                _put_sock(csock, readable_cb=readable_cb, readable_cb_args=readable_cb_args, 
                        idle_timeout_cb=idle_timeout_cb, stack=False)
            except socket.error, e:
                if e[0] == errno.EAGAIN:
                    return #no more
                if e[0] != errno.EINTR:
                    msg = "accept(sock %s %s) error(unlikely): %s" % (sock, readable_cb, str(e))
                    self.log_error(msg)
        return

    def listen(self, sock, readable_cb, readable_cb_args=(), 
            idle_timeout_cb=None, new_conn_cb=None, backlog=50, accept_cb=None, is_blocking=None):
        """ readable_cb :  (connObj, ) + readable_cb_args,
            new_conn_cb :  (socket)    # intercept a new connection socket, you may do authorization checking or handshake protocol, 
                    new_conn_cb returns True to tell the socketengine to perform put_sock(), or returns False to tell socketengine to ignore
            accept_cb:  override the default _accept_cb(), may used by derived classes
            is_blocking:   tell _accept_cb() to set the new socket to blocking mode or non-blocking mode 
        """
        assert isinstance(backlog, int)
        assert not readable_cb or callable(readable_cb)
        assert isinstance(readable_cb_args, tuple)
        assert idle_timeout_cb is None or callable(idle_timeout_cb)
        assert new_conn_cb is None or callable(new_conn_cb)
        assert sock and isinstance(sock, socket.SocketType)
        if is_blocking is None:
            is_blocking = self.is_blocking
        sock.setblocking(0) # set the main socket to nonblock
        if not callable(accept_cb):
            accept_cb = self._accept_conn
        try:
            flags = fcntl.fcntl(sock, fcntl.F_GETFD)
            fcntl.fcntl(sock, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
        except IOError, e:
            self.log_error("cannot set FD_CLOEXEC on listening socket fd, %s" % (str(e)))
        sock.listen(backlog)
        self._poll.register(sock.fileno(), 'r', accept_cb, 
                (sock, readable_cb, readable_cb_args, idle_timeout_cb, new_conn_cb, is_blocking))

    def unlisten(self, sock):
        self._poll.unregister(sock.fileno(), 'r')
        sock.close()

    def _read_ahead(self, conn, maxlen=0):
        if conn.error is not None:
            return True
        if maxlen == 0:
            maxlen = self.READAHEAD_LEN - len(conn.rd_ahead_buf)
        if maxlen <= 0:
            print "max reach"
            try:
                self._poll.unregister(conn.fd, 'r')
            except socket.error:
                pass
            return
        _recv = conn.sock.recv
        buf = conn.rd_ahead_buf
        eof = False
        while maxlen:
            try:
                _buf = _recv(maxlen)
                _l = len(_buf)
                if _l == 0:
                    eof = True
                    break
                buf += _buf
                maxlen -= _l
            except self._error_exceptions, e:
                if e.args[0] in self._eagain_errno:
                    break
                elif e.args[0] == errno.EINTR:
                    continue
                conn.error = e
                break
        conn.rd_ahead_buf = buf
        return eof

    
    def _do_unblock_read(self, conn, ok_cb, direct=False):
        """ return False to indicate need to reg conn into poll.
            return True to indicate no more to read, can be suc or fail.
            """
#        if conn.status_rd != ConnState.TOREAD:
#            raise Exception("not possible")
        expect_len = conn.rd_expect_len
        buf = conn.rd_buf
        _recv = conn.sock.recv
        while expect_len:
            try:
                temp = _recv(expect_len + 1)
                _len = len(temp)
                if not _len:
                    conn.error = PeerCloseError()
                    break
                if _len > expect_len: # always read more to support epoll ET mode, put the rest into read ahead buffer
                    buf += temp[0:expect_len]
                    conn.rd_ahead_buf += temp[expect_len:]
                    expect_len = 0
                else:
                    expect_len -= _len
                    buf += temp
            except self._error_exceptions, e:
                if e[0] in self._eagain_errno: 
                    conn.rd_buf = buf
                    conn.rd_expect_len = expect_len
                    conn.last_ts = self.get_time()
                    conn.stack_count = 0
                    if self._debug and not conn.read_tb:
                        conn.read_tb = traceback.extract_stack()[0:-1]
                    self._sock_dict[conn.fd] = conn
                    self._poll.register(conn.fd, 'r', self._do_unblock_read, (conn, ok_cb, ))
                    return False#return and wait for next trigger
                elif e[0] == errno.EINTR:
                    continue
                conn.error = ReadNonBlockError(e)
                break
        conn.rd_expect_len = expect_len
        conn.rd_buf = buf
        conn.status_rd = ConnState.USING
        conn.last_ts = self.get_time()
        if direct:
            return True
        # now we are done here, and seems read event is registered,
        # as I don't want to unregister the read event without knowing whether subsequence read will be happening and cause overhead,
        # replace the read event with _read_ahead() 
        if conn.error is None:
            self._poll.replace_read(conn.fd, self._read_ahead, (conn, ))
            self._conn_callback(conn, ok_cb, (conn, ) + conn.read_cb_args, stack=conn.read_tb)
        else:
            self._conn_callback(conn, conn.read_err_cb, (conn, ) + conn.read_cb_args, stack=conn.read_tb)


    def _do_unblock_readline(self, conn, ok_cb, max_len, direct=False):
        """ return False to indicate need to reg conn into poll.
            return True to indicate no more to read, can be suc or fail.
            """
#        if conn.status_rd != ConnState.TOREAD:
#            raise Exception("not possible")
        eof = self._read_ahead(conn, max_len)
        pos = conn.rd_ahead_buf.find('\n')
        conn.last_ts = self.get_time()
        if pos < 0:
            if len(conn.rd_ahead_buf) > max_len:
                conn.error = ReadNonBlockError(0, "line maxlength exceed")
            elif conn.error is None:
                if not eof:
                    if self._debug and not conn.read_tb:
                        conn.read_tb = traceback.extract_stack()[0:-1]
                    conn.stack_count = 0
                    self._sock_dict[conn.fd] = conn
                    self._poll.register(conn.fd, 'r', self._do_unblock_readline, (conn, ok_cb, max_len))
                    return False
                else:
                    conn.error = PeerCloseError()
        else:
            conn.rd_buf = conn.rd_ahead_buf[0:pos+1]
            conn.rd_ahead_buf = conn.rd_ahead_buf[pos+1:]

        conn.status_rd = ConnState.USING
        if conn.error is None and not conn.rd_ahead_buf:
            try:
                conn.rd_ahead_buf += conn.sock.recv(1)
            except self._error_exceptions:
                pass
        if direct:
            return True
        if conn.error is None:
            self._poll.replace_read(conn.fd, self._read_ahead, (conn, ))
            self._conn_callback(conn, ok_cb, (conn, ) + conn.read_cb_args, stack=conn.read_tb)
        else:
            self._conn_callback(conn, conn.read_err_cb, (conn, ) + conn.read_cb_args, stack=conn.read_tb)



    def _do_unblock_write(self, conn, buf, ok_cb, direct=False):
        """ return False to indicate need to reg conn into poll.
            return True to indicate no more to write, can be suc or fail.
            """
#        assert conn.status_wr
        _len = len(buf)
        _send = conn.sock.send
        offset = conn.wr_offset
        count = 0
        while offset < _len:
            try:
                res = _send(buffer(buf, offset))
                if not res:
                    conn.error = WriteNonblockError(0, "write zero ?")
                    break
                offset += res
            except self._error_exceptions, e:
                if e[0] in self._eagain_errno:
                    if count < 5:
                        count += 1
                        continue
                    conn.wr_offset = offset
                    conn.last_ts = self.get_time()
                    conn.stack_count = 0
                    if self._debug and not conn.write_tb:
                        conn.write_tb = traceback.extract_stack()[0:-1]
#                    self._lock()
                    self._sock_dict[conn.fd] = conn
                    self._poll.register(conn.fd, 'w', self._do_unblock_write, (conn, buf, ok_cb))
#                    self._unlock()
                    return False#return and poll for next trigger
                elif e[0] == errno.EINTR:
                    continue
                conn.error = WriteNonblockError(e)
                break
        conn.wr_offset = offset
        conn.status_wr = None
        conn.last_ts = self.get_time()
        if direct:
            return True
        # call by poll write event, should unregister
        self._poll.unregister(conn.fd, 'w')
        self._conn_callback(conn, conn.error is None and ok_cb or conn.write_err_cb, (conn, ) + conn.write_cb_args, stack=conn.write_tb)

    def read_avail(self, conn, max_len=0):
        """ read all available data from buffer until max_len is reached.
            returns buf,eof
                eof is true when peer closed """
        eof = self._read_ahead(conn, max_len)
        buf = conn.rd_ahead_buf
        conn.rd_ahead_buf = ""
        if not eof and conn.error is None:
            try:
                conn.rd_ahead_buf += conn.sock.recv(1024)
            except self._error_exceptions:
                pass
            self._poll.replace_read(conn.fd, self._read_ahead, (conn, ))
        return buf, eof


    def read_unblock(self, conn, expect_len, ok_cb, err_cb=None, cb_args=()):
        """ 
            read fixed len data, when done ok_cb() will be called.
            on timeout/error, err_cb will be called, the connection will be close afterward, 
            you must not do it you self, any operation that will lock the server is forbident in err_cb().
            ok_cb/err_cb param: conn, *cb_args
            """
        assert isinstance(conn, Connection)
        assert callable(ok_cb)
        assert expect_len > 0
        assert isinstance(cb_args, tuple)
        ahead_len = len(conn.rd_ahead_buf)
        if ahead_len:
            if conn.error is not None:
                return self._conn_callback(conn, err_cb, (conn, ) + cb_args, count=2)
            elif ahead_len >= expect_len:
                conn.rd_buf = conn.rd_ahead_buf[0:expect_len]
                conn.rd_ahead_buf = conn.rd_ahead_buf[expect_len:]
                return self._conn_callback(conn, ok_cb, (conn, ) + cb_args, count=2)
            else:
                conn.rd_buf = conn.rd_ahead_buf
                conn.rd_ahead_buf = ""
                conn.rd_expect_len = expect_len - ahead_len
        else:
            conn.rd_buf = ""
            conn.rd_expect_len = expect_len
        conn.read_tb = None
        if self._do_unblock_read(conn, ok_cb, direct=True):
            self._conn_callback(conn, conn.error is None and ok_cb or err_cb, (conn, ) + cb_args, count=2)
        else:
            conn.read_cb_args = cb_args
            conn.read_err_cb = err_cb
            conn.status_rd = ConnState.TOREAD


    def readline_unblock(self, conn, max_len, ok_cb, err_cb=None, cb_args=()):
        """ 
            read until '\n' is received or max_len is reached.
            if the line is longer than max_len, a Exception(line maxlength exceed) will be in conn.error which received by err_cb()
            on timeout/error, err_cb will be called, the connection will be close afterward, 
            you must not do it yourself, any operation that will lock the server is forbident in err_cb().
            ok_cb/err_cb param: conn, *cb_args
            NOTE: when done, you have to watch_conn or remove_conn by yourself
            """
        assert isinstance(conn, Connection)
        assert callable(ok_cb)
        assert not err_cb or callable(err_cb)
        assert isinstance(cb_args, tuple)
        conn.rd_buf = ""
        conn.read_tb = None
        if self._do_unblock_readline(conn, ok_cb, max_len, direct=True):
            self._conn_callback(conn, conn.error is None and ok_cb or err_cb, (conn, ) + cb_args, count=2)
        else:
            conn.read_cb_args = cb_args
            conn.read_err_cb = err_cb
            conn.status_rd = ConnState.TOREAD

        
    def write_unblock(self, conn, buf, ok_cb, err_cb=None, cb_args=()):
        """ on timeout/error, err_cb will be called, the connection will be close afterward, 
            you must not do it yourself, any operation that will lock the server is forbident in err_cb().
            ok_cb / err_cb cannot None
            ok_cb/err_cb param: conn, *cb_args
            NOTE: write only temporaryly register for write event, will not effect read
            """
        assert isinstance(conn, Connection)
        assert isinstance(cb_args, tuple)
        conn.wr_offset = 0
        conn.write_tb = None
        if self._do_unblock_write(conn, buf, ok_cb, direct=True):
            self._conn_callback(conn, conn.error is None and ok_cb or err_cb, (conn, ) + cb_args, count=2)
        else:
            conn.write_err_cb = err_cb
            conn.write_cb_args = cb_args
            conn.status_wr = ConnState.TOWRITE



    def get_poll_size(self):
        """ not including the socket listening """
        res = None
        self._lock()
        try:
            res = len(self._sock_dict)
        finally:
            self._unlock()
        return res

    def _check_timeout(self):
        self._lock()
        conns = self._sock_dict.values()
        self._unlock()
        now = self.get_time()
        #the socking listening is not in _sock_dict, so it'll not be touched
        self._last_checktimeout = now
        for conn in conns:
            inact_time = now - conn.last_ts
            if conn.status_rd == ConnState.IDLE and self._idle_timeout > 0 and inact_time > self._idle_timeout:
                if callable(conn.idle_timeout_cb):
                    conn.error = socket.timeout("idle timeout")
                    self._exec_callback(conn.idle_timeout_cb, (conn,) + conn.readable_cb_args)
                self.close_conn(conn)
            elif conn.status_rd == ConnState.TOREAD and self._rw_timeout > 0 and inact_time > self._rw_timeout:
                if callable(conn.read_err_cb):
                    conn.error = socket.timeout("read timeout")
                    self._exec_callback(conn.read_err_cb, (conn,) + conn.read_cb_args, conn.read_tb)
                self.close_conn(conn)
            elif conn.status_wr == ConnState.TOWRITE and self._rw_timeout > 0 and inact_time > self._rw_timeout:
                if callable(conn.write_err_cb):
                    conn.error = socket.timeout("write timeout")
                    self._exec_callback(conn.write_err_cb, (conn,) + conn.write_cb_args, conn.write_tb)
                self.close_conn(conn)

    def _conn_callback(self, conn, cb, args, stack=None, count=1):
        if conn.error is not None:
            self.close_conn(conn) #NOTICE: we will close the conn before err_cb
        if not callable(cb):
            return
        if conn.stack_count < self.STACK_DEPTH:
            conn.stack_count += count
            #try:
            cb(*args)
            #except Exception, e:
            #    msg = "uncaught %s exception in %s %s:%s" % (type(e), str(cb), str(args), str(e))
            #    if stack:
            #        l_out = stack
            #        exc_type, exc_value, exc_traceback = sys.exc_info()
            #        l_in = traceback.extract_tb(exc_traceback)[1:] # 0 is here
            #        stack_trace = "\n".join(map(lambda f: "in '%s':%d %s() '%s'" % f, l_out + l_in))
            #        msg += "\nprevious stack trace [%s]" % (stack_trace)
            #        self.log_error(msg)
            #    else:
            #        self.log_exception(msg)
            #    raise e
        else:
            conn.stack_count = 0
            self._lock()
            self._cbs.append((cb, args, stack))
            self._unlock()
            self._poll.wakeup()


    def _exec_callback(self, cb, args, stack=None):
        try:
            cb(*args)
        except Exception, e:
            msg = "uncaught %s exception in %s %s:%s" % (type(e), str(cb), str(args), str(e))
            if stack:
                l_out = stack
                exc_type, exc_value, exc_traceback = sys.exc_info()
                l_in = traceback.extract_tb(exc_traceback)[1:] # 0 is here
                stack_trace = "\n".join(map(lambda f: "in '%s':%d %s() '%s'" % f, l_out + l_in))
                msg += "\nprevious stack trace [%s]" % (stack_trace)
                self.log_error(msg)
            else:
                self.log_exception(msg)
                raise

    def poll(self, timeout=100):
        """ you need to call this in a loop, return fd numbers polled each time,
            timeout is in ms.
        """
        self._poll_tid = thread.get_ident()
        __exec_callback = self._exec_callback
        #locking when poll may be prevent other thread to lock, but it's possible poll is not thread-safe, so we do the lazy approach
        if self._pending_ops:
            self._lock()
            fd_ops = self._pending_ops
            self._pending_ops = []
            self._unlock()
            for _cb in fd_ops:
                _cb[0](_cb[1])
        if self._cbs:
            self._lock()
            cbs = self._cbs
            self._cbs = []
            self._unlock()
            for cb in cbs:
                __exec_callback(*cb)
        else:
            hlist = self._poll.poll(timeout)
            for h in hlist:
                __exec_callback(h[0], h[1])
        if self._checktimeout_inv > 0 and time.time() - self._last_checktimeout > self._checktimeout_inv:
            self._check_timeout()


class TCPSocketEngine(SocketEngine):

    bind_addr = None

    def __init__(self, poll, is_blocking=True, debug=True):
        SocketEngine.__init__(self, poll, is_blocking=is_blocking, debug=debug)

    def listen_addr(self, addr, readable_cb, readable_cb_args=(), idle_timeout_cb=None, 
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
                new_conn_cb=new_conn_cb, backlog=backlog, is_blocking=is_blocking)
        return sock

    def connect_unblock(self, addr, ok_cb, err_cb=None, cb_args=(), syn_retry=None):
        """
            it's possible addr cannot be resolved and throw a error
            ok_cb param: sock, ...
            err_cb param: exception, ...
            will set FD_CLOEXEC on connected socket fd.
            """
        assert callable(ok_cb)
        assert err_cb == None or callable(err_cb)
        assert isinstance(cb_args, tuple)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)
        fd = sock.fileno()
        res = None
        try:
            if syn_retry:
                sock.setsockopt(socket.SOL_TCP, socket.TCP_SYNCNT, syn_retry)
        except socket.error, e:
            self.log_error("setting TCP_SYNCNT " + str(e))
        try:
            res = sock.connect_ex(addr)
            try:
                flags = fcntl.fcntl(sock, fcntl.F_GETFD)
                fcntl.fcntl(sock, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
            except IOError, e:
                self.log_error("cannot set FD_CLOEXEC on connecting socket fd, %s" % (str(e)))
        except socket.error, e: # when addr resolve error, connect_ex will raise exception
            sock.close()
            if callable(err_cb):
                err_cb(ConnectNonblockError(e), *cb_args)
            return

        stack = self._debug and traceback.extract_stack()[0:-1] or None
        def __on_connected(sock):
            res_code = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            self._poll.unregister(fd, 'w')
            if res_code == 0:
                self._exec_callback(ok_cb, (sock, ) + cb_args, stack)
            else:
                sock.close()
                err_msg = errno.errorcode[res_code]
                if callable(err_cb):
                    self._exec_callback(err_cb, (ConnectNonblockError(res_code, err_msg),) +cb_args, stack)
            return
        if res == 0:
            self._exec_callback(ok_cb, (sock, ) + cb_args, stack)
        elif res == errno.EINPROGRESS:
            self._lock()
            self._poll.register(fd, 'w', __on_connected, (sock, ))
            self._unlock()
        else:
            sock.close()
            err_msg = errno.errorcode[res]
            if callable(err_cb):
                self._exec_callback(err_cb, (ConnectNonblockError(res, err_msg), ) + cb_args, stack)
            return False



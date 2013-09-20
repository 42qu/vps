#!/usr/bin/env python

# frostyplanet@gmail.com
# which is intend to used as backend of socket_engine.py

"""
    thread-safety should be ensured by upper level.
    Poll    will use python-epoll when it's installed, or else will fallback to select.poll()
    EPoll   available depending on whether select.epoll() exists.
    EVPoll  available depending on whether pyev is installed 
"""

import time
import os
import fcntl

try:
    import epoll as select # python-epoll provide the same interface as select.poll, which unlike 2.6's select.epoll
except ImportError:
    import select
import errno

class Poll(object):
    _handles = None
    _poll = None
    _in = select.POLLIN
    _out = select.POLLOUT
    _in_real = select.POLLIN | select.POLLPRI | select.POLLERR | select.POLLHUP | select.POLLNVAL
    _out_real = select.POLLOUT | select.POLLERR | select.POLLHUP | select.POLLNVAL
    _timeout_scale = 1

    def __init__(self, debug=False):
        self._handles = dict()
        self.debug = debug
        self._poll = select.poll()
        self._fd_r, self._fd_w = os.pipe()
        fcntl.fcntl(self._fd_r, fcntl.F_SETFL, os.O_NONBLOCK)
        self.register(self._fd_r, 'r', self._empty_fd)

    def _empty_fd(self):
        while True:
            try:
                os.read(self._fd_r, 256)
            except OSError, e:
                if e.args[0] in [errno.EAGAIN, errno.EINTR]:
                    return
                import traceback
                traceback.print_exc()

    def wakeup(self):
        os.write(self._fd_w, 't')


    def register(self, fd, event, handler, handler_args=()):
        """ event is one of ['r', 'w'] """
        data = self._handles.get(fd)
        if not data:
            if event == 'r':
                self._handles[fd] = [(handler, handler_args, ), None]
                self._poll.register(fd, self._in)
            else: # w
                self._handles[fd] = [None, (handler, handler_args, )]
                self._poll.register(fd, self._out)
        else: # one call to register can be significant overhead
            if event == 'r':
                if data[1] and not data[0]:
                    self._poll.modify(fd, self._in | self._out)
                data[0] = (handler, handler_args, )
            else: # w
                if data[0] and not data[1]:
                    self._poll.modify(fd, self._in | self._out)
                data[1] = (handler, handler_args, )
        return True

    def replace_read(self, fd, handler, handler_args=()):
        """ if read handler is register before, replace it, otherwise just do nothing """
        data = self._handles.get(fd)
        if data and data[0]:
            data[0] = (handler, handler_args, )
            return True
        return False
        

    def unregister(self, fd, event='r'):
        #assert event in ['r', 'w', 'rw', 'all']
        data = self._handles.get(fd)
        if not data:
            return
        if event == 'r':
            if not data[0]:
                return
            if data[1]: # write remains
                self._poll.modify(fd, self._out)
                data[0] = None
                return True
        elif event == 'w':
            if not data[1]:
                return
            if data[0]:
                self._poll.modify(fd, self._in)
                data[1] = None
                return True
        try:
            self._poll.unregister(fd)
        except KeyError:
            pass
        try:
            del self._handles[fd]
            return True
        except KeyError:
            pass


    def poll(self, timeout):
        """ 
            timeout is in milliseconds in consitent with poll.
            return [(function, arg), ...] to exec
            """
        while True:
            plist = self._poll.poll(timeout/ self._timeout_scale) # fd, event
            hlist = []
            for fd, event in plist:
                data = self._handles.get(fd)
                if not data:
                    raise Exception("bug, fd %s, event %s" % (fd, event))
                else:
                    if event & self._in_real:
                        if data[0]:
                            hlist.append(data[0])
                        elif event & self._in:
                            raise Exception("bug")
                    if event & self._out_real:
                        if data[1]:
                            hlist.append(data[1])
                        elif event & self._out:
                            raise Exception("bug")
            return hlist



if 'epoll' in dir(select):

    class EPoll(Poll):
        _handles = None
        _poll = None
        _in = select.EPOLLIN
        _out = select.EPOLLOUT
        _in_real = select.EPOLLIN | select.EPOLLRDBAND | select.EPOLLPRI | select.EPOLLHUP | select.EPOLLERR
        _out_real = select.EPOLLOUT | select.EPOLLWRBAND | select.EPOLLHUP | select.EPOLLERR 
        _timeout_scale = 1000.0


        def __init__(self, is_edge=True):
            self.is_edge = is_edge
            self._handles = dict()
            self._poll = select.epoll()
            if self.is_edge:
                self._in = select.EPOLLET | select.EPOLLIN
                self._out = select.EPOLLET | select.EPOLLOUT
            else:
                self._in = select.EPOLLIN
                self._out = select.EPOLLOUT
            self._fd_r, self._fd_w = os.pipe()
            fcntl.fcntl(self._fd_r, fcntl.F_SETFL, os.O_NONBLOCK)
            self.register(self._fd_r, 'r', self._empty_fd)

           

try:       
    import pyev
    class EVPoll(object):
        """
            pyev support is experimental.
            if you don't use pyev in combine with events otherthan Io, actually use Epoll() above is enough, the performence is almost the same.
        """

        def __init__(self, logger=None):
            #self._loop = pyev.default_loop(io_interval=timeout/1000.0, timeout_interval=timeout/1000.0)
            #self._loop = pyev.default_loop(timeout_interval=timeout)
            self._loop = pyev.default_loop()
            self._timer = pyev.Timer(0.01, 0, self._loop, self._timer_callback)
            self._timeout = 100
#            print self._loop.backend, pyev.EVBACKEND_EPOLL
            self._watchers = dict() # key is fd
            self._empty = []
            self.logger = logger
            self._in = pyev.EV_READ
            self._out = pyev.EV_WRITE

        def register(self, fd, event, handler, handler_args=()):
            """ event is one of ['r', 'w'] """
            watcher = self._watchers.get(fd)
            if not watcher:
                if event == 'r':
                    data = [(handler, handler_args, ), None]
                    _event = self._in
                else: # w
                    data = [None, (handler, handler_args, )]
                    _event = self._out
                watcher = pyev.Io(fd, _event, self._loop, callback=self._callback, data=data, priority=100)
                self._watchers[fd] = watcher
                watcher.start()
            else: # one call to register can be significant overhead
                data = watcher.data
                if event == 'r':
                    data[0] = (handler, handler_args, )
                    if data[1]:
                        watcher.set(fd, self._in | self._out)
                else: # w
                    data[1] = (handler, handler_args, )
                    if data[0]:
                        watcher.set(fd, self._in | self._out)
            return True

        def replace_read(self, fd, handler, handler_args=()):
            """ if read handler is register before, replace it, otherwise just do nothing """
            watcher = self._watchers.get(fd)
            if not watcher:
                return
            data = watcher.data
            if data and data[0]:
                data[0] = (handler, handler_args, )
                return True


        def unregister(self, fd, event='r'):
            #assert event in ['r', 'w', 'rw', 'all']
            watcher = self._watchers.get(fd)
            if not watcher:
                return
            data = watcher.data
            if event == 'r':
                if not data[0]:
                    return
                if data[1]:
                    watcher.set(fd, self._out)
                    data[0] = None
                    return True
            elif event == 'w':
                if not data[1]:
                    return
                if data[0]:
                    watcher.set(fd, self._in)
                    data[1] = None
                    return True
            try:
                del self._watchers[fd]
                watcher.stop()
                return True
            except Exception, e:
                print e
                pass

        def poll(self, timeout=100):
            """ this timeout is for interface compatibility, has no effect """
#            self._loop.start(pyev.EVRUN_ONCE | pyev.EVRUN_NOWAIT)
#            self._loop.start(pyev.EVRUN_NOWAIT)
            if timeout:
                if self._timeout != timeout:
                    self._timeout = timeout
                    self._timer.stop()
                    self._timer.set(timeout/1000.0, timeout/1000.0)
                    self._timer.start()
            self._loop.start(pyev.EVRUN_ONCE)
            return self._empty

        def _timer_callback(self, watcher, revents):
            pass

        def _callback(self, watcher, revents):
            data = watcher.data
            if not data:
                return
            if revents & self._in and data[0]:
                cb = data[0][0]
                if callable(cb):
                    try:
                        cb(*data[0][1])
                    except Exception, e:
                        if self.logger:
                            self.logger.exception(e)
            if revents & self._out and data[1]:
                cb = data[1][0]
                if callable(cb):
                    try:
                        cb(*data[1][1])
                    except Exception, e:
                        if self.logger:
                            self.logger.exception(e)


except ImportError:
    pass
    

                

def get_poll():
    if 'epoll' in dir(select):
        return EPoll()
    else:
        return Poll()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

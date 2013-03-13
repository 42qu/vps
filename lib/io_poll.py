#!/usr/bin/env python

# frostyplanet@gmail.com
# which is intend to used as backend of socket_engine.py

try:
    import epoll as select # python-epoll provide the same interface as select.poll, which unlike 2.6's select.epoll
except ImportError:
    import select
import threading
import errno

if 'epoll' in dir(select):

    class EPoll (object):
        """
            NOTE: it runs on edge-trigger mode.
            """

        _handles = None
        _poll = None


        def __init__ (self, is_edge=False):
            self.is_edge = is_edge
#            self._locker = threading.Lock ()
#            self._lock = self._locker.acquire
#            self._unlock = self._locker.release
            self._handles = dict ()
            self._poll = select.epoll ()
            self._find_handle = self._handles.get
            _in = select.EPOLLIN
            _out = select.EPOLLOUT
#            _in_out = select.EPOLLIN | select.EPOLLOUT
            if self.is_edge:
                _in = select.EPOLLET | _in
                _out = select.EPOLLET | _out
#                _in_out = select.EPOLLET | _in_out
            event_dict = {
                'r': _in,
                'w': _out,
            }
            self._get_ev = event_dict.__getitem__

        def register (self, fd, event, handler, handler_args=()):
            """ if event is 'rw', assume handler is readable callback, handler2 is writable callback
            """
            new_data = None
            data = self._handles.get (fd)
#            self._lock ()
#            try:
            if not data:
                ev = self._get_ev (event)
                assert ev != None
                self._poll.register (fd, ev)
            elif data[0] != event: # one call to register can be significant overhead
                ev = self._get_ev (event)
                assert ev != None
                self._poll.modify (fd, ev)
            handler_args = handler_args or ()
            # event, func, args
            self._handles[fd] = (event, handler, handler_args)
#            finally:
#                self._unlock ()

        def unregister (self, fd):
#            self._lock ()
            try:
                del self._handles[fd]
                self._poll.unregister (fd)
            except KeyError:
                pass
#            self._unlock ()

        def poll (self, timeout):
            """ 
                timeout is in milliseconds in consitent with poll.
                return function and arg to exec
                """
            _find_handle = self._find_handle
#            _in = select.EPOLLIN | select.EPOLLPRI | select.EPOLLERR | select.EPOLLHUP
#            _out = select.EPOLLOUT | select.EPOLLERR | select.EPOLLHUP
            while True:
                try:
                    plist = self._poll.poll (timeout/ 1000.0) # fd, event
#                    self._lock ()
                    hlist = [_find_handle (x[0]) for x in plist]
                    hlist = filter (lambda x:x, hlist)
#                    self._unlock ()
#                    for x in hlist:
#                        if x:
#                            x[1] (*x[2])
                    return hlist
                except select.error, e:
                    if e[0] == errno.EINTR:
                        continue
                    raise e
                



class Poll (object):
    _handles = None
    _poll = None
    event_dict = {
        'r': select.POLLIN,
        'w': select.POLLOUT,
#        'rw': select.POLLIN | select.POLLOUT
    }

    def __init__ (self, debug=False):
        self._handles = dict ()
        self.debug = debug
        self._poll = select.poll ()
#        self._locker = threading.Lock ()
#        self._lock = self._locker.acquire
#        self._unlock = self._locker.release
        self._find_handle = self._handles.get
        self._get_ev = self.event_dict.__getitem__

    def register (self, fd, event, handler, handler_args=()):
        """ if event is 'rw', assume handler is readable callback, handler2 is writable callback
        """
        data = self._handles.get (fd)
#        self._lock ()
#        try:
        if not data or data[0] != event: # one call to register can be significant overhead
            ev = self.event_dict.get (event)
            assert ev != None
            self._poll.register (fd, ev)
        new_data = None
        handler_args = handler_args or ()
        # event, func, args
        self._handles[fd] = (event, handler, handler_args)
#        finally:
#            self._unlock ()

    def unregister (self, fd):
#        self._lock ()
        try:
            del self._handles[fd]
            self._poll.unregister (fd)
        except KeyError:
            pass
#        self._unlock ()

    def poll (self, timeout):
        """ return function and arg to exec
            """
        _find_handle = self._find_handle
#        _in = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
#        _out = select.POLLOUT | select.POLLHUP | select.POLLERR 
        while True:
            try:
                plist = self._poll.poll (timeout) # fd, event
#                self._lock ()
                hlist = [_find_handle (x[0]) for x in plist]
                hlist = filter (lambda x:x, hlist)
#                self._unlock ()
                return hlist
            except select.error, e:
                if e[0] == errno.EINTR:
                    continue
                raise e
                

def get_poll ():
    if 'epoll' in dir(select):
        print "e"
        return EPoll ()
    else:
        return Poll ()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

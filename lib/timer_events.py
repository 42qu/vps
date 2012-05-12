#!/usr/bin/env python


# plan <frostyplanet@gmail.com>
# 2011-08-03
# last changed 2012-3-28

import sched
import threading
import time

class TimerEvents (object):
    """ thread-safe timer based on sched.
        test with python 2.4, 2.5, 2.7"""
    s = None
    logger = None
    th = None
    running = None

    def __init__ (self, timefunc, logger):
        assert callable (timefunc)
        self.timefunc = timefunc
        locker = threading.Lock ()
        self.cond = threading.Condition (locker)
        self.s = sched.scheduler (timefunc, self._delay)
        self.logger = logger
        self.running = False
        self.th = None
        self.event_dict = dict ()

    def _delay (self, inv):
        """ Our delay func will only delay one sec at most, acording to the behavior of sched. 
            Otherwise  adding a long event before the timer starting , you will not be able to schedule a more urgent event, 
            or not being able to stop the timer.
        """
        if inv == 0:
            return
        elif inv > 1:
            inv = 1
        time.sleep (inv) 

    def add_timer (self, inv, func, args=(), prio=1, first_delay=None):
        """ add_timer can only be called before poll """
        if first_delay is None:
            first_delay = inv
        if prio is None:
            prio = 1
        k = str(inv) + ":" + str(func)
        self.cond.acquire ()
        if not self.event_dict.has_key (k):
            self.event_dict[k] = self.s.enter (first_delay, prio, self._run_timer, (inv, prio, func, args))
#        self.logger.debug ("add timer event %s" % (k))
        self.cond.notify ()
        self.cond.release ()

    def _run_timer (self, inv, prio, func, args):
        try:
            func (*args)
        except Exception, e:
            self.logger.exception (e)
        k = str(inv) + ":" + str(func)
        self.cond.acquire ()
        self.event_dict[k] = self.s.enter (inv, prio, self._run_timer, (inv, prio, func, args))
        self.cond.release ()
        

    def add_once_timer (self, delay, func, args=(), prio=1):
        """ add_timer can only be called before poll """
        if prio is None:
            prio = 1
        k = str(delay) + ":" + str(func)
        self.cond.acquire ()
        if not self.event_dict.has_key (k):
            self.event_dict[k] = self.s.enter (delay, prio, self._run_once_timer, (delay, prio, func, args))
        self.cond.notify ()
        self.cond.release ()

    def _run_once_timer (self, delay, prio, func, args):
        try:
            func (*args)
            k = str(delay) + ":" + str(func)
            try:
                del self.event_dict[k]
            except KeyError:
                pass
        except Exception, e:
            self.logger.exception (e)


    def poll (self):
        while self.running:
            self.s.run ()
            self.cond.acquire ()
            if self.running and len(self.event_dict) == 0:
                self.cond.wait ()
            self.cond.release ()
    
    def start (self):
        if self.running:
            return
        self.running = True
        self.th = threading.Thread (target=self.poll, args=())
        self.th.setDaemon (1)
        self.th.start ()

    def stop (self):
        if not self.running:
            return
        assert self.th
        is_error = False
        self.cond.acquire ()
        for k, ev in self.event_dict.iteritems ():
            try:
                self.s.cancel (ev) # must cancel the current events to let the sched.run () exit
                self.logger.debug ("cancel timer event %s" % (k))
            except Exception, e: # i do not know the exception type
                # In what condition will a event not found in list? I really can't figure it out, but it did happend.
                self.logger.exception (e)
                is_error = True
        self.running = False
        self.cond.notify ()
        self.cond.release ()
#        if not is_error:
#            self.th.join ()
        self.th = None


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

#!/usr/bin/env python
#
# @file job_queue.py 
# @author frostyplanet@gmail.com
# @version $Id$
# @brief
#

import threading
import random

class Job (object):

    jobQ = None

    def get_tag (self):
        return ""
    
    def _set_active (self):
        assert self.jobQ
        self.jobQ.activate_job (self)

    def do (self):
        """ return True to make job pending again, 
        return False to indicate done """
        raise Exception, "not implemented"

class JobQueue (object):
    
    _lock = None
    _active_jobs = None
    _slept_jobs = None
    _pending_jobs = None
    _workers = None
    _logger = None

    def __init__ (self, logger=None):
        self._lock = threading.Lock ()
        self._cond = threading.Condition (self._lock)
        self._slept_jobs = dict ()
        self._active_jobs = dict ()
        self._pending_jobs = dict ()
        self._workers = list ()
        self._logger = logger
        self._stopping = False
        
    def _add_pending (self, job):
        #the _lock shall be acquire before calling this
        tag = job.get_tag ()
        if not self._pending_jobs.has_key (tag):
            self._pending_jobs[tag] = list () 
        self._pending_jobs[tag].append (job)
        self._cond.notifyAll ()

    def _get_next_job (self):
        """ scheduler for worker """
        job = None
        q = None
        queue_count = len (self._pending_jobs.values ())
        if queue_count == 1:
            q = self._pending_jobs.values()[0]
        elif queue_count > 1:
            l = list ()
            for tag, q in self._pending_jobs.iteritems ():
                q_size = len (q)
                if q_size:
                    l.append ((q_size, q))
            l.sort (lambda x, y:cmp (x[0], y[0]))
            if len(l):
                rand1 = random.randint (0, len(l) - 1)
                rand2 = random.randint (0, len(l) - 1)
                if rand2 < len (l) / 2:
                    rand1 = 0 
                q = l[rand1][1]
        if q and len(q):
            job = q[0]
            del q[0]
            self._active_jobs[id(job)] = job
        return job

    def put_job (self, job):
        """ for producer thread """
        assert isinstance (job, Job)
        job.jobQ = self
        self._lock.acquire ()
        self._add_pending (job)
        self._lock.release ()

    def activate_job (self, job):
        """ put slept job into pending """
        self._lock.acquire ()
        #chances are the job has been reactived during job.do() in active_jobs,
        #or in slept_jobs,
        # we must guarantee they are put to pending.
        if self._slept_jobs.has_key (id (job)):
            del self._slept_jobs[id (job)]
            self._add_pending (job)
        elif self._active_jobs.has_key (id (job)):
            del self._active_jobs[id (job)]
            self._add_pending (job)  # do the job again
        else: #it's in pending or never be put in the queue
            pass
        self._lock.release ()

    def __str__ (self):
        msg = "=========Job Queue Status============\n"
        self._lock.acquire ()
        msg += "--------pending------\n" 
        for tag, q in self._pending_jobs.iteritems ():
            msg += "tag: '%s' %d\n" % (tag, len(q))
            for job in q:
                msg += "%s\n" % (str (job))
        msg += "--------active (%d) -------\n" % (len (self._active_jobs))
        for job in self._active_jobs.itervalues ():
            msg += "%s\n" % (str (job))
        msg += "--------slept (%d) --------\n" % (len (self._slept_jobs)) 
        for job in self._slept_jobs.itervalues ():
            msg += "%s\n" % (str (job))
        self._lock.release ()
        msg += "====================================\n"
        return msg

    def get_jobs_count (self):
        #return job counts in (pending_count, active_count, slept_count)
        slept = 0
        pending = 0
        active = 0
        self._lock.acquire ()
        for tag, q in self._pending_jobs.iteritems ():
            pending += len(q)
        active = len (self._active_jobs)
        slept = len (self._slept_jobs)
        self._lock.release ()
        return (pending, active, slept)

    def get_slept_jobs (self):
        #return slept job in a list
        slept_jobs = None
        self._lock.acquire ()
        slept_jobs = self._slept_jobs.values ()
        self._lock.release ()
        return slept_jobs
        

    def _worker_thread (self):
        self._cond.acquire ()
        while not self._stopping:
            job = self._get_next_job ()
            if not job:
                self._cond.wait ()
                continue
            self._cond.release ()
            job_res = False
            try:
                job_res = job.do ()
            except Exception, e:
                msg = "job:%s, error %s" % (str(job), str (e))
                if self._logger:
                    self._logger.exception_ex (msg)
                else:
                    print msg
            self._cond.acquire ()
            if self._active_jobs.has_key (id (job)):
                del self._active_jobs[id (job)]
                if job_res:
                    self._slept_jobs[id(job)] = job
            else: #the job has been reactived during job.do()
            # we must guarantee they are put to pending.
                pass
        self._cond.release ()
        return
        
    def start_worker (self, th_num):
        for i in xrange (0, th_num):
            th = threading.Thread (target=self._worker_thread, args=())
            self._workers.append (th)
            th.setDaemon (1)
            th.start ()
   
    def stop (self):
        self._stopping = True 
        self._cond.acquire ()
        self._cond.notifyAll () # get all sleeping worker up
        self._cond.release ()
        for th in self._workers:
            th.join ()


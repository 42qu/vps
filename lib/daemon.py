#!/usr/bin/env python


import os
import time
import sys
import signal


def _fork_service (func, pid_file, log_func=None):
    """ on suc return pid, on error return None 
        (when pidfile cannot be saved, kill the process and return None)"""
    assert pid_file
    pid = None
    try:
        pid = os.fork ()
    except OSError, e:
        if callable (log_func): log_func ("cannot fork service: %s" % (str (e)))
        return None
    if not pid:
        #service child
        signal.signal (signal.SIGCHLD, signal.SIG_DFL)
        # set SIGCHLD to default action, 
        # otherwise SIG_IGN will conflict with subprocess module
        prog_name = sys.argv[0]
        sys.argv[0] = prog_name + " [service]"
        try:
            os.setsid ()
        except OSError, e: 
            if callable (log_func): 
                log_func ("setsid : %s" % (str (e)))
        si = open("/dev/null", 'r')
        os.dup2(si.fileno(), sys.stdin.fileno())
        so = open("/dev/null", 'a+', 0)
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(so.fileno(), sys.stderr.fileno())
        try:
            func ()
            os._exit (0)
        except Exception, e:
            if callable (log_func): log_func ("main_func caught exception: %s" % (str (e)))
            os._exit (1)
    else:
        #parent
        try:
            write_pid (pid_file, pid)
        except IOError, e:
            if callable (log_func): log_func ("cannot save service's pidfile: %s" % (str (e)))
            os.kill (pid, signal.SIGKILL)
            return None
        return pid


def daemonize (func, pid_file, mon_pid_file, log_func=None):
    assert callable (func)
    generation = 0
    mon_pid = None
    signal.signal (signal.SIGCHLD, signal.SIG_IGN)
    if mon_pid_file:
        #need monitor
        try:
            mon_pid = os.fork ()
        except OSError, e:
            if callable (log_func): log_func ("cannot fork monitor: %s" % (str (e)))
            sys.exit (1)
        if mon_pid:
            #parent
            try:
                write_pid (mon_pid_file, mon_pid)
            except IOError, e:
                if callable (log_func): log_func ("cannot save monitor's pidfile: %s" % (str (e)))
                os.kill (mon_pid, signal.SIGKILL)
                sys.exit (1)
            return
        else:
            #monitor child
            prog_name = sys.argv[0]
            sys.argv[0] = prog_name + " [monitor]"
            try:
                os.setsid ()
            except OSError, e: 
                pass
            pid =  _fork_service (func, pid_file, log_func)
            if not pid:
                print "retry in 2 sec, go silent"
            else:
                print "service started, go silent" 

            si = open("/dev/null", 'r')
            os.dup2(si.fileno(), sys.stdin.fileno())
            so = open("/dev/null", 'a+', 0)
            os.dup2(so.fileno(), sys.stdout.fileno())
            os.dup2(so.fileno(), sys.stderr.fileno()) 
            while True:
                time.sleep (2)
                if not pid or not check_alive (pid):
                    generation += 1
                    if callable (log_func): log_func ("service die, trying to fork another (%d)" % (generation))
                    sys.argv[0] = prog_name
                    pid = _fork_service (func, pid_file, log_func)
    else:
        # no monitor
        if _fork_service (func, pid_file, log_func):
            print "started"


def read_pid (pid_file):
    """ if pid_file not exist, return None """
    assert pid_file
    try:
        f = open (pid_file, "r")
        pid = f.readline ()
        f.close ()
        pid = int (pid.strip ("\n"))
        if pid > 0: return pid
        else: return None
    except IOError:
        return None
    
    
def write_pid (pid_file, pid):
    assert pid and pid_file
    f = open (pid_file, "w")
    f.write (str(pid))
    f.close ()

def check_alive (pid):
    """ check process alive, return True or False """
    assert isinstance (pid, int)
    try:
        pgid = os.getpgid (pid)
        if pgid >= 0: return True
        return False
    except OSError, e:
        return False

def stop (sig, pid_file, mon_pid_file):
    """ if service process not exist, return False, otherwise return True
        """
    assert isinstance (sig, int) or sig == None
    assert pid_file
    if sig == None:
        sig = signal.SIGTERM
    if mon_pid_file:
        mon_pid = _check_status (mon_pid_file)
        if mon_pid:
            os.kill (mon_pid, signal.SIGKILL)
            print "kill monitor pid %d" % (mon_pid)
    pid = _check_status (pid_file)
    if pid:
        os.kill (pid, sig)
        print "kill service pid %d, with signal %s, waiting it to stop" % (pid, str(sig))
        while check_alive (pid):
            time.sleep (0.3)
        print "stopped [OK]"
        return True
    if mon_pid:
        print "service process missing, monitor stopped"
        return False
    print "not started"
    return False

def _check_status (pid_file):
    """ read pid_file and check whether pid alive, if so return pid, otherwise return None 
        """
    assert pid_file
    pid = read_pid (pid_file)
    if pid and check_alive (pid):
        return pid
    return None

def status (pid_file, mon_pid_file):
    """ on running ok return 1, on stopped return 0, on error return -1
        """
    assert pid_file
    mon_ok = True
    if mon_pid_file and not _check_status (mon_pid_file):
        mon_ok = False
    ok = _check_status (pid_file)
    if ok and mon_ok:
        print "running fine"
        return 1
    elif mon_ok and not ok:
        print "mon is running, but not service, suggest checking log"
        return -1
    elif not mon_ok and ok:
        print "service running, but not the monitor"
        return -1
    else:
        print "stopped"
        return 0

def start (func, pid_file, mon_pid_file, log_func=None):
    pid = _check_status (mon_pid_file or pid_file)
    if pid:
        print "already started"
    else:
        daemonize (func, pid_file, mon_pid_file, log_func)

def cmd_wrapper (action, main, usage, logger, log_dir, run_dir, pid_file, mon_pid_file):
    if not os.path.exists (log_dir):
        os.makedirs (log_dir, 0700)
    if not os.path.exists (run_dir):
        os.makedirs (run_dir, 0700)
    os.chdir (run_dir)

    def _log_err (msg):
        print msg
        logger.exception (msg)
        return

    def _start ():
        start (main, pid_file, mon_pid_file, _log_err)
        return

    def _stop ():
        stop (signal.SIGTERM, pid_file, mon_pid_file)
        return

    if action == "start":
        _start ()
    elif action == "stop":
        _stop ()
    elif action == "restart":
        _stop ()
        time.sleep (2)
        _start ()
    elif action == "status":
        status (pid_file, mon_pid_file)
    elif action == "run":
        main ()
    else:
        usage ()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

#!/usr/bin/env python
#
import os
import time
import StringIO
import select
import fcntl
import errno
import signal

# This module provides the function similar to subprocess, with optional timeout setting,
# and it's intended to work with python 2.3 or above

try:
    MAXFD = os.sysconf('SC_OPEN_MAX')
except (AttributeError, ValueError):
    MAXFD = 256


class CommandException (Exception):

    def __init__ (self, command, msg, status=None):
        """status is for exit status"""
        Exception.__init__ (self)
        if not isinstance (command, basestring):
            self.command = command.join (" ")
        else:
            self.command = command
        self.status = status
        self.msg = msg

    def __str__ (self):
        if self.status is not None:
            output = "cmd '%s' exit %d, %s" % (self.command, self.status, self.msg)
        else:
            output = "cmd '%s', %s" % (self.command, self.msg)
        return output

class CommandTimeoutException (CommandException):

    def __init__ (self, *args):
        CommandException.__init__ (self, *args)

    def __str__ (self):
        output = "cmd '%s' %s" % (self.command, self.msg)
        return output

class Command (object):

    cmd_line = None
    args = None
    _timeout = None
    PIPE_BUFSIZE = 4096
    _input_buf = ""

    _stdin = None
    _stdout = None
    _stderr = None
    _out_stream = None
    _err_stream = None
    _rdset = None
    _wrset = None
    _start_ts = None
    _last_ts = None
    _pid = None
    _status = None # which is the process exit status
    _exitcode = None # which returned by os.waitpid

    _res_code = None
    _res_out = None
    _res_err = None

    def __init__ (self, cmd, timeout=None, close_fds=True):
        if timeout > 0:
            self.timeout = timeout
            self._timeout = timeout
        else:
            self._timeout = None # must not be 0
        if isinstance (cmd, basestring):
            self.cmd_line = cmd
            self.args = ['/bin/sh', '-c', cmd]
        else:
            self.cmd_line = ' '.join (cmd)
            self.args = cmd
        self.close_fds = close_fds and True or False

    pid = property (lambda self: self._pid)
    
    def _close_fd (self):
        try:
            fdl = [int(i) for i in os.listdir('/proc/self/fd')]
        except OSError:
            fdl = range(1024)
        for i in [i for i in fdl if i > 2]:
            try: 
                os.close(i)
            except OSError:
                pass

    def start (self):
        stdin, self._stdin = os.pipe()
        self._stdout, stdout = os.pipe()
        self._stderr, stderr = os.pipe()
        try:
            self._pid = os.fork ()
        except OSError, e:
            raise CommandException (self.cmd_line, "fork child error, %s" % (e.args[0]))
        if self._pid == 0: #child
            os.dup2(stdin, 0)
            os.dup2(stdout, 1)
            os.dup2(stderr, 2)
            os.close (self._stdin)
            os.close (self._stdout)
            os.close (self._stderr)
            if self.close_fds:
                self._close_fd ()

            #on timeout kill the whole process group, so create new PG first
            os.setsid ()
            try:
                os.execvp(self.args[0], self.args)
            finally:
                os._exit(1)
        else: #parent
            os.close (stdin)
            os.close (stdout)
            os.close (stderr)
            fcntl.fcntl (self._stdin, fcntl.F_SETFL, os.O_NONBLOCK)
            fcntl.fcntl (self._stdout, fcntl.F_SETFL, os.O_NONBLOCK)
            fcntl.fcntl (self._stderr, fcntl.F_SETFL, os.O_NONBLOCK)
            self._out_stream = StringIO.StringIO ()
            self._err_stream = StringIO.StringIO ()
            self._rdset = [self._stdout, self._stderr]
            self._wrset = []
            self._wrset.append (self._stdin)
            self._last_ts = self._start_ts = time.time ()
            

    def cleanup (self):
        self._out_stream.close ()
        self._err_stream.close ()
        if not self._stdin is None:
            os.close (self._stdin)
            self._stdin = None
        if not self._stdout is None:
            os.close (self._stdout)
            self._stdout = None
        if not self._stderr is None:
            os.close (self._stderr)
            self._stderr = None

    def _check_timeout (self):
        if self._timeout > 0:
            now = time.time ()
            time_pass = now - self._last_ts
            if time_pass < self._timeout:
                self._timeout -= time_pass
                self._last_ts = now
                return
            self.cleanup ()
            pgid = os.getpgid (self._pid)
            os.killpg (pgid, signal.SIGKILL)
            raise CommandTimeoutException (self.cmd_line, "exec timeout, %f sec passed" % (now - self._start_ts))

    def _wait_child (self, isblock): 
        """ if the child has finished, return True, otherwise False """
        if not self._exitcode is None:
            return True
        while True:
            try:
                if isblock:
                    _id, self._exitcode = os.waitpid (self._pid, 0)
                    return True
                else:
                    _id, code = os.waitpid (self._pid, os.WNOHANG)
                    if _id == 0:
                        return False
                    else:
                        self._exitcode = code
                        return True
            except OSError, e:
                if e.args[0] == errno.EINTR:
                    continue
                raise CommandException (self.cmd_line, "wait error, %s" % (str (e)))

    def _proc_result (self):
        self._wait_child (True)
        output = self._out_stream.getvalue ()
        err = self._err_stream.getvalue ()
        self.cleanup ()
        if os.WIFSIGNALED (self._exitcode):
            raise CommandException (self.cmd_line, "terminated by signal, %d" %
                (os.WSTOPSIG (self._exitcode)))
        elif os.WIFEXITED (self._exitcode): 
            status = os.WEXITSTATUS (self._exitcode)
        elif os.WIFSTOPPED (self._exitcode):
            raise CommandException (self.cmd_line, "stopped by job control")
        else:      
            raise CommandException (self.cmd_line, "terminated abnormally")
        self._res_code = status
        self._res_out = output
        self._res_err = err
        return (status, output, err)

    def _poll (self, timeout=0):
        try:
            rlist, wlist, xlist = select.select (self._rdset, self._wrset, [], timeout or 0)
            if self._stdin in wlist:
                try:
                    res = os.write (self._stdin, self._input_buf)
                    self._input_buf = self._input_buf[res:]
                    if not self._input_buf:
                        self._wrset.remove (self._stdin)
                        os.close (self._stdin)
                        self._stdin = None
                except IOError, e:
                    if e.args[0] == errno.EPIPE:
                        self._wrset.remove (self._stdin)
                        os.close (self._stdin)
                        self._stdin = None
                    else:
                        raise e
            if self._stdout in rlist: 
                buf = os.read (self._stdout, self.PIPE_BUFSIZE)
                if not buf:
                    self._rdset.remove (self._stdout)
                else:
                    self._out_stream.write (buf)
            if self._stderr in rlist:
                buf = os.read (self._stderr, self.PIPE_BUFSIZE)
                if not buf:
                    self._rdset.remove (self._stderr)
                else:
                    self._err_stream.write (buf)
            self._check_timeout ()
        except select.error, e:
            if e.args[0] != errno.EINTR:
                self.cleanup ()
                raise CommandException (self.cmd_line, "select error, %s" % (str (e)))
        except IOError, e:
            if e.args[0] != errno.EINTR:
                self.cleanup ()
                raise CommandException (self.cmd_line, "pipe error, %s" % (str (e)))

    def poll (self, timeout=None):
        """ if the child has finished, return exitcode, otherwise None.
            if timeout > 0, then block until timeout (seconds)
        """
        res = self._wait_child (False)
        if res:
            self._poll (0)
            return self._res_code
        else:
            self._poll (timeout)
            return None


    def wait (self):
        while self._rdset or self._wrset:
            if self._wait_child (False):
                self._poll (0)
                return self._proc_result ()
            else:
                self._poll (self._timeout or 0.3)
            # if stdout & stderr is closed by child
        if self._timeout > 0:
            while not self._wait_child (False):
                self._check_timeout ()
                try:
                    select.select ([], [], [], self._timeout)
                except select.error, e:
                    if not e.args[0] == errno.EINTR:
                        self.cleanup ()
                        raise CommandException (self.cmd_line, "select error, %s" % (str (e)))
        else:
            self._wait_child (True)
        return self._proc_result ()

    def get_result (self):
        return (self._res_code, self._res_out, self._res_err)

    def read_from (self):
        """ if command terminate by signal, raise CommandException;
            otherwise return (exit_code, output)"""
        self.start ()
        self.wait ()
        if self._res_code != 0:
            if self._res_err:
                return (self._res_code, self._res_err)
        return (self._res_code, self._res_out)

    def read_from_ex (self):
        self.start ()
        return self.wait ()


    def write_to (self, input_str):
        """ open a pipe of command and write input_str to it
            if command not exited using exit(), raise CommandException;
                otherwise return (exit_code, output)
        """
        self._input_buf = input_str
        self.start ()
        self.wait ()
        if self._res_code != 0:
            if self._res_err:
                return (self._res_code, self._res_err)
        return (self._res_code, self._res_out)


    def write_to_ex (self, input_str):
        self._input_buf = input_str
        self.start ()
        return self.wait ()

##########

def search_path (prog_name):
    """ search an executable in system's PATH, return the abs path """
    path = os.environ.get ("PATH")
    paths = []
    if path:
        paths = path.split (":")
    if len (paths) == 0:
        raise Exception ("PATH environment not exists")
    for p in paths:
        bin_path = os.path.join (p, prog_name)
        if os.path.isfile (bin_path) and os.access (bin_path, os.X_OK):
            return bin_path 
    return None

def call_cmd (cmd):
    c = Command (cmd)
    status, out = c.read_from ()
    if status == 0:
        return out.strip ("\r\n")
    raise CommandException (cmd, msg=out, status=status)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

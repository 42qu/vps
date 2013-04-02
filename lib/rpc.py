#!/usr/bin/env python
# coding:utf-8

import pickle
import ssl
from net_io import NetHead
import socket
import ssl
import time


class RPC_Exception (Exception):

    pass

class RPC_Req (object):

    def __init__ (self, func_name, args, k_args):
        assert isinstance (func_name, str)
        assert isinstance (args, (tuple, list))
        assert isinstance (k_args, dict)
        self.func_name = func_name
        self.args = args
        self.k_args = k_args

    def serialize (self):
        return pickle.dumps ((self.func_name, self.args, self.k_args))

    def __str__ (self): 
        karr = map (lambda x: "%s=%s" % (x[0], x[1]),  self.k_args.items ())
        s = "%s( %s" % (self.func_name, ", ".join (map (str, self.args)))
        if karr:
            s += ", " + ", ".join (karr)
        s += " )"
        return s
    
    @classmethod
    def deserialize (cls, buf):
        data = None
        try:
            data = pickle.loads (buf)
        except Exception, e:
            raise RPC_Exception ("unpickle failed %s" % (str(e)))
        if len(data) != 3:
            raise RPC_Exception ("invalid request format")
        args = data[1] or ()
        k_args = data[2] or dict ()
        if not isinstance (args, (tuple, list)) or not isinstance (k_args, dict):
            raise RPC_Exception ("invalid request format")
        for arg in args:
            if not isinstance (arg, (int, float, basestring, dict, list, tuple)):
                raise RPC_Exception ("insecure request")
        for k, arg in k_args.iteritems ():
            if not isinstance (k, basestring) or \
                    not isinstance (arg, (int, float, basestring, dict, list, tuple)):
                raise RPC_Exception ("insecure request")
        return cls (data[0], args, k_args)

class RPC_Resp (object):
    
    def __init__ (self, retval, error):
        self.retval = retval
        self.error = error and str(error) or None
    
    def serialize (self):
        return pickle.dumps ((self.retval, self.error))

    @classmethod
    def deserialize (cls, buf):
        data = None
        try:
            data = pickle.loads (buf)
        except Exception, e:
            raise RPC_Exception ("unpickle failed %s" % (str(e)))
        if len (data) != 2:
            raise RPC_Exception ("invalid response format")
        return cls (data[0], data[1])


class RPC_ServerHandle (object):

    def __init__ (self):
        self.func_dict = dict ()

    def add_handle (self, cb):
        assert callable (cb)
        self.func_dict[cb.func_name] = cb

    def call (self, req):
        assert isinstance (req, RPC_Req)
        func = self.func_dict.get (req.func_name)
        if not callable (func):
            raise Exception ("no such function %s" % (req.func_name))
        call_args_len = len (req.args) + len (req.k_args.values())
        if call_args_len > func.func_code.co_argcount:
            raise Exception ("function %s accepts %d arguments, %d given" % (req.func_name, len(func[1]), call_args_len))
        return func (*req.args, **req.k_args)
        

class SSL_RPC_Client (object):

    sock = None
    timeout = None

    def __init__ (self, logger=None, ssl_version=ssl.PROTOCOL_SSLv3):
        self.connected = False
        self.logger = None
        self.ssl_version = ssl_version
        self.timeout = 10
    
    def connect (self, addr):
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect (addr)
        self.sock = ssl.wrap_socket (self.sock, ssl_version=self.ssl_version)
        self.connected = True
        self.sock.settimeout (self.timeout)

    def set_timeout (self, timeout):
        if self.sock:
            self.sock.settimeout (timeout)
        self.timeout = timeout

    def call (self, func_name, *args, **k_args):
        if not self.connected:
            raise RPC_Exception ("not connected")
        start_ts = time.time ()
        req = RPC_Req (func_name, args, k_args)
        data = req.serialize()
        head = NetHead ()
        head.write_msg (self.sock, data)
        resp = None
        resp_head = NetHead.read_head (self.sock)
        if not resp_head.body_len:
            raise RPC_Exception ("rpc call %s, server-side return empty head" % (str(req)))
        buf = resp_head.read_data (self.sock)
        resp = RPC_Resp.deserialize (buf)
        end_ts = time.time ()
        timespan = end_ts - start_ts
        if resp.error:
            raise RPC_Exception ("rpc call %s return error: %s [%s sec]" % (str(req), str(resp.error), timespan))
        if self.logger:
            self.logger.info ("rpc call %s returned  [%s sec]" % (str(req), timespan))
        return resp.retval
            
    def close (self):
        self.sock.close ()
        self.connected = False
        


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

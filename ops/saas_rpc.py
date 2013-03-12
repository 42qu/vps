#!/usr/bin/env python
# coding:utf-8

import _env
from lib.rpc import SSL_RPC_Client
import conf
from _saas.ttypes import CMD

class SAAS_Client (SSL_RPC_Client):

    def __init__ (self, logger=None):
        self.rpc = SSL_RPC_Client (logger)

    def connect (self):
        print "connect"
        return self.rpc.connect (("dev.frostyplanet.com", conf.SAAS_PORT + 1))

    def close (self):
        self.rpc.close ()

    def __get_attr__ (self, name):
        lambda *args, **k_args: self.rpc.call (name, *args, **k_args)

if __name__ == '__main__':
    client = SAAS_Client ()
    client.connect ()
    print client.todo (conf.HOST_ID, CMD.OPEN)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

#!/usr/bin/env python
# coding:utf-8

import _env
from lib.rpc import SSL_RPC_Client
import conf
from _saas.ttypes import CMD
import types

class SAAS_Client (object):

    def __init__ (self, logger=None):
        self.rpc = SSL_RPC_Client (logger)

    def connect (self):
        print "connect"
        return self.rpc.connect (("dev.frostyplanet.com", conf.SAAS_PORT + 1))

    def close (self):
        self.rpc.close ()

    def todo (self, host_id, cmd):
        return self.rpc.call ("todo", host_id, cmd)

    def host_list (self):
        return self.rpc.call ("host_list")

    def done (self, host_id, cmd, vm_id, state, message):
        return self.rpc.call ("done", host_id, cmd, vm_id, state, message)

    def host_refresh(self, host_id, hd_remain, ram_remain, hd_total=0, ram_total=0):
        return self.rpc.call ("host_refresh", host_id, hd_remain, ram_remain, hd_total, ram_total)

    def vps(self, vm_id):
        return self.rpc.call ("vps", vm_id)

if __name__ == '__main__':
    client = SAAS_Client ()
    client.connect ()
    print client.todo (conf.HOST_ID, CMD.OPEN)
    print client.host_list()
    print client.vps (2)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

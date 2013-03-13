#!/usr/bin/env python
# coding:utf-8

import _env
from lib.rpc import SSL_RPC_Client, RPC_Exception
import conf
from _saas.ttypes import CMD
from lib.attr_wrapper import AttrWrapper
import types

class SAAS_Client (object):

    def __init__ (self, logger=None):
        self.rpc = SSL_RPC_Client (logger)

    def connect (self):
        return self.rpc.connect ((conf.SAAS_HOST, conf.SAAS_PORT + 1))

    def close (self):
        self.rpc.close ()

    def todo (self, host_id, cmd):
        return self.rpc.call ("todo", host_id, cmd)

    def host_list (self):
        return AttrWrapper.wrap (self.rpc.call ("host_list"))

    def done (self, host_id, cmd, vm_id, state, message):
        return self.rpc.call ("done", host_id, cmd, vm_id, int(state), str(message))

    def host_refresh(self, host_id, hd_remain, ram_remain, hd_total=0, ram_total=0):
        return self.rpc.call ("host_refresh", int(host_id), int(hd_remain), int(ram_remain), int(hd_total), int(ram_total))

    def vps(self, vm_id):
        return AttrWrapper(self.rpc.call ("vps", vm_id))

    def migrate_task (self, vm_id):
        return AttrWrapper(self.rpc.call ("migrate_task", vm_id))

if __name__ == '__main__':
    client = SAAS_Client ()
    client.connect ()
#    vps = client.vps (1176)
#    from vps_mgr import VPSMgr
#    m = VPSMgr ()
#    print vps
#    print m.vps_is_valid (vps)
#    print client.todo (conf.HOST_ID, CMD.OPEN)
#    print client.host_list()
#    vps_info = client.vps (2)
#    client.close ()
#    print "vps_info", vps_info, vps_info and True or False
#    print "int_ip", vps_info.int_ip
#    if vps_info.ext_ips:
#        print "ext_ips", vps_info.ext_ips[0].ipv4
#    print "state", vps_info.state, vps_info.state is None
#    print "hd", vps_info.harddisks

    client.close ()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

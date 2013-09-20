#!/usr/bin/env python
# coding:utf-8

import _env
from lib.rpc import AES_RPC_Client, RPC_Exception
import conf
from lib.attr_wrapper import AttrWrapper
from lib.enum import Enum

CMD = Enum(
    NONE = 0,
    OPEN = 1,
    CLOSE = 2,
    REBOOT = 3,
    RM = 4,
    BANDWIDTH = 5,
    OS = 6,
    UPGRADE = 7,
    MIGRATE = 8,
    MONITOR = 9,
    PRE_SYNC = 10,
    RESET_PW = 11,
    )

class VM_STATE:
    RM = 0
    RESERVE = 5
    PAY = 10
    OPEN = 15
    CLOSE = 20

class MIGRATE_STATE:
    NEW = 1
    TO_PRE_SYNC = 2
    PRE_SYNCING = 3
    PRE_SYNCED = 4
    TO_MIGRATE = 5
    MIGRATING = 6
    DONE = 7
    CANCELED = 8

VM_STATE_CN = dict()
VM_STATE_CN[VM_STATE.OPEN] = '运行中'
VM_STATE_CN[VM_STATE.PAY] = '待开通'
VM_STATE_CN[VM_STATE.CLOSE] = '被关闭'
VM_STATE_CN[VM_STATE.RESERVE]  = '未付款'
VM_STATE_CN[VM_STATE.RM]  = '已删除'



class SAAS_Client(object):

    def __init__(self, host_id, logger=None):
        self.rpc = AES_RPC_Client(conf.KEY, logger)
        self.host_id = int(host_id)

    def connect(self):
        return self.rpc.connect((conf.SAAS_HOST, conf.SAAS_PORT + 1))

    def close(self):
        self.rpc.close()

    def doing(self, cmd, vm_id):
        return self.rpc.call("doing", self.host_id, cmd, vm_id)

    def todo(self, cmd):
        return self.rpc.call("todo", self.host_id, cmd)

    def host_list(self):
        return AttrWrapper.wrap(self.rpc.call("host_list"))

    def done(self, cmd, vm_id, state, message):
        return self.rpc.call("done", self.host_id, cmd, vm_id, int(state), str(message))

    def host_refresh(self, hd_remain, ram_remain, hd_total=0, ram_total=0):
        return self.rpc.call("host_refresh", self.host_id, int(hd_remain), int(ram_remain), int(hd_total), int(ram_total))

    def vps(self, vm_id):
        return AttrWrapper(self.rpc.call("vps", vm_id))

    def migrate_task(self, vm_id):
        return AttrWrapper(self.rpc.call("migrate_task", vm_id))




if __name__ == '__main__':
    client = SAAS_Client(1)
    client.connect()
#    vps = client.vps(1176)
#    from vps_mgr import VPSMgr
#    m = VPSMgr()
#    print vps
#    print m.vps_is_valid(vps)
#    print client.todo(conf.HOST_ID, CMD.OPEN)
#    print client.host_list()
#    vps_info = client.vps(2)
#    client.close()
#    print "vps_info", vps_info, vps_info and True or False
#    print "int_ip", vps_info.int_ip
#    if vps_info.ext_ips:
#        print "ext_ips", vps_info.ext_ips[0].ipv4
#    print "state", vps_info.state, vps_info.state is None
#    print "hd", vps_info.harddisks

    client.close()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

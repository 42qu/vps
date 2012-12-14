#!/usr/bin/env python
# coding:utf-8

_dictcls = None
import collections
if 'OrderedDict' in dir (collections):
    _dictcls = collections.OrderedDict
else:
    _dictcls = dict

VPS_HOST_TYPE_NAME2ID = _dictcls (
    centos6_xen= 1,
    centos5_xen=2,
    ubuntu_xen_openvswitch=3,
)

VPS_HOST_TYPE_ID2NAME = dict()

for k, v in VPS_HOST_TYPE_NAME2ID.iteritems():
    VPS_HOST_TYPE_ID2NAME[v] = k

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

VM_STATE_CN = _dictcls()
VM_STATE_CN[VM_STATE.OPEN] = '运行中'
VM_STATE_CN[VM_STATE.PAY] = '待开通'
VM_STATE_CN[VM_STATE.CLOSE] = '被关闭'
VM_STATE_CN[VM_STATE.RESERVE]  = '未付款'
VM_STATE_CN[VM_STATE.RM]  = '已删除'

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

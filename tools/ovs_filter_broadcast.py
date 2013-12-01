#!/usr/bin/env python
# coding:utf-8

import _env
import conf
import sys
import os
import re
from ops.openvswitch import OVSOps
from lib.command import call_cmd, CommandException
import conf
assert conf.XEN_BRIDGE
assert conf.EXT_INF


def add_rule(net):
    assert net
    ovsops = OVSOps()
    ofport = ovsops.find_ofport_by_name(conf.EXT_INF)
    assert ofport > 0
    call_cmd(
        "ovs-ofctl add-flow %s 'ip,in_port=%s,nw_dst=%s,priority=2000,action=normal'" %
        (conf.XEN_BRIDGE, ofport, net))
    call_cmd("ovs-ofctl add-flow %s 'ip,in_port=%s,priority=10,action=drop'" %
             (conf.XEN_BRIDGE, ofport))


def usage():
    print "%s network/mask" % (sys.argv[0])
    os._exit(1)

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        usage()
    add_rule(sys.argv[1])


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

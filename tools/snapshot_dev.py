#!/usr/bin/env python
# coding:utf-8

import _env
import os
import sys
import getopt
import ops.vps_common as vps_common
import conf
assert conf.VPS_LVM_VGNAME

def snapshot_dev (lv_dev):
    if not os.path.exists (lv_dev):
        raise Exception ("no such dev %s" % (lv_dev))
    snapshot_dev = vps_common.lv_snapshot (lv_dev, "snap_%s" % (os.path.basename(lv_dev)) , conf.VPS_LVM_VGNAME)
    print snapshot_dev, "is created"

def usage ():
    print "usage: %s LVMdevice" % (sys.argv[0])

if "__main__" == __name__:
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
            "help",
        ])
    for opt, v in optlist:
        if opt == '--help':
            usage ()
            os._exit (0)
    if len (args) < 1:
        usage ()
        os._exit (1)
    lv_dev = args[0]
    snapshot_dev (lv_dev)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

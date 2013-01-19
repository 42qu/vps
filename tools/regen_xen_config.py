#!/usr/bin/env python
# coding:utf-8

import sys
import os
import _env
from vps_mgr import VPSMgr
import getopt
from ops.vps_ops import VPSOps

def usage ():
    print "usage: %s vps_id" % (sys.argv[0])
    return

def main ():
    if len (sys.argv) < 2:
        usage ()
        os._exit (0)
    vps_id = int(sys.argv[1])

    client = VPSMgr ()
    vpsops = client.vpsops
    xv = vpsops.load_vps_meta (vps_id)
    vpsops.create_xen_config (xv)

if __name__ == '__main__':
    main ()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

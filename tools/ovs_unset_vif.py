#!/usr/bin/env python
# coding:utf-8

import os
import sys

import _env
import conf
from vps_mgr import VPSMgr
from ops.openvswitch import OVSOps
import getopt


def usage (): 
    print "%s vif_name" % (sys.argv[0])
    print "vif_name must match /\w(+d)/"
    return

def main ():
    vif_name = args[0]
    client = VPSMgr ()
    try:
        ovsops = OVSOps ()
        ofport = ovsops.find_ofport_by_name (vif_name)
        ovsops.unset_mac_filter (ofport)
        ovsops.unset_traffic_limit (vif_name)
        return 0
    except Exception, e:
        client.logger.exception (e)
        print >> sys.stderr, str(e)
        return 1
 
if __name__ == '__main__':
    if len (sys.argv) <= 1:
        usage ()
        os._exit (0)
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
                 "help", 
                 ])

    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
    res = main ()
    os._exit (res)
 

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

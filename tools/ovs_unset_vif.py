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
    print "%s bridge vif_name" % (sys.argv[0])
    print "vif_name must match /\w(+d)/"
    return

def main ():
    bridge = args[0]
    vif_name = args[1]
    client = VPSMgr ()
    try:
        ovsops = OVSOps ()
        ovsops.unset_traffic_limit (vif_name)
        ofport = ovsops.find_ofport_by_name (vif_name)
        if ofport < 0:
            client.logger.error ("vif %s ofport=%s, which is impossible , you can fix it by delete the port from bridge" % (vif_name, ofport))
            return 1
        ovsops.unset_mac_filter (bridge, ofport)
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

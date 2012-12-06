#!/usr/bin/env python
# coding:utf-8

import os
import sys

import _env
import conf
from lib.log import Log

from ops.openvswitch import OVSOps
import getopt


def usage (): 
    print "%s bridge vif_name" % (sys.argv[0])
    print "vif_name must match /\w(+d)/"
    return

def main ():
    bridge = args[0]
    vif_name = args[1]
    logger = Log ("vps_mgr", config=conf)
    try:
        ovsops = OVSOps ()
        ofport = ovsops.find_ofport_by_name (vif_name)
        if ofport < 0:
            logger.error ("vif %s ofport=%s, skip it" % (vif_name, ofport))
        else:
            ovsops.unset_mac_filter (bridge, ofport)
        ovsops.unset_traffic_limit (vif_name)  # it's strange that if you unset traffic first, might find ofport==-1
        logger.debug ("unset %s" % vif_name)
        return 0
    except Exception, e:
        logger.exception (e)
        print >> sys.stderr, str(e)
        return 0
 
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

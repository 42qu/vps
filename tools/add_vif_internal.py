#!/usr/bin/env python

import sys
import os
import _env
from vps_mgr import VPSMgr
import conf
import getopt
from ops.vps_ops import VPSOps

def usage ():
    print "usage: %s vps_id int_ip netmask" % (sys.argv[0])
    return

def add_vif_int (vps_id, ip, netmask):
    print "adding vps_id=", vps_id, "ip=", ip, "netmask=", netmask
    vpsmgr = VPSMgr ()
    vpsops = VPSOps (vpsmgr.logger)
    try:
        vpsops.add_vif_int (vps_id, ip, netmask)
    except Exception, e:
        vpsmgr.logger.exception (e)
        raise e
    
if __name__ == '__main__':
    if len (sys.argv) < 4:
        usage ()
        os._exit (0)

    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
                 "help", 
                 ])
    vps_id = args[0]
    ip = args[1]
    netmask = args[2]
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)

    add_vif_int (vps_id, ip, netmask)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

#!/usr/bin/env python

import sys
import os
import _env
from vps_mgr import VPSMgr
import getopt
from ops.vps_ops import VPSOps
from zkit.ip import int2ip 

def usage ():
    print "usage: %s vps_id int_ip netmask" % (sys.argv[0])
    return

def add_vif_int (vps_id):
    client = VPSMgr ()
    vps_info = None
    try:
        vps_info = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state: [%s] %s" % (type(e), str(e))
        os._exit (1)
    if not vps_info.int_ip or not vps_info.int_ip.ipv4:
        print "not internal ip for %s" % (vps_id)
    vpsops = VPSOps (client.logger)
    try:
        vpsops.set_vif_int (vps_id, int2ip(vps_info.int_ip.ipv4), int2ip(vps_info.int_ip.ipv4_netmask))
    except Exception, e:
        client.logger.exception (e)
        raise e
    
if __name__ == '__main__':
    if len (sys.argv) < 2:
        usage ()
        os._exit (0)

    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
                 "help", 
                 ])
    vps_id = int(args[0])
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)

    add_vif_int (vps_id)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

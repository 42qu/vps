#!/usr/bin/env python

import sys
import os
import _env
from vps_mgr import VPSMgr
import getopt

def usage ():
    print "usage: %s vps_id" % (sys.argv[0])
    return

def add_vif_int (vps_id):
    client = VPSMgr ()
    vps_info = None
    try:
        vps_info = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state: [%s] %s" % (type(e), str(e))
        return
    if not vps_info.int_ip or not vps_info.int_ip.ipv4:
        print "not internal ip for %s" % (vps_id)
    vpsops = client.vpsops
    try:
        if vps_info.int_ip:
            vpsops.set_vif_int (vps_id, vps_info.int_ip.ipv4, vps_info.int_ip.ipv4_netmask)
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
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
    vps_id = int(args[-1])
    add_vif_int (vps_id)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

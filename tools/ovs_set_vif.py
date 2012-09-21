#!/usr/bin/env python
# coding:utf-8

import os
import sys
import _env
import conf
import re
from vps_mgr import VPSMgr
from ops.vps_ops import VPSOps
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
        om = re.match (r'^\w+?(\d+)\w*?$', vif_name)
        if not om:
            print >> sys.stderr, "wrong vif format %s" % (vif_name)
            return 1
        vps_id = int (om.group (1))
        xv = client.vpsops.load_vps_meta (vps_id)
        vif = xv.vifs.get (vif_name)
        if not vif:
            client.logger.error ("no vif %s in metadata of %s" % (vif_name, vps_id))
            return 1
        ofport = ovsops.find_ofport_by_name (vif_name)
        ovsops.set_mac_filter (ofport, vif.ip_dict.keys ())
        ovsops.unset_traffic_limit (vif_name)

        if vif.bandwidth:
            ovsops.set_traffic_limit (vif_name, vif.bandwidth * 1024)
            print "set vif %s bandwidth %sm/s" % (vif_name, vif.bandwidth)
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

#!/usr/bin/env python
# coding:utf-8
import sys
import os
import _env
from vps_mgr import VPSMgr
import conf

import getopt


def usage():
    print "%s vps_id " % (sys.argv[0])


def change_ip(vps_id):
    client = VPSMgr()
    vps_info = None
    try:
        vps_info = client.query_vps(vps_id)
    except Exception, e:
        print "failed to query vps state: [%s] %s" % (type(e), str(e))
        os._exit(1)
    client.vps_change_ip(vps_info)

if __name__ == '__main__':
    optlist, args = getopt.gnu_getopt(sys.argv[1:], "", [
        "help",
    ])
    if len(args) < 1:
        usage()
        os._exit(0)
    for opt, v in optlist:
        if opt == '--help':
            usage()
            os._exit(0)
    vps_id = int(args[0])
    change_ip(vps_id)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

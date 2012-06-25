#!/usr/bin/env python

import sys
import os
import _env
from vps_mgr import VPSMgr
import conf
import saas.const.vps as vps_const

import getopt

def usage ():
    print "%s vps_id" % (sys.argv[0])

def upgrade_vps (vps_id):
    client = VPSMgr ()
    vps = None
    try:
        vps = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state:" + type(e) + str(e)
        return
    if not client.vps_upgrade (vps):
        print "error occured, pls check the error log"

if __name__ == '__main__':

    vps_image = None
    os_id = None
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
        "help", 
        ])
    if len (args) < 2:
        usage ()
        os._exit (0)

    vps_id = int (args[0])
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
    upgrade_vps (vps_id)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

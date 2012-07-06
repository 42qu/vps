#!/usr/bin/env python2.6
import sys
import os
import _env
from vps_mgr import VPSMgr
import conf
import saas.const.vps as vps_const

import getopt


def usage ():
    print "%s vps_id " % (sys.argv[0])
    print "%s vps_id os_id" % (sys.argv[0])
    print "%s vps_id os_id --image VPS_IMAGE_OR_TARBALL" % (sys.argv[0])

def reinstall_os (vps_id, os_id=None, vps_image=None):
    client = VPSMgr ()
    vps = None
    try:
        vps = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state:" + type(e) + str(e)
    if not client._reinstall_os (vps_id, vps, os_id, vps_image):
        print "error occured, pls check the error log"

if __name__ == '__main__':

    vps_image = None
    os_id = None
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
        "help", "image=",
        ])
    if len (args) < 1:
        usage ()
        os._exit (0)

    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
        if opt == '--image':
            vps_image = v
    vps_id = int (args[0])


    if vps_image:
        if len (args) < 2:
            usage ()
            os._exit (0)

    if len (args) > 1:
        os_id = int (args[1])

    reinstall_os (vps_id, os_id, vps_image)
 


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

#!/usr/bin/env python

import sys
import os
import _env
from vps_mgr import VPSMgr
import conf
import const as vps_const

import getopt


def create_vps (vps_id, vps_image=None, is_new=True):
    client = VPSMgr ()
    vps = None
    try:
        vps = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state: [%s] %s" % (type(e), str(e))
        return
    if not vps:
        print "not backend data for vps %s" % (vps_id)
        return
    if vps.state not in [vps_const.VPS_STATE_PAY, vps_const.VPS_STATE_RUN]:
        print "vps %s state=%s, is not to be created" % (vps_id, vps_const.VPS_STATE2CN[vps.state])
        return
    if vps_image and not os.path.exists (vps_image):
        print "%s not exist" % (vps_image)
        return
    if not client.vps_open(vps, vps_image, is_new):
        print "error, pls check the log"
        return


def usage ():
    print "%s vps_id --image [VPS_IMAGE_OR_TARBALL] [ --keeppasswd ]" % (sys.argv[0])

if __name__ == '__main__':
    vps_image = None
    keeppasswd = False
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
                 "help", "keeppasswd", "image="
                 ])

    if len (args) < 1:
        usage ()
        os._exit (0)

    vps_id = int (args[0])
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
        if opt == '--image':
            vps_image = v
        elif opt == '--keeppasswd':
            keeppasswd = True
    create_vps (vps_id, vps_image, is_new=not keeppasswd)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

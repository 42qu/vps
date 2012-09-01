#!/usr/bin/env python

import sys
import os
import _env
from vps_mgr import VPSMgr
import conf
from saas.ttypes import Cmd
from ops.vps import XenVPS

import getopt

def usage ():
    print "%s vps_id" % (sys.argv[0])
    return


def reopen_vps (vps_id):
    client = VPSMgr ()
    vps_info = None
    try:
        vps_info = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state: %s %s " % (type(e), str(e))
        return False
    if not vps_info:
        print "not backend data for vps %s" % (vps_id)
        return False
    try:
        xv = XenVPS (vps_info.id)
        client.setup_vps (xv, vps_info)
        client.vpsops.reopen_vps (vps_id, xv)
        client.done_task (Cmd.OPEN, vps_id, True)
        return True
    except Exception, e:
        client.logger.exception ("for %s: %s" % (str(vps_id), str(e)))
        client.done_task (Cmd.OPEN, vps_id, False, "error, " + str(e))
        return False

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
    vps_id = int (args[0])
    reopen_vps (vps_id)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

#!/usr/bin/env python

import sys
import os
import _env
from vps_mgr import VPSMgr
import const as vps_const
import conf
import time

import getopt

def delete_vps (vps_id, forced=False):
    """ interact operation """
    client = VPSMgr ()
    vps = None
    try:
        vps = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state: [%s] %s" % (str(type(e)), str(e))
        if not forced:
            return
    if not vps:
        print "not backend data for vps %s" % (vps_id)
        if not forced:
            return
    if vps and vps.host_id == conf.HOST_ID and vps.state != vps_const.VPS_STATE_RM: 
        print "vps %s state=%s, is not to be deleted" % (vps_id, vps_const.VPS_STATE2CN[vps.state])
        if not forced:
            return
    answer = raw_input ('if confirm to delete vps %s, please type "CONFIRM" in uppercase:' % (vps_id))
    if answer != 'CONFIRM':
        print "aborted"
        return
    print "going to delete vps %s, you have 5 seconds to regret" % (vps_id)
    time.sleep(5)
    print "begin"
    try:
        client._vps_delete (vps_id, vps)
        print "done"
    except Exception, e:
        print type(e), e
    return



def usage ():
    print "%s vps_id" % (sys.argv[0])
    return

if __name__ == '__main__':
    if len (sys.argv) <= 1:
        usage ()
        os._exit (0)
    vps_id = int (sys.argv[1])
    forced = False
    optlist, args = getopt.gnu_getopt (sys.argv[2:], "f", [
                 "help", "force",
                 ])
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
        if opt in [ '-f', '--force' ]:
            forced = True

    delete_vps (vps_id, forced)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

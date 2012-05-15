#!/usr/bin/env python

import sys
import os
import _env
from vps_mgr import VPSMgr
import saas.const.vps as vps_const
import conf
import time

import getopt

def delete_vps (vps_id):
    """ interact operation """
    client = VPSMgr ()
    vps = None
    try:
        vps = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state:" + type(e) + str(e)
        return
    if not client.vps_is_valid (vps):
        print "not backend data for vps %s" % (vps_id)
        return
    if vps.state != vps_const.VPS_STATE_RM: 
        print "vps %s state=%s, is not to be deleted" % (vps_id, vps_const.VPS_STATE2CN[vps.state])
        return
    if vps.host_id != conf.HOST_ID:
        print "vps %s host_id=%s != current host %s ?" % (vps.id, vps.host_id, conf.HOST_ID)
    answer = raw_input ('if confirm to delete vps %s, please type "CONFIRM" in uppercase:' % (vps_id))
    if answer != 'CONFIRM':
        print "aborted"
        return
    print "you have 10 second to regreat"
    time.sleep(10)
    print "begin"
    try:
        client.delete_vps (vps)
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
    optlist, args = getopt.gnu_getopt (sys.argv[2:], "", [
                 "help", 
                 ])
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)

    delete_vps (vps_id)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

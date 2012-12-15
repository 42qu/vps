#!/usr/bin/env python
import sys
import os
import getopt
import _env
from lib.log import Log
import conf
import re
from vps_mgr import VPSMgr
from ops.vps import XenVPS


def migrate_vps (vps_id, dest_ip=None, speed=None, force=False):
    client = VPSMgr ()
    if force:
        assert dest_ip
    if client._vps_migrate (vps_id, force=force, to_host_ip=dest_ip, speed=speed):
        print "ok"
    else:
        print "error, pls see log"

def usage ():
    print "usage: %s  [ --speed MBbit/s] [-f] vps_id [vps_id2 ...] dest_ip" % (sys.argv[0])
    print "usage with migrate task: %s  vps_id" % (sys.argv[0])

def main ():
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "f", [
                 "help", "speed=", "force"
                 ])
    speed = None
    force = False
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
        if opt == '--speed':
            speed = float (v)
        if opt == '-f' or opt == '--force':
            force = True
    
    if len (args) < 1:
        usage ()
        os._exit (1)
    vps_ids = map (lambda x: int(x), args[0:-1])
    dest_ip = None
    if re.match (r'^\d+\.\d+\.\d+\.\d+$', args[-1]):
        dest_ip = args[-1]
    else:
        vps_ids.append (int(args[-1]))
    for vps_id in vps_ids:
        migrate_vps (vps_id, dest_ip, speed=speed, force=force)


if "__main__" == __name__:
    main ()




# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

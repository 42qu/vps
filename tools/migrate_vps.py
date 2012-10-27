#!/usr/bin/env python
import sys
import os
import getopt
import _env
from lib.log import Log
import conf
from ops.migrate import MigrateClient
from vps_mgr import VPSMgr
from ops.vps import XenVPS
from ops.vps_ops import VPSOps


def migrate_vps (vps_id, dest_ip, speed=None, force=False):
    logger = Log ("vps_mgr", config=conf)
    client = VPSMgr ()
    vps_info = None
    try:
        vps_info = client.query_vps (vps_id)
    except Exception, e:
        print "failed to query vps state: [%s] %s" % (type(e), str(e))
        if not force:
            os._exit (1)
    try:
        vpsops = VPSOps (logger)
        xv = None
        if vps_info:
            xv = XenVPS (vps_info.id)
            client.setup_vps (xv, vps_info)
        migclient = MigrateClient (logger, dest_ip)
        vpsops.migrate_vps (migclient, vps_id, dest_ip, speed=speed, _xv=xv)
        print "ok"
    except Exception, e:
        logger.exception (e)
        raise e

def usage ():
    print "usage: %s  [ --speed MByte/s] vps_id [vps_id2 ...] dest_ip" % (sys.argv[0])

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
    
    if len (args) < 2:
        usage ()
        os._exit (1)
    vps_ids = map (lambda x: int(x), args[0:-1])
    dest_ip = args[-1]
    for vps_id in vps_ids:
        migrate_vps (vps_id, dest_ip, speed=speed, force=force)


if "__main__" == __name__:
    main ()




# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

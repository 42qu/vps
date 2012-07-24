#!/usr/bin/env python
import sys
import os
import getopt
import _env
from lib.log import Log
import conf
from ops.vps_ops import VPSOps


def migrate_vps (vps_id, dest_ip):
    logger = Log ("vps_mgr", config=conf)
    try:
        vpsops = VPSOps (logger)
        migclient = MigrateClient (logger, dest_ip)
        vpsops.migrate_vps (migclient, vps_id, dest_ip)
        print "ok"
    except Exception, e:
        logger.exception (e)
        raise e

def usage ():
    print "usage: %s vps_id dest_ip" % (sys.argv[0])

def main ():
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
                 "help", 
                 ])

    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
    
    if len (args) != 2:
        usage ()
        os._exit (1)
    vps_id = args[0]
    dest_ip = args[1]
    migrate_vps (vps_id, dest_ip)


if "__main__" == __name__:
    main ()




# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

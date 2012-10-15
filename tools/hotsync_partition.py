#!/usr/bin/env python

import sys
import os
import getopt
import _env
from lib.log import Log
import conf
from ops.migrate import MigrateClient

def hotsync_partition (lv_dev, dest_ip, speed=None):
    logger = Log ("vps_mgr", config=conf)
    try:
        client = MigrateClient (logger, dest_ip)
        client.snapshot_sync (lv_dev, speed=speed)
        print "ok"
    except Exception, e:
        logger.exception (e)
        raise e
    
def usage ():
    print "usage: %s  [ --speed MByte/s] lvm_dev dest_ip " % (sys.argv[0])

def main ():
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "", [
                 "help", "speed="
                 ])
    speed = None
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
        if opt == '--speed':
            speed = float (v)
    
    if len (args) != 2:
        usage ()
        os._exit (1)
    lv_dev = args[0]
    dest_ip = args[1]
    arr = lv_dev.split ("/")
    if len (arr) == 4 and arr[0] == "" and arr[1] == 'dev' and os.path.exists(lv_dev):
        hotsync_partition (lv_dev, dest_ip, speed)
    else:
        print >> sys.stderr, "%s is not a logical volumn device" % (lv_dev)
        os._exit (1)


if "__main__" == __name__:
    main ()

    # vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

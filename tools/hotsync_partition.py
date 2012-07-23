#!/usr/bin/env python

import sys
import os
import getopt
import _env
from lib.log import Log
import conf
from ops.migrate import MigrateClient

def hotsync_partition (dest_ip, lv_dev):
    logger = Log ("migrate_client", config=conf)
    client = MigrateClient (logger, dest_ip)
    client.snapshot_sync (lv_dev)
    
def usage ():
    print "usage: %s dest_ip lvm_dev" % (sys.argv[0])

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
    dest_ip = args[0]
    lv_dev = args[1]
    arr = lv_dev.split ("/")
    if len (arr) == 4 and arr[0] == "" and arr[1] == 'dev' and os.path.exists(lv_dev):
        hotsync_partition (dest_ip, lv_dev)
    else:
        print >> sys.stderr, "%s is not a logical volumn device" % (lv_dev)
        os._exit (1)


if "__main__" == __name__:
    main ()

    # vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

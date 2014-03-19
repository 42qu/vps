#!/usr/bin/env python
# coding:utf-8

import sys
import os
import getopt
import _env
from lib.log import Log
import conf
import re
from vps_mgr import VPSMgr
from ops.saas_rpc import MIGRATE_STATE


def hotsync_vps(vps_id, dest_ip, speed=None, force=False):
    client = VPSMgr()
    task = client.query_migrate_task(vps_id)
    if task is not None and task.state == MIGRATE_STATE.NEW:
        force = True
    if client._vps_hot_sync(vps_id, to_host_ip=dest_ip, speed=speed, force=force):
        print "%s ok" % (vps_id)
    else:
        print "error, pls see log"


def usage():
    print "usage: %s [ --speed Mbit/s] vps_id1  vps_id2 ... dest_ip " % (sys.argv[0])
    print "usage with migrate task: %s vps_id1 vps_id2 ... " % (sys.argv[0])


def main():
    optlist, args = getopt.gnu_getopt(sys.argv[1:], "f", [
        "help", "speed=", "force"
    ])
    speed = None
    force = False
    for opt, v in optlist:
        if opt == '--help':
            usage()
            os._exit(0)
        if opt == '--speed':
            speed = float(v)
        if opt == '-f' or opt == '--force':
            force = True
    if len(args) < 1:
        usage()
        os._exit(1)
    vps_ids = map(int, args[0:-1])
    dest_ip = None
    if re.match(r'^\d+$', args[-1]):
        vps_ids.append(int(args[-1]))
    else:
        dest_ip = args[-1]
    for vps_id in vps_ids:
        hotsync_vps(vps_id, dest_ip, speed=speed, force=force)

if __name__ == '__main__':
    main()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

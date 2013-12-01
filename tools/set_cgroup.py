#!/usr/bin/env python
# coding:utf-8

import glob
import sys
import re
import os
import _env
import conf
from vps_mgr import VPSMgr
from ops.ixen import XenStore


def _set_cgroup(client, vps_id, mode):
    meta = client.vpsops._meta_path(vps_id, is_trash=False)
    if not os.path.exists(meta):
        print >> sys.stderr, vps_id, "has no meta"
        return
    xv = client.vpsops._load_vps_meta(meta)
    for disk in xv.data_disks.values():
        if mode == 'reset':
            disk.set_cgroup_limit_default()
        elif mode == 'down':
            disk.set_cgroup_limit_below_default()
        print str(disk), disk.cgroup_limit
        disk.create_limit()
    xv.swap_store.create_limit()
    client.vpsops.save_vps_meta(xv)

def usage():
    pg_name = sys.argv[0]
    print "%s           # reapply setting" % (pg_name)
    print "%s --reset   # reset all individual setting to default" % (pg_name)
    print "%s --down   # change set setting down to default, (if it was higher before)" % (pg_name)


def check_all():
    import getopt
    mode = None
    pretend = False
    opt_list, args = getopt.gnu_getopt(sys.argv, "", ["down", "reset", "help"])
    for opt, v in opt_list:
        if opt == '--help':
            usage()
            return
        elif opt == '--down':
            mode = 'down'
        elif opt == '--reset':
            mode = 'reset'

    client = VPSMgr()
    all_ids = client.vpsops.all_vpsid_from_config()
    print "xen_config: %d, running: %d" % (len(all_ids), client.vpsops.running_count)
    for vps_id in all_ids:
        print "vps", vps_id
        _set_cgroup(client, vps_id, mode)

if __name__ == '__main__':
    check_all()



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

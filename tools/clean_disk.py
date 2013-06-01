#!/usr/bin/env python
# coding:utf-8

import glob
import sys
import re
import os
import _env
import conf
from vps_mgr import VPSMgr
from ops.vps import XenVPS
from ops.ixen import XenStore
from ops.saas_rpc import VM_STATE, VM_STATE_CN

def _delete_all (xv, status, days=0):
    for disk in xv.data_disks ():
        if disk.exists ():
            if days and not disk.test_expire ():
                print status, str(disk), "not expired"
                continue
            print status, str(disk)
        if disk.trash_exists ():
            if days and not disk.test_expire ():
                print status, disk.trash_str (), "not expired"
                continue
            print status, disk.trash_str ()
    for disk in xv.trash_disks.values ():
        if disk.trash_exists ():
            if days and not disk.test_expire ():
                print status, disk.trash_str (), "not expired"
                continue
            print status, disk.trash_str ()


def _delete_trash (xv, status, days=0):
    for disk in xv.trash_disks.values ():
        if disk.trash_exists ():
            if days and not disk.test_expire ():
                print status, disk.trash_str (), "not expired"
                continue
            print status, disk.trash_str ()


def _check_disk (client, vps_id):
    is_trash = False
    is_delete = False
    meta = client.vpsops._meta_path (vps_id, is_trash=False)
    if not os.path.exists (meta):
        meta = client.vpsops._meta_path (vps_id, is_trash=True)
        if not os.path.exists (meta):
            meta = client.vpsops._meta_path (vps_id, is_trash=True, is_delete=True)
            if not os.path.exists (meta):
                meta = client.vpsops._meta_path (vps_id, is_trash=False, is_delete=True)
                if not os.path.exists (meta):
                    return
            is_delete = True
        else:
            is_trash = True
    xv = client.vpsops._load_vps_meta (meta)
    if is_delete:
        _delete_all (xv, "deleted")
    else:
        vps_info = None
        try:
            vps_info = client.query_vps (vps_id)
        except Exception, e:
            raise e
        if is_trash:
            if not vps_info:
                _delete_all (xv, "closed but no meta")
            elif str(vps_info.host_id) != str(conf.HOST_ID):
                _delete_all (xv, "closed but not on this host")
            else:
                print "ignore closed vps", vps_id
                return
        else:
            if not vps_info:
                _delete_trash (xv, "running but no meta")
            elif str(vps_info.host_id) != str(conf.HOST_ID):
                _delete_all (xv, "running but not on this host", days=7)
            else:
                _delete_trash (xv, "running", days=7)



def check_all ():
    assert conf.XEN_CONFIG_DIR and os.path.isdir (conf.XEN_CONFIG_DIR)
    assert conf.VPS_METADATA_DIR and os.path.isdir (conf.VPS_METADATA_DIR)
    all_ids = set ()
    client = VPSMgr ()
    configs = glob.glob (os.path.join (conf.VPS_METADATA_DIR, "*.json*"))
    for config in configs:
        om = re.match (r'^vps(\d+)\.\w+$', os.path.basename (config))
        if not om:
            continue
        vps_id = int(om.group (1))
        all_ids.add (vps_id)
    print "meta %d"  % (len(all_ids))
    for vps_id in all_ids:
        _check_disk (client, vps_id)

if __name__ == '__main__':
    check_all ()


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

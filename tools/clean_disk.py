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
import getopt

def _delete_disk (logger, disk, dry=True):
    if dry:
        return
    disk.delete ()
    logger.info ("deleted %s" % (str(disk)))

def _delete_disk_trash (logger, disk, dry=True):
    if dry:
        return
    disk.delete_trash ()
    logger.info ("deleted %s" % (disk.trash_str ()))
     

def _delete_all (logger, xv, status, days=0, dry=True):
    for disk in xv.data_disks ():
        if disk.exists ():
            if days and not disk.test_expire (days):
                print status, str(disk), "not expired"
                continue
            print status, str(disk)
            _delete_disk (logger, disk, dry=dry)
        if disk.trash_exists ():
            if days and not disk.test_expire (days):
                print status, disk.trash_str (), "not expired"
                continue
            print status, disk.trash_str ()
            _delete_disk_trash (logger, disk, dry=dry)
    for disk in xv.trash_disks.values ():
        if disk.trash_exists ():
            if days and not disk.test_expire (days):
                print status, disk.trash_str (), "not expired"
                continue
            print status, disk.trash_str ()
            _delete_disk_trash (logger, disk, dry=dry)


def _delete_trash (logger, xv, status, days=0, dry=True):
    for disk in xv.trash_disks.values ():
        if disk.trash_exists ():
            if days and not disk.test_expire (days):
                print status, disk.trash_str (), "not expired"
                continue
            print status, disk.trash_str ()
            _delete_disk_trash (logger, disk, dry=dry)


def _check_disk (client, vps_id, dry=True):
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
    logger = client.logger
    if is_delete:
        _delete_all (logger, xv, "deleted", dry=dry)
    else:
        vps_info = None
        try:
            vps_info = client.query_vps (vps_id)
        except Exception, e:
            raise e
        if is_trash:
            if not vps_info:
                _delete_all (logger, xv, "closed but no meta", dry=dry)
            elif str(vps_info.host_id) != str(conf.HOST_ID):
                _delete_all (logger, xv, "closed but not on this host", dry=dry)
            else:
                print "ignore closed vps", vps_id
                return
        else:
            if not vps_info:
                _delete_trash (logger, xv, "running but no meta", dry=dry)
            elif str(vps_info.host_id) != str(conf.HOST_ID):
                _delete_all (logger, xv, "running but not on this host", days=7, dry=dry)
            else:
                _delete_trash (logger, xv, "running", days=7, dry=dry)



def check_all (dry=True):
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
        _check_disk (client, vps_id, dry=dry)

def usage ():
    print "%s [-p] vps_id" % (sys.argv[0])
    print "-p for pretending run"
    return


if __name__ == '__main__':
    dry = False
    optlist, args = getopt.gnu_getopt (sys.argv[1:], "p", [
                 "help", "pretend",
                 ])
    for opt, v in optlist:
        if opt == '--help': 
            usage ()
            os._exit (0)
        if opt in [ '-p', '--pretend' ]:
            dry = True
    check_all (dry=dry)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

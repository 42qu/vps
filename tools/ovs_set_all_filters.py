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
from ops.openvswitch import OVSOps


def _set_vif_filter(ovsops, vif):
    ofport = ovsops.find_ofport_by_name(vif.ifname)
    if ofport >= 0:
        ovsops.set_mac_filter(vif.bridge, ofport, vif.ip_dict.keys())


def _set_filter(client, ovsops, vps_id):
    meta = client.vpsops._meta_path(vps_id, is_trash=False)
    if not os.path.exists(meta):
        print >> sys.stderr, vps_id, "has no meta"
        return
    xv = client.vpsops._load_vps_meta(meta)
    ext_vif = xv.vifs.get(xv.vif_ext_name)
    if ext_vif:
        _set_vif_filter(ovsops, ext_vif)
    int_vif = xv.vifs.get(xv.vif_int_name)
    if int_vif:
        _set_vif_filter(ovsops, int_vif)


def check_all():
    assert conf.XEN_CONFIG_DIR and os.path.isdir(conf.XEN_CONFIG_DIR)
    assert conf.VPS_METADATA_DIR and os.path.isdir(conf.VPS_METADATA_DIR)
    client = VPSMgr()
    ovsops = OVSOps()
    all_ids = client.vpsops.all_vpsid_from_config()
    print ""
    print "xen_config: %d, running: %d" % (len(all_ids), client.vpsops.running_count)
    for vps_id in all_ids:
        print "vps", vps_id
        _set_filter(client, ovsops, vps_id)

if __name__ == '__main__':
    check_all()





# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

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


def _clear_vif_filter(ovsops, vif):
    ofport = ovsops.find_ofport_by_name(vif.ifname)
    if ofport >= 0:
        ovsops.unset_mac_filter(vif.bridge, ofport)


def _clear_filter(client, ovsops, vps_id):
    meta = client.vpsops._meta_path(vps_id, is_trash=False)
    if not os.path.exists(meta):
        print >> sys.stderr, vps_id, "has no meta"
        return
    xv = client.vpsops._load_vps_meta(meta)
    ext_vif = xv.vifs.get(xv.vif_ext_name)
    if ext_vif:
        _clear_vif_filter(ovsops, ext_vif)
    int_vif = xv.vifs.get(xv.vif_int_name)
    if int_vif:
        _clear_vif_filter(ovsops, int_vif)


def check_all():
    assert conf.XEN_CONFIG_DIR and os.path.isdir(conf.XEN_CONFIG_DIR)
    assert conf.VPS_METADATA_DIR and os.path.isdir(conf.VPS_METADATA_DIR)
    all_ids = []
    client = VPSMgr()
    ovsops = OVSOps()
    configs = glob.glob(os.path.join(conf.XEN_CONFIG_DIR, "vps*"))
    for config in configs:
        om = re.match(r'^vps(\d+)$', os.path.basename(config))
        if not om:
            continue
        vps_id = int(om.group(1))
        all_ids.append(vps_id)
    all_ids.sort()
    domain_dict = XenStore.domain_name_id_map()
    del domain_dict['Domain-0']
    print ""
    print "xen_config: %d, running: %d" % (len(all_ids), len(domain_dict))
    for vps_id in all_ids:
        print "vps", vps_id
        _clear_filter(client, ovsops, vps_id)

if __name__ == '__main__':
    check_all()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

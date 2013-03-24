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

def _check_bandwidth (client, vps_id):
    meta = client.vpsops._meta_path (vps_id, is_trash=False)
    if not os.path.exists (meta):
        print >> sys.stderr, vps_id, "has no meta"
        return
    xv = client.vpsops._load_vps_meta (meta)
    vps_info = None
    try:
        vps_info = client.query_vps (vps_id)
    except Exception, e:
        print str(e)
        return 
    _xv = XenVPS (vps_id)
    client.setup_vps (_xv, vps_info)
    if vps_info.host_id != conf.HOST_ID:
        is_running = xv.is_running () and "(running)" or "(not running)"
        print "vps %s %s host_id=%s not on this host" % (vps_id, is_running, vps_info.host_id)
        return
    elif vps_info.state != VM_STATE.OPEN:
        is_running = xv.is_running () and "(running)" or "(not running)"
        print "vps %s %s backend state=%s " % (vps_id, is_running, VM_STATE_CN[vps_info.state])
        return
    if not _xv.vif_ext or not xv.vif_ext:
        return
    if xv.vif_ext.bandwidth != _xv.vif_ext.bandwidth:
        print "vps", vps_id, "bandwidth old:", xv.vif_ext.bandwidth, "new:", _xv.vif_ext.bandwidth
        client.vpsops.change_qos (_xv)
 


def check_all ():
    assert conf.XEN_CONFIG_DIR and os.path.isdir (conf.XEN_CONFIG_DIR)
    assert conf.VPS_METADATA_DIR and os.path.isdir (conf.VPS_METADATA_DIR)
    all_ids = []
    client = VPSMgr ()
    configs = glob.glob (os.path.join (conf.XEN_CONFIG_DIR, "vps*"))
    for config in configs:
        om = re.match (r'^vps(\d+)$', os.path.basename (config))
        if not om:
            continue
        vps_id = int(om.group (1))
        all_ids.append (vps_id)
    all_ids.sort ()
    domain_dict = XenStore.domain_name_id_map ()
    del domain_dict['Domain-0']
    print ""
    print "xen_config: %d, running: %d"  % (len(all_ids), len(domain_dict))
    for vps_id in all_ids:
        print "vps", vps_id
        _check_bandwidth (client, vps_id)

if __name__ == '__main__':
    check_all ()


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

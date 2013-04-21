#!/usr/bin/env python
# coding:utf-8

import glob
import re
import os
import _env
import conf
from vps_mgr import VPSMgr
from ops.vps import XenVPS
from ops.ixen import XenStore
import ops.vps_common as vps_common
from ops.saas_rpc import VM_STATE, VM_STATE_CN
from tools.add_vif_internal  import add_vif_int

def check_all_vps ():
    assert conf.XEN_CONFIG_DIR and os.path.isdir (conf.XEN_CONFIG_DIR)
    assert conf.VPS_METADATA_DIR and os.path.isdir (conf.VPS_METADATA_DIR)
    all_ids = []
    client = VPSMgr ()
    vpsops = client.vpsops
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
        add_vif_int (vps_id)

if __name__ == '__main__':
    check_all_vps ()


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

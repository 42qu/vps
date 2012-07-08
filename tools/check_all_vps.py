#!/usr/bin/env python

import glob
import re
import os
import _env
import conf
import saas.const.vps as vps_const
from vps_mgr import VPSMgr
from ops.vps import XenVPS
from ops.vps_ops import VPSOps
import ops.vps_common as vps_common

def check_via_meta (client, vpsops, vps_id, vps_info):
    meta = vpsops._meta_path (vps_id, is_trash=False)
    if os.path.exists (meta):
        xv = vpsops._load_vps_meta (meta)
        is_running = xv.is_running () and "(running)" or "(not running)"
        ip_ok = "ip %s " % (xv.ip) +  (vps_common.ping (xv.ip) and "reachable" or "timeout")
        print "vps %s %s %s" % (vps_id, is_running, ip_ok)
        return
    else:
        xv = XenVPS (vps_id)
        is_running = xv.is_running () and "(running)" or "(not running)"
        if not vps_info:
            print "vps %s %s has neither meta data or backend data" % (vps_id, is_running)
            return
        else:
            client.setup_vps (xv, vps_info)
            ip_ok = "ip %s " % (xv.ip) +  vps_common.ping (xv.ip) and "reachable" or "timeout"
            print "vps %s %s %s has no meta_data" % (vps_id, is_running, ip_ok)
            return


def check_via_backend (client, vps_id):
    vps_info = None
    try:
        vps_info = client.query_vps (vps_id)
        if not vps_info:
            return False, None
    except Exception, e:
        raise e
    xv = XenVPS (vps_id)
    if vps_info.host_id != conf.HOST_ID:
        is_running = xv.is_running () and "(running)" or "(not running)"
        print "vps %s %s host_id=%s not on this host" % (vps_id, is_running, vps_info.host_id)
        return True, None
    elif vps_info.state != vps_const.VPS_STATE_RUN:
        is_running = xv.is_running () and "(running)" or "(not running)"
        print "vps %s %s backend state=%s " % (vps_id, is_running, vps_const.VPS_STATE2CN[vps_info.state])
        print True, None
    return False, vps_info

def check_all_vps ():
    assert conf.XEN_CONFIG_DIR and os.path.isdir (conf.XEN_CONFIG_DIR)
    assert conf.VPS_METADATA_DIR and os.path.isdir (conf.VPS_METADATA_DIR)
    all_ids = []
    client = VPSMgr ()
    vpsops = VPSOps (client.logger)
    configs = glob.glob (os.path.join (conf.XEN_CONFIG_DIR, "vps*"))
    for config in configs:
        om = re.match (r'^vps(\d+)$', os.path.basename (config))
        if not om:
            continue
        vps_id = int(om.group (1))
        all_ids.append (vps_id)
    all_ids.sort ()
    for vps_id in all_ids:
        checked, vps_info = check_via_backend (client, vps_id)
        if checked:
            continue
        check_via_meta (client, vpsops, vps_id, vps_info)


if __name__ == '__main__':
    check_all_vps ()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

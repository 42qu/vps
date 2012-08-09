#!/usr/bin/env python2.6

import _env
import conf
from ops.vps_common import vg_free_space
from vps_mgr import VPSMgr

if __name__ == '__main__':
    disk_free = vg_free_space (conf.VPS_LVM_VGNAME)
    print disk_free
    client = VPSMgr ()
    client.refresh_host_space ()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

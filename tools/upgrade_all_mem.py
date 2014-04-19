#!/usr/bin/env python
# coding:utf-8

import _env
import os
from vps_mgr import VPSMgr

def change_meta(client, vps_id):
    meta = client.vpsops._meta_path(vps_id, is_trash=False)
    if os.path.exists(meta):
        xv = client.vpsops._load_vps_meta(meta)
        if xv.mem_m == 512:
            xv.mem_m = 768
            client.vpsops.save_vps_meta(xv)
            print "change", xv.vps_id
        

def main():
    client = VPSMgr()
    all_ids = client.vpsops.all_vpsid_from_config()
    for vps_id in all_ids:
        change_meta(client, vps_id)

if __name__ == '__main__':
    main()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

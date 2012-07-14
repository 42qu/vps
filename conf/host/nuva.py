#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from os.path import dirname

def prepare(o):
    o.HOST_ID = 1
    o.USE_LVM = True
    o.VPS_LVM_VGNAME="main2"
    base_dir = dirname (dirname (dirname (__file__)))
    o.log_dir = os.path.join (base_dir, "log")

    o.RUN_DIR = os.path.join (base_dir, "run")
    o.OS_IMAGE_DIR = "/mnt/data/vps/os_image/"
#    o.VPS_IMAGE_DIR = "/mnt/data/vps"
#    o.VPS_SWAP_DIR = "/mnt/data/swp/"
    o.VPS_METADATA_DIR = "/mnt/data/vps/metadata" 
    o.MOUNT_POINT_DIR = "/mnt/data/vps/mnt"
    o.RSYNC_CONF_PATH = "/mnt/data/vps/rsync.conf"
    o.XEN_BRIDGE = "br0"
    o.XEN_INTERNAL_BRIDGE = "br0"


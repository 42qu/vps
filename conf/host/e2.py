#!/usr/bin/env python

import os
from os.path import dirname

def prepare(o):
    base_dir = dirname (dirname (dirname (__file__)))
    o.log_dir = os.path.join (base_dir, "log") # for test
    o.RUN_DIR = os.path.join (base_dir, "run")

    o.USE_LVM = False
    o.VPS_IMAGE_DIR = "/vps"
    o.VPS_SWAP_DIR = "/swp" 
    o.VPS_METADATA_DIR = "/vps/metadata"
    o.OS_IMAGE_DIR = "/vps/images/"
    o.VPS_TRASH_DIR = "/vps/trash" 
    o.XEN_BRIDGE = "xenbr0"


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

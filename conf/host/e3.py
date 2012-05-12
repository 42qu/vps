#!/usr/bin/env python

import os
from os.path import dirname

def prepare(o):
    base_dir = dirname (dirname (dirname (__file__)))
    o.log_dir = os.path.join (base_dir, "log") # for test

    o.RUN_DIR = os.path.join (base_dir, "run")
    o.USE_LVM = True
    o.OS_IMAGE_DIR = "/data/vps/images/"
#    o.VPS_IMAGE_DIR = "/data/vps"
#    o.VPS_SWAP_DIR = "/data/swp"
    o.VPS_LVM_VGNAME="main"
    o.XEN_BRIDGE = "xenbr0"


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

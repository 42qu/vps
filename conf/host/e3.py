#!/usr/bin/env python

import os
from os.path import dirname

def prepare(o):
    o.HOST_ID = 2
    o.USE_LVM = True
    base_dir = dirname (dirname (dirname (__file__)))
    o.log_dir = os.path.join (base_dir, "log") # for test

    o.RUN_DIR = os.path.join (base_dir, "run")
    o.OS_IMAGE_DIR = "/data/vps/images/"
    o.VPS_LVM_VGNAME="main"
    o.XEN_BRIDGE = "xenbr0"


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

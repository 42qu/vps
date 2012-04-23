#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from os.path import dirname

def prepare(o):
    o.HOST_ID = 2
    base_dir = dirname (dirname (dirname (__file__)))
    o.log_dir = os.path.join (base_dir, "log")
    o.run_dir = os.path.join (base_dir, "run")
    o.os_image_dir = "/mnt/data/vps/os_image/"
    o.vps_image_dir = "/mnt/data/vps"
    o.vps_swap_dir = "/mnt/data/swp/"
    o.xen_bridge = "br0"


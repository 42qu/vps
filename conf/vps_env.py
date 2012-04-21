#!/usr/bin/env python

import os
# for log.py
log_dir = "/var/log/vps_mgr"
log_rotate_size = 20000
log_backup_count = 3
log_level = "DEBUG"
# for log.py

run_dir = "/var/run/vps_mgr"

tarball_dir = "/vps/tarball"
template_image_dir = "/vps/images"
vps_image_dir = "/vps"
vps_swap_dir = "/swp"
xen_config_dir = "/etc/xen"
xen_auto_dir = "/etc/xen/auto"
xen_bridge = "xenbr0"
mkfs_cmd = "mkfs.ext4"

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

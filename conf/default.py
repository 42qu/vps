#!/usr/bin/env python
# -*- coding: utf-8 -*-


def prepare(o):
    from os.path import join, dirname
    from _env import PREFIX
    
    o.SSL_KEY_PEM = join(dirname(PREFIX),'conf/private/key.pem')
    o.SSL_CERT = join(dirname(PREFIX),'conf/private/cacert.pem')
    o.SAAS_PORT = 50042

    o.SAAS_HOST = "saas-vps.42qu.us"
    import socket
    HOSTNAME = socket.gethostname()
    import re
    HOST_ID  = re.search("\d+",HOSTNAME)
    if HOST_ID: 
        HOST_ID = int(HOST_ID.group())
    o.HOST_ID = HOST_ID

    # for log.py
    o.log_dir = "/var/log/vps_mgr"
    o.log_rotate_size = 20000
    o.log_backup_count = 3
    o.log_level = "DEBUG"
    # for log.py

    o.run_dir = "/var/run/vps_mgr"
    o.tarball_dir = "/vps/tarball"
    o.template_image_dir = "/vps/images"
    o.vps_image_dir = "/vps"
    o.vps_swap_dir = "/swp"
    o.xen_config_dir = "/etc/xen"
    o.xen_auto_dir = "/etc/xen/auto"
    o.xen_bridge = "xenbr0"
    o.mkfs_cmd = "mkfs.ext4"

    return o


def finish(o):
    return o


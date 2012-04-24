#!/usr/bin/env python
# -*- coding: utf-8 -*-


def prepare(o):
    from os.path import join, dirname
    from _env import PREFIX
    
#    o.SSL_KEY_PEM = join(dirname(PREFIX),'conf/private/server.key')
    o.SSL_CERT = join(dirname(PREFIX),'conf/private/server.pem')
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
    o.os_image_dir = "/vps/images"
    o.vps_image_dir = "/vps"
    o.vps_swap_dir = "/swp"
    o.xen_config_dir = "/etc/xen"
    o.xen_auto_dir = "/etc/xen/auto"
    o.xen_bridge = "xenbr0"
    o.mkfs_cmd = "/sbin/mkfs.ext4 -F"
    o.os_image_dict = {
        #    2: 'CentOS-6.2',
        #    1: 'CentOS-5.8',
        #    10002: 'Ubuntu-11.10',
        #    10001: 'Ubuntu-10.04',
        #    20001: 'Debian-6.0',
        #    30001: 'Arch',
            50001: {'os':'Gentoo', 'image':'gentoo_201202_amd64.tar.gz'},
            50002: {'os':'Gentoo', 'image':'gentoo_template.img'},
        #    60001: 'Fedora',
        #   70001: 'OpenSUSE',
        #    80001: 'Slackware',
        #    90001: 'Scientific Linux',
        #   100001: 'NetBSD',
    }

    return o


def finish(o):
    return o


#!/usr/bin/env python
# -*- coding: utf-8 -*-


def prepare(o):
    from os.path import join, dirname
    from _env import PREFIX

    o.USE_OVS = False
    o.OVS_DB_SOCK = "unix:/var/run/openvswitch/db.sock"
#    o.SSL_CERT = join(dirname(PREFIX),'conf/private/server.pem')
    from private.saas import KEY
    o.KEY = KEY
    o.SAAS_PORT = 50042
    o.SAAS_HOST = "0.0.0.0"
    o.TIME_ZONE = "Asia/Shanghai"

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
    o.XEN_PYTHON_LIB = "/usr/lib/xen-default/lib/python/"
    o.SAVE_PATH = "/data/vps/save"

    o.VPS_NUM_LIMIT = None
    o.RUN_DIR = "/var/run/vps_mgr"
    o.OS_IMAGE_DIR = "/data/vps/images"
    o.VPS_METADATA_DIR = "/data/vps/metadata" 
    o.MOUNT_POINT_DIR = "/data/vps/mnt"
    o.VPS_TRASH_DIR = "/data/vps/trash" # no needed when USE_LVM=True
    o.VPS_IMAGE_DIR = "/data/vps" # no needed when USE_LVM=True
    o.VPS_SWAP_DIR = "/data/swp" # no needed when USE_LVM=True
    #o.METRIC_SERVER = "carbonserver"
    o.USE_LVM=True
    o.VPS_LVM_VGNAME="main"
    o.LVM_VG_MIN_SPACE = 100 # leave 100G in the VG for temporary needs
    o.XEN_CONFIG_DIR = "/etc/xen"
    o.XEN_AUTO_DIR = "/etc/xen/auto"
    o.MONITOR_COLLECT_INV = 30  # in sec
    o.LARGE_NETFLOW = 6.0 * 1024 * 1024 # in bit
    o.XEN_BRIDGE = "xenbr0"
    o.EXT_INF = "eth0"
    o.XEN_INTERNAL_BRIDGE = "xenbr1"
    o.INT_INF = "eth1"
    o.RSYNC_CONF_PATH = "/data/vps/rsync.conf"
    o.RSYNC_PORT = 26554
    o.INF_PORT = 26550
    o.SAAS_RECOVER_THRESHOLD = 5
    o.SAAS_BAD_THRESHOLD = 60 * 3
    o.MAIN_DISK = "/dev/sda"

    o.DEFAULT_FS_TYPE = 'ext4'
    o.CLOSE_EXPIRE_DAYS = 0.8
    o.CGROUP_SCRIPT_DIR = "/data/vps/cgroup/"
    o.BLK_READ_IOPS = 1000
    o.BLK_WRITE_IOPS = 800
    o.BLK_READ_BPS = 12 * 1000 * 1000
    o.BLK_WRITE_BPS = 7 * 1000 * 1000
    o.BLK_SWAP_IOPS = 150
    o.BLK_SWAP_BPS = 2 * 1000 * 1000

    o.OS_IMAGE_DICT = {
            4: {'os':'CentOS', 'version':'6.3-amd64', 'image': 'centos-6.3-amd64.tar.gz'},
            3: {'os':'CentOS', 'version': '5.9-i386', 'image': 'centos-5.9-i386.tar.gz'},
            2: {'os':'CentOS', 'version':'6.2-amd64', 'image': 'centos-6.2-amd64.tar.gz'},
            1: {'os':'CentOS', 'version': '5.8-i386', 'image': 'centos-5.8-i386.tar.gz'},
        10003: {'os': 'Ubuntu', 'version': '12.04-amd64', 'image': 'ubuntu-12.04-amd64.tar.gz'},
        10002: {'os': 'Ubuntu', 'version': '11.10-amd64', 'image': 'ubuntu-11.10-amd64.tar.gz'},
        10001: {'os': 'Ubuntu', 'version': '10.04-amd64', 'image': 'ubuntu-10.04-amd64.tar.gz'},
        20001: {'os': 'Debian', 'version': '6.0-amd64', 'image': 'debian-6.0-amd64.tar.gz'},
        20002: {'os': 'Debian', 'version': '7.0-amd64', 'image': 'debian-7.0-amd64.tar.gz'},
        30001: {'os': 'Arch', 'image': 'arch-2011.08.19-i386-fs-ext3.tar.gz'},
        50001: {'os':'Gentoo', 'image':'gentoo-2013.04.03-amd64.tar.gz'},
        60001: {'os': 'Fedora'},
        70001: {'os': 'OpenSUSE'},
        80001: {'os':'Slackware'},
        90001: {'os':'Scientific'},
        100001: {'os':'NetBSD'},
    }

    o.SMS_NUMBER_LIST = (
        "13693622296",
    )

    return o


def finish(o):
    return o


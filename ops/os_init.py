#!/usr/bin/env python

import re
import os
import _env
from lib.command import call_cmd
from vps import XenVPS
import string

def os_init (vps, vps_mountpoint, os_type, os_version, to_init_passwd=True):
    assert isinstance (vps, XenVPS)
    
    if os_type.find ('gentoo') == 0:
        gentoo_init (vps, vps_mountpoint)
    elif re.match (r'^(redhat|rhel|centos).*', os_type):
        redhat_init (vps, vps_mountpoint)
    elif re.match (r'^(debian|ubuntu).*$', os_type):
        debian_init (vps, vps_mountpoint)
    elif os_type.find ('arch') == 0:
        arch_init (vps, vps_mountpoint)
    else:
        raise NotImplementedError ()
    if to_init_passwd:
        set_root_passwd (vps, vps_mountpoint)
    gen_fstab (vps, vps_mountpoint)


def gen_fstab (vps, vps_mountpoint):

    fstab_t = string.Template ("""
/dev/$root_xen_dev		 /                      $root_fs_type    defaults,noatime        1 1
tmpfs                   /dev/shm                tmpfs   defaults        0 0
devpts                  /dev/pts                devpts  gid=5,mode=620  0 0
sysfs                   /sys                    sysfs   defaults        0 0
proc                    /proc                   proc    defaults        0 0
""")
    fstab = fstab_t.substitute (root_xen_dev=vps.root_store.xen_dev, root_fs_type=vps.root_store.fs_type)
    if vps.swap_store.size_g > 0:
        fstab += "/dev/%s   none    swap    sw  0 0\n"  % (vps.swap_store.xen_dev)
    keys = vps.data_disks.keys ()
    keys.remove (vps.root_store.xen_dev)
    keys.sort ()
    for k in keys:
        disk = vps.data_disks[k]
        if disk.mount_point and disk.mount_point not in ['none', '/']:
            fstab += "/dev/%s   %s  %s  defaults    0 0\n" % (disk.xen_dev, disk.mount_point, disk.fs_type) 
            mount_dir = os.path.join (vps_mountpoint, disk.mount_point.strip ("/"))
            os.makedirs (mount_dir, 0755)
    f = open (os.path.join (vps_mountpoint, "etc/fstab"), 'w')
    try:
        f.write (fstab)
    finally:
        f.close ()

def set_root_passwd (vps, vps_mountpoint):
    sh_script = """
echo 'root:%s' | /usr/sbin/chpasswd
""" % (vps.root_pw)

    user_data = os.path.join (vps_mountpoint, "root/user_data")
    f = open (user_data, "w")
    try:
        try:
            f.write (sh_script)
        finally:
            f.close ()
        call_cmd ("chroot %s /bin/sh /root/user_data" % (vps_mountpoint)) # chroot's path varies among linux distribution
    finally:
        if os.path.exists (user_data):
            os.remove (user_data)
    

def gentoo_init (vps, vps_mountpoint):
    vm_net_config_content = string.Template ("""
config_eth0="$ADDRESS netmask $NETMASK"
routes_eth0="default via $GATEWAY"
""").substitute (ADDRESS=vps.ip, NETMASK=vps.netmask, GATEWAY=vps.gateway)
    f = open (os.path.join (vps_mountpoint, "etc/conf.d/hostname"), "w+")
    try:
        f.write ('hostname="%s"\n' % (vps.name))
    finally:
        f.close ()
    f = open (os.path.join (vps_mountpoint, "etc/conf.d/net"), "w+")
    try:
        f.write (vm_net_config_content)
    finally:
        f.close ()


def debian_init (vps, vps_mountpoint):
    f = open (os.path.join (vps_mountpoint, "etc/hostname"), "w+")
    try:
        f.write ('%s\n' % (vps.name))
    finally:
        f.close ()

    vm_net_config_content = string.Template("""
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
address $ADDRESS
netmask $NETMASK
gateway $GATEWAY
""").substitute (ADDRESS=vps.ip, NETMASK=vps.netmask, GATEWAY=vps.gateway)
    f = open (os.path.join (vps_mountpoint, "etc/network/interfaces"), "w+")
    try:
        f.write (vm_net_config_content)
    finally:
        f.close ()


def redhat_init (vps, vps_mountpoint):
    network = """
NETWORKING=yes
HOSTNAME=%s
""" % (vps.name)
    f = open (os.path.join (vps_mountpoint, "etc/sysconfig/network"), "w+")
    try:
        f.write (network)
    finally:
        f.close ()
    ifcfg_eth0 = string.Template ("""
DEVICE=eth0
BOOTPROTO=none
ONBOOT=yes
TYPE=Ethernet
IPADDR=$ADDRESS
NETMASK=$NETMASK
GATEWAY=$GATEWAY
""").substitute (ADDRESS=vps.ip, NETMASK=vps.netmask, GATEWAY=vps.gateway)
    f = open (os.path.join (vps_mountpoint, "etc/sysconfig/network-scripts/ifcfg-eth0"), "w+")
    try:
        f.write (ifcfg_eth0)
    finally:
        f.close ()
    

def arch_init (vps, vps_mountpoint):
    rcconf = string.Template ("""
LOCALE="en_US.utf8"
HARDWARECLOCK="UTC"
USEDIRECTISA="no"
TIMEZONE="America/New_York"
KEYMAP="us"
CONSOLEFONT=
CONSOLEMAP=
USECOLOR="yes"
MOD_AUTOLOAD="yes"
MODULES=()
HOSTNAME="arch"
USELVM="no"
interface=eth0
address=$ADDRESS
netmask=$NETMASK
gateway=$GATEWAY
DAEMONS=(syslog-ng network crond sshd)

""").substitute (HOSTNAME=vps.name, ADDRESS=vps.ip, NETMASK=vps.netmask, GATEWAY=vps.gateway)
    f = open (os.path.join (vps_mountpoint, "etc/rc.conf"), "w+")
    try:
        f.write (rcconf)
    finally:
        f.close ()

    

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

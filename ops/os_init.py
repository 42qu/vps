#!/usr/bin/env python

import os
import _env
from lib.command import call_cmd
from vps import XenVPS

def os_init (vps, vps_mountpoint):
    assert isinstance (vps, XenVPS)
    
    os_type = vps.os_type
    if os_type == 'gentoo':
        gentoo_init (vps, vps_mountpoint)
    elif os_type == 'redhat' or os_type == 'centos':
        redhat_init (vps, vps_mountpoint)
    elif os_type == 'debian' or os_type == 'ubuntu':
        debian_init (vps, vps_mountpoint)
    else:
        raise NotImplementedError ()
    set_root_passwd (vps, vps_mountpoint)


def set_root_passwd (vps, vps_mountpoint):
    sh_script = """
echo 'root:%s' | /usr/sbin/chgpasswd
""" % (vps.root_pw)

    user_data = os.path.join (vps_mountpoint, "tmp/user_data")
    f = open (user_data, "w")
    try:
        try:
            f.write (sh_script)
        finally:
            f.close ()
        call_cmd ("/bin/chroot %s /bin/sh /tmp/user_data")
    finally:
        if os.path.exists (user_data):
            os.remove (user_data)
    

def gentoo_init (vps, vps_mountpoint):
    vm_net_config_content = """
config_eth0="%s netmask %d"
routes_eth0="default via %s"
""" % (vps.ip, vps.netmask, vps.gateway)
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

    vm_net_config_content = """
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
address %s
netmask %s
gateway %s
""" % (vps.ip, vps.netmask, vps.gateway)
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
    ifcfg_eth0 = """
DEVICE=eth0
BOOTPROTO=none
ONBOOT=yes
TYPE=Ethernet
IPADDR=%s
NETMASK=%s
GATEWAY=%s
""" % (vps.ip, vps.netmask, vps.gateway)
    f = open (os.path.join (vps_mountpoint, "etc/sysconfig/network-scripts/ifcfg-eth0"))
    try:
        f.write (ifcfg_eth0)
    finally:
        f.close ()
    


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

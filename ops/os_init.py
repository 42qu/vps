#!/usr/bin/env python

import re
import os
import ops._env
from lib.command import call_cmd
from ops.vps import XenVPS
import string
import time
import crypt
import shutil
import conf
TIMEZONE = None

DNS_SERVERS = None
if 'TIME_ZONE' in dir(conf):
    TIME_ZONE = conf.TIME_ZONE
if 'DNS_SERVERS' in dir(conf):
    DNS_SERVERS = conf.DNS_SERVERS

def os_init (xv, vps_mountpoint, os_type, os_version, is_new=True, to_init_passwd=False, to_init_fstab=False):
    assert isinstance (xv, XenVPS)
    assert vps_mountpoint and os.path.exists (vps_mountpoint)
    
    if os_type.find ('gentoo') == 0:
        gentoo_init (xv, vps_mountpoint)
    elif re.match (r'^(redhat|rhel|centos).*', os_type):
        redhat_init (xv, vps_mountpoint)
    elif re.match (r'^(debian|ubuntu).*$', os_type):
        debian_init (xv, vps_mountpoint)
    elif os_type.find ('arch') == 0:
        arch_init (xv, vps_mountpoint)
    else:
        raise NotImplementedError ()
    set_timezone (vps_mountpoint)
    if is_new or to_init_passwd:
        set_root_passwd_2 (xv, vps_mountpoint)
    if is_new or to_init_fstab:
        gen_fstab (xv, vps_mountpoint)
    if is_new:
        clean_up (vps_mountpoint)

def clean_up (vps_mountpoint):
    files = [
            "root/.bash_history",
            "root/.ssh/known_hosts",
            "var/log/syslog",
            "var/log/messages",
            "var/log/audit.log",
            ]
    for file_path in files:
        a_path = os.path.join (vps_mountpoint, file_path)
        if os.path.isfile (a_path):
            print "remove %s" % (a_path)
            os.remove (a_path)

def migrate_users (xv, vps_mountpoint, vps_mountpoint_old):
    passwd_path_old = os.path.join (vps_mountpoint_old, "etc", "passwd")
    shadow_path_old = os.path.join (vps_mountpoint_old, "etc", "shadow")
    group_path_old = os.path.join (vps_mountpoint_old, "etc", "group")
    passwd_path = os.path.join (vps_mountpoint, "etc", "passwd")
    shadow_path = os.path.join (vps_mountpoint, "etc", "shadow")
    group_path = os.path.join (vps_mountpoint, "etc", "group")
    passwd_data = {}
    shadow_data = {}
    group_data = {}
    root_shadow = None
    lines = None

    def __parse (filepath, data_dict):
        f = open (filepath, "r")
        try:
            lines = f.readlines ()
        finally:
            f.close ()
        for line in lines: 
            line = line.strip ("\n")
            arr = line.split (":")
            if arr[2]:
                ugid = int(arr[2])
                if  ugid >= 500 and ugid != 65534: # non-system users/groups are copied
                    data_dict[arr[0]] = line
        return
    __parse (passwd_path_old, passwd_data)
    __parse (group_path_old, group_data)
    
    f = open (shadow_path_old, "r")
    try:
        lines = f.readlines ()
    finally:
        f.close ()
    for line in lines:
        line = line.strip ("\n")
        arr = line.split (":")
        if arr[0] == 'root':
            root_shadow = arr[1]
        elif passwd_data.has_key (arr[0]):
            shadow_data[arr[0]] = line
    
    def __append_data (filepath, data_dict):
        f = open (filepath, "a")
        try:
            for line in data_dict.itervalues ():
                f.write (line + '\n')
        finally:
            f.close()
        return
    #write passwd & group
    __append_data (passwd_path, passwd_data)
    __append_data (group_path, group_data)
    
    f = open (shadow_path, "r")
    shadow_arr = []
    try:
        lines = f.readlines()
    finally:
        f.close ()
    for line in lines:
        line = line.strip ("\n")
        arr = line.split (":")
        if arr[0] == 'root':
            arr[1] = root_shadow
            arr[2] = str(int(time.time ()))
            shadow_arr.append (":".join (arr))
        else:
            shadow_arr.append (line)
    shadow_arr += shadow_data.values ()
    s = os.stat (shadow_path)
    old_mode = s.st_mode
    #write shadow
    f = open (shadow_path, "w")
    try:
        f.write ("\n".join (shadow_arr))
    finally:
        f.close ()
    os.chmod (shadow_path, old_mode)
    

def gen_fstab (xv, vps_mountpoint):

    fstab_t = string.Template (
"""/dev/$root_xen_dev		 /                      $root_fs_type    defaults,noatime        1 1
tmpfs                   /dev/shm                tmpfs   defaults        0 0
devpts                  /dev/pts                devpts  gid=5,mode=620  0 0
sysfs                   /sys                    sysfs   defaults        0 0
proc                    /proc                   proc    defaults        0 0
""")
    fstab = fstab_t.substitute (root_xen_dev=xv.root_store.xen_dev, root_fs_type=xv.root_store.get_fs_type ())
    if xv.swap_store.size_g > 0:
        fstab += "/dev/%s   none    swap    sw  0 0\n"  % (xv.swap_store.xen_dev)
    keys = xv.data_disks.keys ()
    keys.remove (xv.root_store.xen_dev)
    keys.sort ()
    for k in keys:
        disk = xv.data_disks[k]
        if disk.mount_point and disk.mount_point not in ['none', '/']:
            fstab += "/dev/%s   %s  %s  defaults    0 0\n" % (disk.xen_dev, disk.mount_point, disk.get_fs_type ()) 
            mount_dir = os.path.join (vps_mountpoint, disk.mount_point.strip ("/"))
            if not os.path.exists (mount_dir):
                os.makedirs (mount_dir, 0755)
    f = open (os.path.join (vps_mountpoint, "etc/fstab"), 'w')
    try:
        f.write (fstab)
    finally:
        f.close ()

def gen_resolv (vps_mountpoint):
    if DNS_SERVERS:
        resolv_path = os.path.join (vps_mountpoint, "etc/resolv.conf")
        if not os.path.isfile (resolv_path):
            return False
        resolv_content = "".join (
                map (lambda s: "nameserver %s\n" % (s), DNS_SERVERS) 
                )
        f = open (resolv_path, "w")
        try:
            f.write (resolv_content)
        finally:
            f.close ()
        return True

def set_timezone (vps_mountpoint):
    if TIME_ZONE:
        localtime_path = os.path.join (vps_mountpoint, "etc/localtime")
        zone_info_path = os.path.join (vps_mountpoint, "usr/share/zoneinfo/", TIME_ZONE)
    shutil.copy (zone_info_path, localtime_path)

def set_root_passwd (xv, vps_mountpoint):
    if not xv.root_pw:
        print "orz, root passwd is empty, skip"
        return
    sh_script = """
echo 'root:%s' | /usr/sbin/chpasswd
""" % (xv.root_pw)

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

def generate_shadow_hash (passwd):
    return crypt.crypt(passwd, '\$5\$SA213LTsalt\$')
    
def set_root_passwd_2 (xv, vps_mountpoint):
    root_shadow = generate_shadow_hash (xv.root_pw)
    shadow_path = os.path.join (vps_mountpoint, "etc", "shadow")
    f = open (shadow_path, "r")
    shadow_arr = []
    try:
        lines = f.readlines()
    finally:
        f.close ()
    for line in lines:
        line = line.strip ("\n")
        arr = line.split (":")
        if arr[0] == 'root':
            arr[1] = root_shadow
            arr[2] = str(int(time.time ()))
            shadow_arr.append (":".join (arr))
        else:
            shadow_arr.append (line)
    s = os.stat (shadow_path)
    old_mode = s.st_mode
    #write shadow
    f = open (shadow_path, "w")
    try:
        f.write ("\n".join (shadow_arr))
    finally:
        f.close ()
    os.chmod (shadow_path, old_mode)

def gentoo_init (xv, vps_mountpoint):

    f = open (os.path.join (vps_mountpoint, "etc/conf.d/hostname"), "w+")
    try:
        f.write ('hostname="%s"\n' % (xv.name))
    finally:
        f.close ()
    gen_resolv (vps_mountpoint)
    vm_net_config = ""
    vif_keys = xv.vifs.keys ()
    vif_keys.sort ()
    for i in xrange (0, len (vif_keys)):
        vif_name = vif_keys[i]
        vif = xv.vifs.get (vif_name)
        vm_net_eth = string.Template ("""
config_eth$NUMBER="$IPS"
""").substitute (
        NUMBER=i,
        IPS="\n".join (map (lambda x: "%s netmask %s" % (x[0], x[1]), vif.ip_dict.items ())),
        )
        net_lo_path = os.path.join (vps_mountpoint, "etc/init.d/net.lo")
        net_eth_path = os.path.join (vps_mountpoint, "etc/init.d/net.eth%d" % (i))
        runlevel_net_eth_path = os.path.join (vps_mountpoint, "etc/runlevels/default/net.eth%d" % (i))
        if not os.path.islink (net_eth_path):
            os.symlink ("/etc/init.d/net.lo", net_eth_path)
        if not os.path.islink (runlevel_net_eth_path):
            os.symlink ("/etc/init.d/net.eth%d" % (i), runlevel_net_eth_path)
        vm_net_config += vm_net_eth
        if i == 0 and xv.gateway: 
            vm_route = string.Template ("""routes_eth0="default via $GATEWAY"
    """).substitute (GATEWAY=xv.gateway)
            vm_net_config += vm_route

    f = open (os.path.join (vps_mountpoint, "etc/conf.d/net"), "w+")
    try:
        f.write (vm_net_config)
    finally:
        f.close ()

def _debain_vif (eth_name, vif, gateway_ip=None):
    ips = vif.ip_dict.items ()
    assert len(ips) > 0
    eth_conf = string.Template("""
auto $ETH
iface $ETH inet static
    address $ADDRESS
    netmask $NETMASK
""").substitute (ETH=eth_name, ADDRESS=ips[0][0], NETMASK=ips[0][1])
    if gateway_ip:
        eth_conf += "\tgateway %s\n" % (gateway_ip)
    if DNS_SERVERS:
        eth_conf += "\tdns-nameservers %s" % (" ".join (DNS_SERVERS))

    if len (ips) > 1:
        for i in xrange (1, len (ips)):
            eth_conf += string.Template("""
auto $ETH:$NUMBER
iface $ETH:$NUMBER inet static
    address $ADDRESS
    netmask $NETMASK
""").substitute (ETH=eth_name, NUMBER=i, ADDRESS=ips[i][0], NETMASK=ips[i][1])
    return eth_conf



def debian_init (xv, vps_mountpoint):
    f = open (os.path.join (vps_mountpoint, "etc/hostname"), "w+")
    try:
        f.write ('%s\n' % (xv.name))
    finally:
        f.close ()
    gen_resolv (vps_mountpoint)

    vm_net_config = """
auto lo
iface lo inet loopback
"""
    vif_keys = xv.vifs.keys ()
    vif_keys.sort ()
    for i in xrange (0, len (vif_keys)):
        vif_name = vif_keys[i]
        vif = xv.vifs.get (vif_name)
        vm_net_config += _debain_vif ("eth%d" % i, vif, i == 0 and xv.gateway or None)
        
    f = open (os.path.join (vps_mountpoint, "etc/network/interfaces"), "w+")
    try:
        f.write (vm_net_config)
    finally:
        f.close ()

def _redhat_vif (eth_name, vif, vps_mountpoint, gateway_ip=None):
    ips = vif.ip_dict.items ()
    assert len(ips) > 0
    ifcfg_eth = string.Template ("""
DEVICE=$ETH
BOOTPROTO=none
ONBOOT=yes
TYPE=Ethernet
IPADDR=$ADDRESS
NETMASK=$NETMASK
""").substitute (ETH=eth_name, ADDRESS=ips[0][0], NETMASK=ips[0][1])
    if gateway_ip:
        ifcfg_eth += "GATEWAY=%s\n" % gateway_ip
    f = open (os.path.join (vps_mountpoint, "etc/sysconfig/network-scripts/ifcfg-%s" % (eth_name)), "w+")
    try:
        f.write (ifcfg_eth)
    finally:
        f.close ()
 
    if len (ips) > 1:
        for i in xrange (1, len (ips)):
            ifcfg_eth = string.Template ("""
DEVICE=$ETH:$NUMBER
BOOTPROTO=None
ONBOOT=yes
TYPE=Ethernet
IPADDR=$ADDRESS
NETMASK=$NETMASK
""").substitute (ETH=eth_name, NUMBER=i, ADDRESS=ips[i][0], NETMASK=ips[i][1])
            f = open (os.path.join (vps_mountpoint, "etc/sysconfig/network-scripts/ifcfg-%s:%s" % (eth_name, i)), "w+")
            try:
                f.write (ifcfg_eth)
            finally:
                f.close ()
     


def redhat_init (xv, vps_mountpoint):

    gen_resolv (vps_mountpoint)

    network = """
NETWORKING=yes
HOSTNAME=%s
""" % (xv.name)
    f = open (os.path.join (vps_mountpoint, "etc/sysconfig/network"), "w+")
    try:
        f.write (network)
    finally:
        f.close ()

    vif_keys = xv.vifs.keys ()
    vif_keys.sort ()
    for i in xrange (0, len (vif_keys)):
        vif_name = vif_keys[i]
        vif = xv.vifs.get (vif_name)
        _redhat_vif ("eth%d" % (i), vif, vps_mountpoint, i == 0 and xv.gateway or None)

   

def arch_init (xv, vps_mountpoint):

    gen_resolv (vps_mountpoint)

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

""").substitute (HOSTNAME=xv.name, ADDRESS=xv.ip, NETMASK=xv.netmask, GATEWAY=xv.gateway)
    f = open (os.path.join (vps_mountpoint, "etc/rc.conf"), "w+")
    try:
        f.write (rcconf)
    finally:
        f.close ()

    

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

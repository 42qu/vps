#!/usr/bin/env python

import re
import os

import _env
from string import Template
import vps_common
from ops.vps_store import VPSStoreImage, VPSStoreLV, VPSStoreBase
from ops.vps_netinf import VPSNetInf


import conf
assert conf.XEN_BRIDGE
assert conf.XEN_CONFIG_DIR
assert conf.XEN_AUTO_DIR
assert conf.DEFAULT_FS_TYPE
import xen
import time



class XenVPS (object):
    """ needs root to run xen command """

    xen_inf = None
    name = None
    root_store = None
    swap_store = None
    config_path = None
    auto_config_path = None
    xen_bridge = None
    has_all_attr = False
    vcpu = None
    mem_m = None
    disk_g = None
    ip = None # main ip
    netmask = None # main ip netmask
    gateway = None
    template_image = None
    root_pw = None
    data_disks = None
    os_id = None

    def __init__ (self, _id):
        self.vps_id = _id
        self.name = "vps%s" % (str(_id).zfill (2)) # to be compatible with current practice standard
        self.config_path = os.path.join (conf.XEN_CONFIG_DIR, self.name)
        self.auto_config_path = os.path.join (conf.XEN_AUTO_DIR, self.name)
        self.xen_bridge = conf.XEN_BRIDGE
        self.has_all_attr = False
        self.xen_inf = xen.get_xen_inf ()
        self.data_disks = {}
        self.vifs = {}

    def to_meta (self):
        data = {}
        data['vps_id'] = self.vps_id
        data['os_id'] = self.os_id
        data['vcpu'] = self.vcpu
        data['mem_m'] = self.mem_m
        data['root_size_g'] = self.root_store.size_g
        data['swap_size_g'] = self.swap_store.size_g
        data['root_xen_dev'] = self.root_store.xen_dev
        data['gateway'] = self.gateway
        data['ip'] = self.ip
        data['netmask'] = self.netmask
        disks = []
        for disk in self.data_disks.itervalues ():
            if disk.xen_dev != self.root_store.xen_dev:
                disk_data = disk.to_meta ()
                assert disk_data
                disks.append (disk_data)
        data['data_disks'] = disks
        vifs = []
        for vif in self.vifs.itervalues ():
            if vif.ip != self.ip:
                vif_data = vif.to_meta ()
                assert vif_data
                vifs.append (vif_data)
        data['vifs'] = vifs
        return data

    @classmethod
    def from_meta (cls, data):
        assert data
        self = cls (data['vps_id'])
        self.setup (data['os_id'], data['vcpu'], data['mem_m'], data['root_size_g'], None, 
                data['gateway'], data['ip'], data['netmask'], data['swap_size_g'])
        for _disk in data['data_disks']:
            disk = VPSStoreBase.from_meta (_disk)
            assert disk
            self.data_disks[disk.xen_dev] = disk
        for _vif in data['vifs']:
            vif = VPSNetInf.from_meta (_vif)
            self.vifs[vif.ifname] = vif
        return self

    def setup (self, os_id, vcpu, mem_m, disk_g, root_pw=None, gateway=None, ip=None, netmask=None, swp_g=None):
        """ on error will raise Exception """
        assert mem_m > 0 and disk_g > 0 and vcpu > 0
        self.has_all_attr = True
        self.os_id = os_id
        self.vcpu = vcpu
        self.mem_m = mem_m
        if swp_g is not None:
            swp_g = swp_g
        else:
            if self.mem_m >= 2000:
                swp_g = 2
            else:
                swp_g = 1

        if conf.USE_LVM:
            assert conf.VPS_LVM_VGNAME
            self.root_store = VPSStoreLV ("xvda1", conf.VPS_LVM_VGNAME, "%s_root" % self.name, None, '/', disk_g)
            self.swap_store = VPSStoreLV ("xvda2", conf.VPS_LVM_VGNAME, "%s_swap" % self.name, 'swap', 'none', swp_g)
        else:
            self.root_store = VPSStoreImage ("xvda1", conf.VPS_IMAGE_DIR, conf.VPS_TRASH_DIR, "%s.img" % self.name,
                    None, '/', disk_g)
            self.swap_store = VPSStoreImage ("xvda2", conf.VPS_SWAP_DIR, conf.VPS_TRASH_DIR, "%s.swp" % self.name, 
                    'swap', 'none', swp_g)

        self.data_disks[self.root_store.xen_dev] = self.root_store

        self.root_pw = root_pw
        self.gateway = gateway
        if ip:
            assert ip and netmask is not None and gateway and isinstance (netmask, basestring)
            self.ip = ip
            self.netmask = netmask
            self.add_netinf (self.name, ip, netmask, bridge=self.xen_bridge, mac=None)
        

    def add_extra_storage (self, disk_id, size_g, fs_type=conf.DEFAULT_FS_TYPE):
        assert disk_id > 0
        assert size_g > 0
        xen_dev = "xvdc%d" % (disk_id)
        mount_point = '/mnt/data%d' % (disk_id)
        if conf.USE_LVM:
            assert conf.VPS_LVM_VGNAME
            lv_name = "%s_data%s" % (self.name, disk_id)
            self.data_disks[xen_dev] = VPSStoreLV (xen_dev, conf.VPS_LVM_VGNAME, lv_name, fs_type, mount_point, size_g)
        else:
            filename = "%s_data%s.img" % (self.name, disk_id)
            self.data_disks[xen_dev] = VPSStoreImage (xen_dev, conf.VPS_IMAGE_DIR, conf.VPS_TRASH_DIR, filename, fs_type, mount_point, size_g)

    def add_netinf (self, name, ip, netmask, bridge, mac):
        mac = mac or vps_common.gen_mac ()
        self.vifs[name] = VPSNetInf (ifname=name, ip=ip, netmask=netmask, mac=mac, bridge=bridge)


    def check_resource_avail (self, ignore_trash=False):
        """ on error or space not available raise Exception """
        assert self.has_all_attr
        if self.is_running ():
            raise Exception ("check resource: %s is running, no need to create" % (self.name))
        mem_free = self.xen_inf.mem_free ()
        if self.mem_m > mem_free:
            raise Exception ("check resource: xen free memory is not enough  (%dM left < %dM)" % (mem_free, self.mem_m))
        #check disks not implemented, too complicate, expect error throw during vps creation
        # check ip available
        if 0 == os.system ("ping -c2 -W1 %s >/dev/null" % (self.ip)):
            raise Exception ("check resource: ip %s is in use" % (self.ip))
        if os.system ("ping -c2 -W1 %s >/dev/null" % (self.gateway)):
            raise Exception ("check resource: gateway %s is not reachable" % (self.gateway))
        if not ignore_trash:
            if os.path.exists (self.config_path):
                raise Exception ("check resource: %s already exists" % (self.config_path))
            if self.root_store.exists ():
                raise Exception ("check resource: %s already exists" % (str(self.root_store)))
            if self.swap_store.exists ():
                raise Exception ("check resource: %s already exists" % (str(self.swap_store)))

    def gen_xenpv_config (self):
        assert self.has_all_attr
        # must called after setup ()

        all_t = Template ("""
bootloader = "/usr/bin/pygrub"
name = "$name"
vcpus = "$vcpu"
maxmem = "$mem"
memory = "$mem"
vif = [ $vifs ]
disk = [ $disks ]
root = "/dev/xvda1"
extra = "fastboot independent_wallclock=1"
on_shutdown = "destroy"
on_poweroff = "destroy"
on_reboot = "restart"
on_crash = "restart"
""" )

        vif_t = Template ("""  "vifname=$ifname,mac=$mac,ip=$ip,bridge=$bridge"  """)
        disk_t = Template (""" "$path,$dev,$mod" """)
        disks = []
        vifs = []
        disk_keys = self.data_disks.keys ()
        disk_keys.sort ()
        disks.append (disk_t.substitute (path=self.root_store.xen_path, dev=self.root_store.xen_dev, mod="w") )
        if self.swap_store.size_g > 0:
            disks.append ( disk_t.substitute (path=self.swap_store.xen_path, dev=self.swap_store.xen_dev, mod="w") )
        for k in disk_keys:
            data_disk = self.data_disks[k]
            if k != self.root_store.xen_dev:
                disks.append ( disk_t.substitute (path=data_disk.xen_path, dev=data_disk.xen_dev, mod="w") )

        for vif in self.vifs.values ():
            vifs.append ( vif_t.substitute (ifname=vif.ifname, mac=vif.mac, ip=vif.ip, bridge=vif.bridge) )

        xen_config = all_t.substitute (name=self.name, vcpu=str(self.vcpu), mem=str(self.mem_m), 
                    disks=",".join (disks), vifs=",".join (vifs)
                )
        return xen_config
       
    def is_running (self):
        return self.xen_inf.is_running (self.name)

    def start (self):
        if self.is_running ():
            return
        self.xen_inf.create (self.config_path)
        start_ts = time.time ()
        while True:
            time.sleep (1)
            if self.is_running ():
                return 
            now = time.time ()
            if now - start_ts > 5:
                raise Exception ("failed to create domain %s" % (self.name))


    def stop (self):
        """ shutdown a vps, because os needs time to shutdown, will wait for 30 sec until it's really not running
            if shutdowned, returns True, otherwise return False
        """
        if not self.is_running ():
            return True
        self.xen_inf.shutdown (self.name)
        start_ts = time.time ()
        while True:
            time.sleep (1)
            if not self.is_running ():
                return True
            now = time.time ()
            if now - start_ts > 30:
                # shutdown failed
                return False

    def destroy (self):
        """ if failed to destroy, raise Exception """
        self.xen_inf.destroy (self.name)
        start_ts = time.time ()
        while True:
            time.sleep (1)
            if not self.is_running ():
                return
            now = time.time ()
            if now - start_ts > 5:
                raise Exception ("cannot destroy %s after 5 sec" % (self.name))


    def wait_until_reachable (self, timeout=20):
        """ wait for the vps to be reachable and return True, or timeout returns False"""
        start_ts = time.time ()
        if not self.ip:
            raise Exception ("%s has no ip, vps object not properly setup" % (self.name))
        while True:
            time.sleep (1)
            if 0 == os.system ("ping -c1 -W1 %s>/dev/null" % (self.ip)):
                return True
            now = time.time ()
            if now - start_ts > timeout:
                return False

    def create_autolink (self):
        if os.path.exists(self.auto_config_path):
            if os.path.islink (self.auto_config_path):
                dest = os.readlink (self.auto_config_path)
                if not os.path.isabs (dest):
                    dest = os.path.join (os.path.dirname(self.auto_config_path), dest)
                if dest == os.path.abspath(self.config_path):
                    return
                os.remove (self.auto_config_path)
            else:
                raise Exception ("a non link file %s is blocking link creation" % (self.auto_config_path))
        os.symlink(self.config_path, self.auto_config_path)
                
            



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

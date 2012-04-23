#!/usr/bin/env python

import re
import os

import _env
from string import Template
import vps_common
import os_image


import conf
assert conf.xen_bridge
assert conf.vps_image_dir
assert conf.vps_swap_dir
assert conf.xen_config_dir
assert conf.xen_auto_dir
assert conf.mkfs_cmd


class XenVPS (object):

    name = None
    img_path = None
    swp_path = None
    config_path = None
    auto_config_path = None
    xen_bridge = None
    has_all_attr = False
    vcpu = None
    mem_m = None
    disk_g = None
    swp_g = None
    mac = None
    ip = None
    netmask = None
    gateway = None
    template_image = None
    os_type = None
    os_version = None
    root_pw = None

    def __init__ (self, _id):
        self.name = "vps%s" % str(_id)
        self.img_path = os.path.join (conf.vps_image_dir, self.name + ".img")
        self.swp_path = os.path.join (conf.vps_swap_dir, self.name + ".swp")
        self.config_path = os.path.join (conf.xen_config_dir, self.name)
        self.auto_config_path = os.path.join (conf.xen_auto_dir, self.name)
        self.xen_bridge = conf.xen_bridge
        self.has_all_attr = False

    def setup (self, os_id, vcpu, mem_m, disk_g, ip, netmask, gateway, root_pw, mac=None, swp_g=None):
        """ on error will raise Exception """
        assert mem_m > 0 and disk_g > 0 and vcpu > 0
        assert ip and netmask is not None and gateway
        self.has_all_attr = True
        self.vcpu = vcpu
        self.mem_m = mem_m
        self.disk_g = disk_g
        if swp_g:
            self.swp_g = swp_g
        else:
            if self.mem_m >= 2000:
                self.swp_g = 2
            else:
                self.swp_g = 1
        self.mac = mac and vps_common.gen_mac ()
        self.ip = ip
        self.netmask = netmask
        self.gateway = gateway
        self.root_pw = root_pw
        self.template_image, self.os_type, self.os_version = os_image.find_os_image (os_id)

    def check_resource_avail (self):
        """ on error or space not available raise Exception """
        assert self.has_all_attr
        #TODO check memory
        #TODO check disk

        # check ip available
        if 0 == os.system ("ping -c2 -W2 %s >/dev/null" % (self.ip)):
            raise Exception ("ip %s is in use" % (self.ip))
        if os.path.exists (self.config_path):
            raise Exception ("%s already exists" % (self.config_path))
        if os.path.exists (self.img_path):
            raise Exception ("%s already exists" % (self.img_path))
        if os.path.exists (self.swp_path):
            raise Exception ("%s already exists" % (self.swp_path))

    def gen_xenpv_config (self):
        assert self.has_all_attr
        # must called after setup ()

        t = Template ("""
bootloader = "/usr/bin/pygrub"
name = "$name"
vcpus = "$vcpu"
maxmem = "$mem"
memory = "$mem"
vif = [ "vifname=$name,mac=$mac,ip=$ip,bridge=$bridge" ]
disk = [ "file:$img_path,sda1,w","file:$swp_path,sda2,w" ]
on_shutdown = "destroy"
on_poweroff = "destroy"
on_reboot = "restart"
on_crash = "restart"
""" )
        xen_config = t.substitute (name=self.name, vcpu=str(self.vcpu), mem=str(self.mem_m), 
                mac=str(self.mac), img_path=self.img_path, swp_path=self.swp_path,
                bridge=self.xen_bridge)
        return xen_config
       
    def is_running (self):
        raise NotImplementedError ()

    def start (self):
        raise NotImplementedError ()

    def stop (self):
        raise NotImplementedError ()





# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

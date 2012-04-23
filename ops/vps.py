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
import xen
import time


class XenVPS (object):
    """ needs root to run xen command """

    xen_inf = None
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
        if _id < 10:
            self.name = "vps0%d" % (_id) # to be compatible with current practice standard
        else:
            self.name = "vps%d" % str(_id)
        self.img_path = os.path.join (conf.vps_image_dir, self.name + ".img")
        self.swp_path = os.path.join (conf.vps_swap_dir, self.name + ".swp")
        self.config_path = os.path.join (conf.xen_config_dir, self.name)
        self.auto_config_path = os.path.join (conf.xen_auto_dir, self.name)
        self.xen_bridge = conf.xen_bridge
        self.has_all_attr = False
        if xen.XenXM.available ():
            self.xen_inf = xen.XenXM
        elif xen.XenXL.available ():
            self.xen_inf = xen.XenXL
        else:
            raise Exception ("xen-tools is not available")

    def setup (self, os_id, vcpu, mem_m, disk_g, ip, netmask, gateway, root_pw, mac=None, swp_g=None):
        """ on error will raise Exception """
        assert mem_m > 0 and disk_g > 0 and vcpu > 0
        assert ip and netmask is not None and gateway and isinstance (netmask, basestring)
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
        self.mac = mac or vps_common.gen_mac ()
        self.ip = ip
        self.netmask = netmask
        self.gateway = gateway
        self.root_pw = root_pw
        self.template_image, self.os_type, self.os_version = os_image.find_os_image (os_id)

    def check_resource_avail (self):
        """ on error or space not available raise Exception """
        assert self.has_all_attr
        mem_free = self.xen_inf.mem_free ()
        if self.mem_m > mem_free:
            raise Exception ("xen free memory is not enough  (%dM left < %dM)" % (mem_free, self.mem_m))

        #check disks not implemented, too complicate, expect error throw during vps creation
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
                img_path=self.img_path, swp_path=self.swp_path,
                ip=self.ip, bridge=self.xen_bridge, mac=str(self.mac))
        return xen_config
       
    def is_running (self):
        self.xen_inf.is_running (self.name)

    def reboot (self):
        if self.is_running ():
            self.xen_inf.reboot (self.name)
        else:
            self.start ()

    def start (self):
        if self.is_running ():
            return
        self.xen_inf.create (self.config_path)

    def stop (self):
        if not self.is_running ():
            return
        self.xen_inf.shutdown (self.name)

    def wait_until_reachable (self, timeout=20):
        """ wait for the vps to be reachable and return True, or timeout returns False"""
        start_ts = time.time ()
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

#!/usr/bin/env python

import re
import os

import _env
from string import Template
import vps_common
import os_image


import conf
assert conf.XEN_BRIDGE
assert conf.VPS_IMAGE_DIR
assert conf.VPS_SWAP_DIR
assert conf.XEN_CONFIG_DIR
assert conf.XEN_AUTO_DIR
assert conf.MKFS_CMD
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
        self.name = "vps%s" % (str(_id).zfill (2)) # to be compatible with current practice standard
        self.img_path = os.path.join (conf.VPS_IMAGE_DIR, self.name + ".img")
        self.swp_path = os.path.join (conf.VPS_SWAP_DIR, self.name + ".swp")
        self.config_path = os.path.join (conf.XEN_CONFIG_DIR, self.name)
        self.auto_config_path = os.path.join (conf.XEN_AUTO_DIR, self.name)
        self.xen_bridge = conf.XEN_BRIDGE
        self.has_all_attr = False
        self.xen_inf = xen.get_xen_inf ()

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
disk = [ "file:$img_path,xvda1,w","file:$swp_path,xvda2,w" ]
root = "/dev/xvda1"
extra = "fastboot"
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
        return self.xen_inf.is_running (self.name)

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
        """ shutdown a vps, because os needs time to shutdown, will wait for 60 sec until it's really not running"""
        if not self.is_running ():
            return
        self.xen_inf.shutdown (self.name)
        start_ts = time.time ()
        while True:
            time.sleep (1)
            if not self.is_running ():
                return
            now = time.time ()
            if now - start_ts > 60:
                raise Exception ("")


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

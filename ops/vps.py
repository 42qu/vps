#!/usr/bin/env python

import re
import os

import _env
from string import Template
import vps_common
import os_image
from ops.vps_store import VPSStoreImage, VPSStoreLV


import conf
assert conf.XEN_BRIDGE
assert conf.XEN_CONFIG_DIR
assert conf.XEN_AUTO_DIR
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
        if conf.USE_LVM:
            assert conf.VPS_LVM_VGNAME
            self.root_store = VPSStoreLV (conf.VPS_LVM_VGNAME, "%s_root" % self.name)
            self.swap_store = VPSStoreLV (conf.VPS_LVM_VGNAME, "%s_swap" % self.name)
        else:
            self.root_store = VPSStoreImage (conf.VPS_IMAGE_DIR, conf.VPS_TRASH_DIR, "%s.img" % self.name)
            self.swap_store = VPSStoreImage (conf.VPS_SWAP_DIR, conf.VPS_TRASH_DIR, "%s.swp" % self.name)

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

        t = Template ("""
bootloader = "/usr/bin/pygrub"
name = "$name"
vcpus = "$vcpu"
maxmem = "$mem"
memory = "$mem"
vif = [ "vifname=$name,mac=$mac,ip=$ip,bridge=$bridge" ]
disk = [ "$root_path,xvda1,w","$swap_path,xvda2,w" ]
root = "/dev/xvda1"
extra = "fastboot independent_wallclock=1"
on_shutdown = "destroy"
on_poweroff = "destroy"
on_reboot = "restart"
on_crash = "restart"
""" )
        xen_config = t.substitute (name=self.name, vcpu=str(self.vcpu), mem=str(self.mem_m), 
                root_path=self.root_store.xen_path, swap_path=self.swap_store.xen_path,
                ip=self.ip, bridge=self.xen_bridge, mac=str(self.mac))
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

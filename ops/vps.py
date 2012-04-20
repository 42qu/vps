#!/usr/bin/env python

import re
import os

import config
from string import Template
import vps.vps_common as vps_common
from fping import ping
assert config.xen_bridge
assert config.vps_image_dir
assert config.vps_swap_dir
assert config.xen_config_dir
assert config.xen_auto_dir
assert config.mkfs_cmd



class XenVPS (object):

    mem_m = None
    disk_g = None
    mac = None
    ip = None
    netmask = None
    gateway = None

    def __init__ (self, _id):
        self.name = "vps%s" % str(_id)
        self.img_path = os.path.join (config.vps_image_dir, self.name + ".img")
        self.swp_path = os.path.join (config.vps_swap_dir, self.name + ".swp")
        self.config_path = os.path.join (config.xen_config_dir, self.name)
        self.auto_config_path = os.path.join (config.xen_auto_dir, self.name)
        self.has_all_attr = False

    def setup (self, os_id, mem_m, disk_g, ip, netmask, gateway, mac=None, swap_g=None):
        #TODO os_id
        assert mem_m > 0 and disk_g > 0
        assert ip and netmask is not None and gateway
        self.has_all_attr = True
        self.mem_m = mem_m
        self.disk_g = disk_g
        if swap_g:
            self.swap_g = swap_g
        else:
            if self.mem_m >= 2000:
                self.swap_g = 2
            else:
                self.swap_g = 1
        self.mac = mac and vps_common.gen_mac ()
        self.ip = ip
        self.netmask = netmask
        self.gateway = gateway

    def check_resource_avail (self):
        """ on error or space not available raise Exception """
        assert self.has_all_attr
        #TODO
        # check memory
        #TODO
        # check disk
        #TODO
        # check ip available
        if 0 == os.system ("ping -c1 -W2 %s >/dev/null" % (self.ip)):
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
        xen_config = t.substitue (name=self.name, vcpu=str(vcpu), mem=str(self.mem_m), 
                mac=str(self.mac), img_path=self.img_path, swp_path=self.swp_path,
                bridge=config.xen_bridge)
        return xen_config
       
    def is_running (self):
        raise NotImplemented ()

    def start (self):
        raise NotImplemented ()

    def stop (self):
        raise NotImplemented ()

class VPSOps (object):

    def __init__ (self, logger):
        self.logger = logger

    def create_vps (self, vps):

        assert isinstance (vps, VPS, template_os):
        assert vps.has_all_attr
        try:
            vps.check_resource_avail ()

            self.logger.info ("begin to create image for vps %s" % (vps.name))
            vps_common.create_raw_image (vps.img_path, vps.disk_g, config.mkfs_cmd)
            self.logger.info ("image %s created" % (vps.img_path))
            vps_common.create_raw_image (vps.swp_path, vps.swap_g, "mkswap")
            self.logger.info ("swap image %s created" % (vps.swp_path))
            vps_mountpoint = vps_common.mount_loop_tmp (vps.img_path)
            self.logger.info ("mounted vps image %s" % (vps.img_path))
            try:
                if re.match (r'.*\.img$', template_os):
                    vps_common.sync_img (vps_mountpoint, template_os)
                else:
                    vps_common.unpack_tarball (vps_mountpoint, template_os)
                self.logger.info ("syned vps os to %s" % (vps.img_path))
                # TODO init os according to os type
            finally:
                vps_common.umount_tmp (vps_mountpoint)
            xen_config = vps.gen_xenpv_config ()
            f = open (vps.config_path, 'w')
            try:
                f.write (xen_config)
            finally:
                f.close ()
            self.logger.info ("%s created" % (vps.config_path))
            #TODO make link to xen auto 
        except Exception, e:
            self.logger.exception (e)

    def delete_vps (self, vps):
        raise NotImplemented ()
        


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

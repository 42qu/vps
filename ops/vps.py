#!/usr/bin/env python

import config

class XenVPS (object):

    def __init__ (self, _id):
        self.name = "vps%s" % str(_id)
        self.img_path = os.path.join (config.vps_image_dir, self.name + ".img")
        self.swp_path = os.path.join (config.vps_swap_dir, self.name + ".swp")
        self.config_path = os.path.join (config.xen_config_dir, self.name)
        self.auto_config_path = os.path.join (config.xen_auto_dir, self.name)

    def check_space_avail (self):
        #TODO
        return True

    def is_running (self):
        raise NotImplemented ()

    def start (self):
        raise NotImplemented ()

    def stop (self):
        raise NotImplemented ()



class VPSOPS (object):

    def __init__ (self):
        pass

    @staticmethod
    def create_vps (_id, vcpu, mem_m, disk_g, ip, netmask, gateway, root):
        raise NotImplemented ()
    
    @staticmethod
    def create_xen_config (name, vcpu, mem_m, img_path, swp_path):
        raise NotImplemented ()

    @staticmethod
    def sync_img (vpsmountpoint, template_img_path):
        raise NotImplemented ()

    @staticmethod
    def unpack_img (vpsmountpoint, template_img_path):
        raise NotImplemented ()



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

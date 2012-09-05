#!/usr/bin/env python

import ops._env
import conf
assert conf.XEN_BRIDGE
assert conf.XEN_INTERNAL_BRIDGE

class VPSNet (object):
    
    ifname = None
    bridge = None
    ip_dict = None
    mac = None

    def __init__ (self, ifname, ip_dict, bridge, mac):
        # ip_dict: ip=>netmask
        self.ifname = ifname
        self.bridge = bridge
        self.ip_dict = ip_dict
        self.mac = mac

    @classmethod
    def from_meta (cls, data):
        _class = data['__class__']
        if _class == VPSNetExt.__name__:
            if data.has_key ("ip"):
                return VPSNetExt (data['ifname'], {data['ip']: data['netmask']}, data['mac'])
            else:
                return VPSNetExt (data['ifname'], data['ip_dict'], data['mac'])
        if _class == VPSNetInt.__name__:
            if data.has_key ("ip"):
                return VPSNetInt (data['ifname'], {data['ip'], data['netmask']}, data['mac'])
            else:
                return VPSNetInt (data['ifname'], data['ip_dict'], data['mac'])

        raise TypeError (_class)

    def to_meta (self):
        data = {}
        data['__class__'] = self.__class__.__name__
        data['ifname'] = self.ifname
        data['ip_dict'] = self.ip_dict
        data['mac'] = self.mac
        return data

    def clone (self):
        return self.__class__ (self.ifname, self.ip_dict.copy (), self.mac)


class VPSNetExt (VPSNet):

    def __init__ (self, ifname, ip_dict, mac):
        VPSNet.__init__ (self, ifname, ip_dict, conf.XEN_BRIDGE, mac)


class VPSNetInt (VPSNet):

    def __init__ (self, ifname, ip_dict, mac):
        VPSNet.__init__ (self, ifname, ip_dict, conf.XEN_INTERNAL_BRIDGE, mac)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

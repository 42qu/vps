#!/usr/bin/env python

import ops._env
import conf
assert conf.XEN_BRIDGE
assert conf.XEN_INTERNAL_BRIDGE

class VPSNet (object):
    
    ifname = None
    bridge = None
    ip = None
    netmask = None
    mac = None

    def __init__ (self, ifname, ip, netmask, bridge, mac):
        self.ifname = ifname
        self.bridge = bridge
        self.ip = ip
        self.netmask = netmask
        self.mac = mac

    @classmethod
    def from_meta (cls, data):
        _class = data['__class__']
        if _class == VPSNetExt.__name__:
            return VPSNetExt (data['ifname'], data['ip'], data['netmask'], data['mac'])
        if _class == VPSNetInt.__name__:
            return VPSNetInt (data['ifname'], data['ip'], data['netmask'], data['mac'])
        raise TypeError (_class)

    def to_meta (self):
        data = {}
        data['__class__'] = self.__class__.__name__
        data['ifname'] = self.ifname
        data['ip'] = self.ip
        data['netmask'] = self.netmask
        data['mac'] = self.mac
        return data

    def clone (cls, other):
        return cls (other.ifname, other.ip, other.netmask, other.mac)
    clone = classmethod (clone)


class VPSNetExt (VPSNet):

    def __init__ (self, ifname, ip, netmask, mac):
        VPSNet.__init__ (self, ifname, ip, netmask, conf.XEN_BRIDGE, mac)


class VPSNetInt (VPSNet):

    def __init__ (self, ifname, ip, netmask, mac):
        VPSNet.__init__ (self, ifname, ip, netmask, conf.XEN_INTERNAL_BRIDGE, mac)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

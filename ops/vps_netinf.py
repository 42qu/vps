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
    bandwidth = None

    def __init__ (self, ifname, ip_dict, bridge, mac, bandwidth=0):
        # ip_dict: ip=>netmask
        self.ifname = ifname
        self.bridge = bridge
        self.ip_dict = ip_dict
        self.mac = mac
        self.bandwidth = float(bandwidth)

    @classmethod
    def from_meta (cls, data):
        _class = data['__class__']
        self = None
        if _class == VPSNetExt.__name__:
            if data.has_key ("ip"):
                self = VPSNetExt (data['ifname'], {data['ip']: data['netmask']}, data['mac'], data.get ('bandwidth'))
            else:
                self = VPSNetExt (data['ifname'], data['ip_dict'], data['mac'], data.get ('bandwidth'))
        if _class == VPSNetInt.__name__:
            if data.has_key ("ip"):
                self = VPSNetInt (data['ifname'], {data['ip']: data['netmask']}, data['mac'], data.get ('bandwidth'))
            else:
                self = VPSNetInt (data['ifname'], data['ip_dict'], data['mac'], data.get ('bandwidth'))
        if self:
            return self
        raise TypeError (_class)

    def to_meta (self):
        data = {}
        data['__class__'] = self.__class__.__name__
        data['ifname'] = self.ifname
        data['ip_dict'] = self.ip_dict
        data['mac'] = self.mac
        data['bandwidth'] = self.bandwidth
        return data

    def clone (self):
        data = self.__class__ (self.ifname, self.ip_dict.copy (), self.mac, self.bandwidth)
        return data

class VPSNetExt (VPSNet):

    def __init__ (self, ifname, ip_dict, mac, bandwidth=0):
        VPSNet.__init__ (self, ifname, ip_dict, conf.XEN_BRIDGE, mac, bandwidth=bandwidth)


class VPSNetInt (VPSNet):

    def __init__ (self, ifname, ip_dict, mac, bandwidth=0):
        VPSNet.__init__ (self, ifname, ip_dict, conf.XEN_INTERNAL_BRIDGE, mac, bandwidth=bandwidth)



# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

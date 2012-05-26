#!/usr/bin/env python

class VPSNetInf (object):
    
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
        return cls (data['ifname'],
                data['ip'],
                data['netmask'],
                data['bridge'],
                data['mac'])

    def to_meta (self):
        data = {}
        data['ifname'] = self.ifname
        data['bridge'] = self.bridge
        data['ip'] = self.ip
        data['netmask'] = self.netmask
        data['mac'] = self.mac
        return data

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

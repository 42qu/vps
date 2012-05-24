#!/usr/bin/env python

class VPSNetInf (object):
    
    ifname = None
    bridge = None
    ip = None
    netmask = None
    mac = None

    def __init__ (self, name, ip, netmask, bridge, mac):
        self.ifname = name
        self.bridge = bridge
        self.ip = ip
        self.netmask = netmask
        self.mac = mac


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

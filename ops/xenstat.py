#!/usr/bin/env python
# coding:utf-8

import _env
import sys
import os
import time

try:
    import conf
    if 'XEN_PYTHON_LIB' in dir(conf): 
        sys.path.append (conf.XEN_PYTHON_LIB) # for xen 4.1 in ubuntu
except ImportError:
    #sys.path.append ("/usr/lib/xen-default/lib/python/")
    pass

import xen.xm.main
from xen.xm.main import SERVER_XEN_API, serverType, server, serverURI, ServerProxy

import pprint

class XenStat (object):

    """
{'cpu_time': 2548814.654679083,
 'domid': '0',
 'mem': 1023,
 'name': 'Domain-0',
 'seclabel': '',
 'state': 'r-----',
 'up_time': -1.0,
 'vcpus': 1
 'ts': collection_time
 'cpu_avg':  average_cpu_percentage_divided_by_cores
}
"""
    def __init__ (self):
        self.server = ServerProxy(serverURI)
        self.dom_dict = dict () # name -> dominfo
        self.last_ts = None


    def run (self, dom_names): 
        """ can be either id or name """
        for dom_name in dom_names: 
            domain = self.server.xend.domain (dom_name)
            info = xen.xm.main.parse_doms_info (domain)
            info['ts'] = time.time ()
            last_info = self.dom_dict.get (dom_name)
            if last_info:
                info['cpu_avg'] = \
                    float(info['cpu_time'] - last_info['cpu_time']) / float(info['ts'] - last_info['ts']) / int(info['vcpus'])
            else:
                info['cpu_avg'] = 0
            self.dom_dict[dom_name] = info
  
if __name__ == '__main__':
    from ops.ixen import get_xen_inf, XenStore
    xs = XenStat ()

    dom_map = XenStore.domain_name_id_map ()
    dom_names = dom_map.keys ()
    while True:
        xs.run (dom_names)
        time.sleep (1)
#        dom0 = xs.dom_dict.get ('Domain-0')
#        print dom0['cpu_avg']
        infos = xs.dom_dict.values ()
        cpu_total = 0
        for info in infos:
            print info['name'], info['cpu_avg'], info['vcpus']
            cpu_total += info['cpu_avg']
        print cpu_total

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

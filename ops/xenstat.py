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
        self.total_cpu = 0 # should be less than real cpu number


    def run (self, dom_names): 
        """ dom_names: full domain list, can be either id or name """
        total_cpu_time_diff = 0
        total_vcpu = 0
        total_ts_diff = 0
        new_dom_dict = dict ()
        for dom_name in dom_names: 
            domain = self.server.xend.domain (dom_name)
            info = xen.xm.main.parse_doms_info (domain)
            info['ts'] = time.time ()
            last_info = self.dom_dict.get (dom_name)
            if last_info:
                cpu_diff = float(info['cpu_time'] - last_info['cpu_time'])
                ts_diff = float(info['ts'] - last_info['ts'])
                info['cpu_avg'] = cpu_diff / ts_diff / int(info['vcpus']) * 100
                if info['cpu_avg'] > 100:
                    info['cpu_avg'] = 100
                total_vcpu += int(info['vcpus'])
                total_cpu_time_diff += cpu_diff
                total_ts_diff += ts_diff
            else:
                info['cpu_avg'] = 0
            new_dom_dict[dom_name] = info
            if total_ts_diff:
                ts_avg = total_ts_diff / len (dom_names)
                self.total_cpu = total_cpu_time_diff / ts_avg * 100
        self.dom_dict = new_dom_dict
  
if __name__ == '__main__':
    from ops.ixen import get_xen_inf, XenStore
    xs = XenStat ()

    dom_map = XenStore.domain_name_id_map ()
    dom_names = dom_map.keys ()
    while True:
        xs.run (dom_names)
        time.sleep (1)
        dom0 = xs.dom_dict.get ('Domain-0')
        print dom0['cpu_avg']
        print xs.total_cpu

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

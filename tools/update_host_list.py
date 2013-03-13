#!/usr/bin/env python
# coding:utf-8

import os
from os.path import dirname, abspath
import sys
import _env
import conf
from lib.log import Log
import _saas
from vps_mgr import VPSMgr

def update_iplist (host_list):
    dir_path = os.path.join (dirname (dirname (abspath (__file__))), "conf/private")
    if not os.path.exists (dir_path):
        os.makedirs (dir_path)
    conf_path = os.path.join (dir_path, "migrate_svr.py")
    ip_list = []
    for host in host_list:
        if host.ext_ip:
            ip_list.append (host.ext_ip)
        if host.int_ip:
            ip_list.append (host.int_ip)
    conf_content = """#!/usr/bin/python

ALLOWED_IPS = [
%s
]
""" % (",\n".join (map (lambda x: "'%s'" % x, ip_list)))
    f = open (conf_path, "w")
    try:
        f.write (conf_content)
    finally:
        f.close ()


def main ():
    logger = Log ("vps_mgr", config=conf)
    mgr = VPSMgr ()
    host_list = None
    try:
        rpc = mgr.rpc_connect ()
        try:
            host_list = rpc.host_list ()
        finally:
            rpc.close ()
        update_iplist (host_list)
    except Exception, e:
        print e
        logger.exception (e)
        return
       
if __name__ == '__main__':
    main ()
    

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

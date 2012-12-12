#!/usr/bin/env python
# coding:utf-8

import os
from os.path import dirname, abspath
import sys
import _env
import conf
from lib.log import Log
import _saas
import _saas.VPS
from zthrift.client import get_client
from zkit.ip import int2ip 

def update_iplist (host_list):
    conf_path = os.path.join (dirname (dirname (abspath (__file__))), "conf/private/migrate_svr.py")
    ip_list = []
    for host in host_list:
        if host.ext_ip:
            ip_list.append (int2ip(host.ext_ip))
        if host.int_ip:
            ip_list.append (int2ip(host.int_ip))
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
    trans, client = get_client (_saas.VPS)
    host_list = None
    try:
        trans.open ()
        try:
            host_list = client.host_list ()
        finally:
            trans.close ()
        update_iplist (host_list)
    except Exception, e:
        print e
        logger.exception (e)
        return
       
if __name__ == '__main__':
    main ()
    

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

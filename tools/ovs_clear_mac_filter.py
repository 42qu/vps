#!/usr/bin/env python
# coding:utf-8

import os
import sys
import re
import _env
from lib.command import call_cmd
from ops.openvswitch import OVSOps
import getopt

def usage ():
    print "clear filter rules that are not in used, which might be left by not calling the ovs_unset_vif.py script"
    print "usage:"
    print "%s bridge" % (sys.argv[0])

def main ():
    if len (sys.argv) <= 1:
        usage ()
        os._exit (0)

    bridge = sys.argv[1]
    cmd = "ovs-ofctl dump-flows %s" % (bridge)
    out = call_cmd (cmd)
    lines = out.split ("\n")
    regx = re.compile (r'^.*in_port=(\d+).*$')
    ovsops = OVSOps ()
    unused_ofport = dict ()
    using_ofport = dict ()
    print "of_port that are in used:"
    for line in lines:
        om = re.match (regx, line)
        if not om:
            continue
        of_port = int(om.group (1))
        if of_port < 0:
            continue
        if using_ofport.has_key(of_port) or unused_ofport.has_key(of_port):
            continue
        try:
            if_name = ovsops.ovsdb.find_one ('name', 'Interface', {'ofport': of_port}) 
            print if_name, of_port
            using_ofport[of_port] = 1
        except LookupError, e:
            unused_ofport[of_port] = 1
    print "of_port that are not used:"
    print unused_ofport.keys ()
    for of_port in unused_ofport.keys ():
        call_cmd ("ovs-ofctl del-flows %s 'in_port=%s'" % (bridge, of_port))
    print "cleaned"

if __name__ == '__main__':
    main ()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

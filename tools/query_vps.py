#!/usr/bin/env python

import sys
import _env
from vps_mgr import VPSMgr


def usage():
    print "usage: %s vps_id" % (sys.argv[0])


def main():
    if len(sys.argv) <= 1:
        usage()
        return
    vps_id = int(sys.argv[1])
    mgr = VPSMgr()
    rpc = mgr.rpc_connect()
    try:
        vps = rpc.vps(vps_id)
        print mgr.dump_vps_info(vps)
    finally:
        rpc.close()


if __name__ == '__main__':
    main()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

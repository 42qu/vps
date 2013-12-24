#!/usr/bin/env python
# coding:utf-8

import sys
import _env
from vps_mgr import VPSMgr

def send_alarm(msg):
    mgr = VPSMgr()
    rpc = mgr.rpc_connect()
    try:
        rpc.alarm(msg)
    finally:
        rpc.close()


def main():
    if len(sys.argv) <= 1:
        msg = sys.stdin.read()
        if msg:
            send_alarm(msg)
        else:
            print >> sys.stderr, "no input provided"
        return
    msg = " ".join(sys.argv)
    send_alarm(msg)

if __name__ == '__main__':
    main()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

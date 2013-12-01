#!/usr/bin/env python
# coding:utf-8

import nmap


def scan_port_open(ip):
    nm = nmap.PortScanner()
    nm.scan(ip, arguments="")
    nm.scaninfo()
    if ip not in nm.all_hosts():
        return False
    if nm[ip].state() == 'up':
        return True
    return False

if __name__ == '__main__':
    print scan_port_open("113.11.199.171")


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

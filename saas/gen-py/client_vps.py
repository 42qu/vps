#!/usr/bin/env python
#coding:utf-8


from zthrift.client import client

from saas import VPS
from client.vps import handler

def main():
    print 'cliening ...'
    client(VPS, handler)
    print 'done'

if __name__ == "__main__":
    main()

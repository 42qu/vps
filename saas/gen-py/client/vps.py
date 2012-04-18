#!/usr/bin/env python
#coding:utf-8
import _env

from zthrift.client import client

from saas import VPS
from ctrl.vps import handler

def main():
    print 'client runing ...'
    client(VPS, handler)
    print 'done'

if __name__ == "__main__":
    main()


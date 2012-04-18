#!/usr/bin/env python
#coding:utf-8


from zthrift.client import client

from saas import VPS
from client.vps import handler

print 'cliening ...'
client(VPS, handler)
print 'done'


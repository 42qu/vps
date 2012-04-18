#!/usr/bin/env python

from zthrift.server import server

from saas import VPS
from server.vps import Handler

print 'serving ...'
server(VPS, Handler())
print 'done'



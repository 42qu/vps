#!/usr/bin/env python

from zthrift.server import server

from saas import VPS
from client.vps import Handler

print 'serving ...'
server(VPS, Handler)
print 'done'



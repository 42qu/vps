#!/usr/bin/env python
# coding:utf-8

import socket
import struct
import pickle

class CarbonPayload (object):

    def __init__ (self):
        self.data = []

    def append (self, path, timestamp, value):
        self.data.append ((path, (timestamp, value)))

    def serialize (self):
        payload = pickle.dumps (self.data)
        return struct.pack ("!L", len(payload))

    def is_empty (self):
        return not self.data


def send_data (server_addr, payload):
    sock = socket.socket ()
    sock.connect (server_addr)
    try:
        sock.sendall (payload)
    finally:
        sock.close ()


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

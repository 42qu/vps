#!/usr/bin/env python

# plan <frostyplanet@gmail.com>
# 2011-08-03

#
# @file 
# @version $Id: net_io.py,v 1.2 2010/04/01 03:13:37 anning Exp $
# @brief
#


import struct
import socket
import errno


#if suc to send all in buf, return length of buf, otherwise raise socket.error (errno=0) 
def send_all (sock, buf):
    data_len = len (buf)
    while data_len:
        try:
            res = sock.send (buf)
            if (not res):
                raise socket.error (0, "peer closed")
            buf = buf[res:data_len]
            data_len -= res
        except socket.error, e:
            _errno = e[0]
            if _errno not in (errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK):
                raise e
    return data_len

#if suc to recv data of length ="length", return data, otherwise raise socket.error (errno=0)
def recv_all (sock, length):
    buf = ''
    while length:
        try:
            temp = sock.recv(length)
            if temp == "":
                raise socket.error (0, "peer closed")
            length -= len(temp)
            buf += temp
        except socket.error, e:
            _errno = e[0]
            if _errno not in (errno.EINTR, errno.EAGAIN, errno.EWOULDBLOCK):
                raise e
    return buf


class NetHead:

    _STRUCT = '!3I'
    size = struct.calcsize(_STRUCT)
        
    def __init__(self):
        self._id = 0
        self.magic_num = 0xE7342119
        self.body_len = 0

    def pack(self, body_len=0):
        if body_len == 0:
            body_len = self.body_len
        return struct.pack(self._STRUCT, self.magic_num, self._id, body_len)

    def unpack(cls, buf):
        """ on error will raise ValueError """
        self = cls ()
        if len(buf) != cls.size:
            raise ValueError ("invalid head, size expect %d, but got %d" % (cls.size, len(buf)))
        fields = struct.unpack(self._STRUCT, buf)
        if self.magic_num != fields[0]:
            raise ValueError ("invalid head, magic number error")
        self._id = fields[1]
        self.body_len = fields[2]
        return self
    unpack = classmethod (unpack)

    def read_head (cls, sock):
        """ on error or timeout will throw exception """
        head_buf = recv_all (sock, NetHead.size)
        self = cls.unpack (head_buf)
        return self
    read_head = classmethod (read_head)

    def read_data (self, sock):
        """ on error or timeout will throw socket.error """
        if not self.body_len:
            return None
        return recv_all (sock, self.body_len)
    
    def write_msg (self, sock, buf):
        """ possible throw socket.error """
        head_buf = self.pack (len (buf))
        send_all (sock, head_buf)
        return send_all (sock, buf)

# vim: set sw=4 ts=4 et :

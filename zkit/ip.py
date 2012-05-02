#coding:utf-8
import socket
import struct

def ip2int(ip):
    return struct.unpack("!I",socket.inet_aton(ip))[0]

def int2ip(num):
    return socket.inet_ntoa(struct.pack("!I",num))

if __name__ == "__main__":
    print socket.has_ipv6
    print int2ip(ip2int("127.0.123.249"))
    print int2ip(ip2int("201.119.123.249"))


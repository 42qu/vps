#coding:utf-8
import socket
import struct

def ip2int(ip):
    return struct.unpack("!I",socket.inet_aton(ip))[0]

def int2ip(num):
    return socket.inet_ntoa(struct.pack("!I",num))

def address_to_in6 (address):
    try:
        return socket.inet_pton (socket.AF_INET6, address)
    except socket.error:
        in4 = socket.inet_pton (socket.AF_INET, address)
        in6 = struct.pack ("!IIII", 0, 0, 0xffff, struct.unpack("!I", in4)[0])
        return in6
        
        

if __name__ == "__main__":
    print socket.has_ipv6
    print int2ip(ip2int("127.0.123.249"))
    print int2ip(ip2int("201.119.123.249"))
    print socket.inet_ntop (socket.AF_INET6, address_to_in6 ("::ffff:10.10.1.1"))
    print socket.inet_ntop (socket.AF_INET6, address_to_in6 ("10.10.1.1"))

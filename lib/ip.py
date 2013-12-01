# coding:utf-8
import socket
import re
import struct


def ip2int(ip):
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def int2ip(num):
    return socket.inet_ntoa(struct.pack("!I", num))


def address_to_in6(address):
    try:
        return socket.inet_pton(socket.AF_INET6, address)
    except socket.error:
        in4 = socket.inet_pton(socket.AF_INET, address)
        in6 = struct.pack("!IIII", 0, 0, 0xffff, struct.unpack("!I", in4)[0])
        return in6


def is_ipv4(ip):
    if not ip:
        return False
    om = re.match(r'^(\d+)\.(\d+)\.(\d+)\.(\d+)$', ip)
    if om:
        if int(om.group(1)) <= 255 and int(om.group(2)) <= 255 and int(om.group(3)) <= 255 and int(om.group(4)) <= 255:
            return True
    return False


def is_host_ip(ip):
    if not is_ipv4(ip):
        return False
    om = re.match(r'^(\d+)\.(\d+)\.(\d+)\.(\d+)$', ip)
    if om:
        last = int(om.group(4))
        if last > 0 and last < 255:
            return True
    return False


def check_host_ipv4(ip_inner, netmask_int):
    net_int = ip_inner & netmask_int
    net_full_int = net_int + (0xffffffff & (~ netmask_int))
    return ip_inner < net_full_int and ip_inner > net_int


def check_gateway_ipv4(ip_inner, netmask_int, gateway_int):
    net_int = ip_inner & netmask_int
    net_full_int = net_int + (0xffffffff & (~ netmask_int))
    print net_int, gateway_int, net_full_int
    return net_int == gateway_int - 1 or net_full_int == gateway_int + 1

if __name__ == "__main__":
    print socket.has_ipv6
    print ip2int("218.245.3.150")
    print int2ip(ip2int("127.0.123.249"))
    print int2ip(ip2int("201.119.123.249"))
    assert check_host_ipv4(ip2int("10.10.10.2"), ip2int("255.255.255.0"))
    assert check_host_ipv4(ip2int("10.10.10.1"), ip2int("255.255.255.0"))
    assert not check_host_ipv4(ip2int("10.10.10.0"), ip2int("255.255.255.0"))
    assert check_host_ipv4(ip2int("10.10.10.254"), ip2int("255.255.255.0"))
    assert not check_host_ipv4(ip2int("10.10.10.255"), ip2int("255.255.255.0"))
    assert check_gateway_ipv4(
        ip2int('10.10.10.2'), ip2int('255.255.255.0'), ip2int('10.10.10.1'))
    assert not check_gateway_ipv4(
        ip2int('10.10.10.2'), ip2int('255.255.255.0'), ip2int('10.10.2.1'))
    assert check_gateway_ipv4(ip2int('119.254.32.162'),
                              ip2int('255.255.255.240'), ip2int('119.254.32.161'))
    print socket.inet_ntop(socket.AF_INET6, address_to_in6("::ffff:10.10.1.1"))
    print socket.inet_ntop(socket.AF_INET6, address_to_in6("10.10.1.1"))

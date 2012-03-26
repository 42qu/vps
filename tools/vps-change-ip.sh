#!/bin/bash

OS="ubuntu"
#OS="centos"
#OS="gentoo"
#OS="debian"
IMG="ubuntu01.img"
IPADDRESS="119.254.32.175"
GATEWAY="119.254.32.161"
NETMASK="255.255.254.0"

mount -o loop /vps/$IMG /mnt

if [ $OS == "ubuntu" ] || [ $OS == "debian" ]
then
cat >/mnt/etc/network/interfaces <<-__END__
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
address $IPADDRESS
gateway $GATEWAY
netmask $NETMASK
__END__
elif [ $OS == "centos" ] || [ $OS == "fedora" ]
then
cat >/mnt/etc/sysconfig/network-scripts/ifcfg-eth0 <<-__END__
DEVICE=eth0
BOOTPROTO=none
ONBOOT=yes
TYPE=Ethernet
IPADDR=$IPADDRESS
GATEWAY=$GATEWAY
NETMASK=$NETMASK
__END__
elif [ $OS == "gentoo" ]
then
cat >/mnt/etc/conf.d/net <<-__END__
config_eth0="$IPADDRESS netmask $NETMASK"
routes_eth0="default via $GATEWAY"
__END__
fi

umount /mnt

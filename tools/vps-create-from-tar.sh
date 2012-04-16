#!/bin/bash

XENHOME=/vps
XENSWAP=/swp
XENCONF=/etc/xen
XENLOG=/var/log/xen
XENTOOLLOG=/var/log/xen-tools

NAME="vps20"
VCPU="1"
VRAM="2048"
SWAP="1024"
DISK="5G"

OS="ubuntu"
#OS="centos5"
#OS="centos6"
#OS="gentoo"
#OS="debian"
#IPADDRESS="119.254.32.170"
#GATEWAY="119.254.32.161"
IPADDRESS="119.254.35.107"
GATEWAY="119.254.35.97"
NETMASK="255.255.254.0"

genXenMac() {
    S="00:16:3e:"
    E=`(date; cat /proc/interrupts) | md5sum | sed -r 's/^(.{6}).*$/\1/; s/([0-9a-f]{2})/\1:/g; s/:$//;'`
    echo $S$E
}

cat >$XENCONF/$NAME <<-__END__
bootloader = "/usr/bin/pygrub"
vcpus = "$VCPU"
maxmem = "$VRAM"
memory = "$VRAM"
name = "$NAME"
vif = [ "vifname=$NAME,mac=`genXenMac`,ip=$IPADDRESS,bridge=xenbr0" ]
disk = [ "file:$XENHOME/$NAME.img,sda1,w","file:$XENSWAP/$NAME.swp,sda2,w" ]
root = "/dev/sda1"
extra = "fastboot"
on_shutdown = "destroy"
on_poweroff = "destroy"
on_reboot = "restart"
on_crash = "restart"
__END__

#cp $XENHOME/$OS"00".img $XENHOME/$NAME.img
dd if=/dev/zero of=$XENHOME/$NAME.img bs=1 count=1 seek=$DISK
mkfs.ext3 $XENHOME/$NAME.img
mount -o loop $XENHOME/$NAME.img /mnt
tar -zxSf $XENHOME/$OS.tar.gz -C /mnt/
umount /mnt

dd if=/dev/zero of=$XENSWAP/$NAME.swp bs=1024 count=`expr $SWAP \* 1024`
mkswap $XENSWAP/$NAME.swp

mount -o loop $XENHOME/$NAME.img /mnt

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
elif [ $OS == "centos6" ]
then
cat >/mnt/etc/sysconfig/network-scripts/ifcfg-eth0 <<-__END__
DEVICE="eth0"
BOOTPROTO="static"
DNS1="8.8.8.8"
GATEWAY="$GATEWAY"
IPADDR="$IPADDRESS"
IPV6INIT="no"
MTU="1500"
NETMASK="$NETMASK"
NM_CONTROLLED="yes"
ONBOOT="yes"
TYPE="Ethernet"
__END__
elif [ $OS == "gentoo" ]
then
cat >/mnt/etc/conf.d/net <<-__END__
config_eth0="$IPADDRESS netmask $NETMASK"
routes_eth0="default via $GATEWAY"
__END__
fi

umount /mnt

xm create $NAME
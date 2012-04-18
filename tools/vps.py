#!/usr/bin/python
# -*- coding: UTF-8 -*-

from fabric.api import *

def us():
        env.user = 'root'
        env.hosts = [
                '72.20.52.221',
        ]
        env.password = 'password'

def cn():
        env.user = 'root'
        env.hosts = [
                '119.254.32.166',
#                '119.254.32.111',
        ]
        env.password = 'password'

def list():
        run('xm list')

def create(name, vcpu, vram, swap, disk, os, address, gateway, netmask):
#       name = "vps21"
#       vcpu = "1"
#       vram = "2048"
#       swap = "1024"
#       disk = "50G"
#       os   = "ubuntu"
#       address = "119.254.35.108"
#       gateway = "119.254.35.97"
#       netmask = "255.255.254.0"

        cmd = '/home/lyee/vps/tools/vps.sh ' + name + ' ' + vcpu + ' ' + vram + ' ' + swap + ' ' + disk + ' ' + os + ' ' + address + ' ' + gateway + ' ' + netmask
        print cmd

        run(cmd)

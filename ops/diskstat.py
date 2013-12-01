#!/usr/bin/env python
# coding:utf-8

import vps_common
import os


class DiskStat(object):
    read_ops_count = None
    read_byte_count = None
    write_ops_count = None
    write_byte_count = None
    io_time_weighted = None
    io_time = None

    def __init__(self, dev):
        self.dev = dev


def read_stat(dev_list):
    lines = None
    result_dict = dict()
    dev_name_r = dict()
    for dev in dev_list:
        _dev = os.path.basename(os.path.realpath(dev))
        dev_name_r[_dev] = dev
    f = open("/proc/diskstats")
    try:
        lines = f.readlines()
    finally:
        f.close()
    for line in lines:
        l = line.strip("\n")
        arr = l.split()
        dev = arr[2]
#        print dev
        if not dev_name_r.has_key(dev):
            continue
        sector_size = vps_common.get_sector_size(dev)
        stat = DiskStat(dev_name_r[dev])
        stat.read_ops_count = int(arr[3])
        stat.read_byte_count = int(arr[5]) * sector_size
#        read_time = int(arr[6])
        stat.write_ops_count = int(arr[7])
        stat.write_byte_count = int(arr[9]) * sector_size
#        write_time = int(arr[10])
        stat.io_time = int(arr[12])
        stat.io_time_weighted = int(arr[13])
        result_dict[stat.dev] = stat
    return result_dict


def cal_stat(s, last_s, t_elapse):
    read_ops = (s.read_ops_count - last_s.read_ops_count) / t_elapse
    read_byte = (s.read_byte_count - last_s.read_byte_count) / t_elapse
    write_ops = (s.write_ops_count - last_s.write_ops_count) / t_elapse
    write_byte = (s.write_byte_count - last_s.write_byte_count) / t_elapse
    io_util = (s.io_time - last_s.io_time) / t_elapse / 1000.0 * 100
    if io_util > 100:
        io_util = 100
    return read_ops, read_byte, write_ops, write_byte, io_util


if __name__ == '__main__':
    import pprint
    import time
    last_result = None
    while True:
        result = read_stat(["sda"])
        time.sleep(1)
        if last_result:
            print cal_stat(result['sda'], last_result['sda'], 1)
        last_result = result

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

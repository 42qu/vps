#!/usr/bin/env python

def read_proc ():
    """ return a dict
    { if: (rx_bytes, tx_bytes) }
    """
    result = dict ()
    lines = None 
    f = open ("/proc/net/dev", "r")
    try:
        lines = f.readlines ()
    finally:
        f.close ()
    lines = lines[2:]
    for line in lines:
        arr = line.split (":") 
        assert len(arr) == 2
        if_name = arr[0].strip ()
        arr = arr[1].split ()
        assert len(arr) == 16
        rx = int(arr[0])
        tx = int(arr[8])
        result[if_name] = (rx, tx)
    return result


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :

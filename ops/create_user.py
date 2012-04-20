#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess

""" 
 run with file 'pw' in the same directory.
 each line of 'pw' formats like: 
   user:passwd
or
   user:passwd:group1,group2
"""

main = """
    data_file = os.path.join (os.path.dirname (__file__), "user_data")
    # user data split in lines, in "user:passwd:group1,group2" format
    if not os.path.isfile (data_file):
        print >> sys.stderr, "%s not found" % (data_file)
        return
    f = open (data_file, "r")
    lines = []
    try:
        lines = f.readlines ()
    finally:
        f.close ()
    user_list = []
    for line in lines:
        line = line.rstrip ("\n")
        arr = line.split (":")
        if len (arr) < 2:
            continue
        user = arr[0]
        passwd = arr[1]
        if os.system ("groups %s >/dev/null" % (user)) != 0:
            if len (arr) == 3:
                os.system ("useradd -m -G %s %s" % (arr[2], user))
            else:
                os.system ("useradd -m %s -g users" % (user))

        user_list.append ((user, passwd))
    p = subprocess.Popen (["chpasswd"], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for item in user_list:
        p.stdin.write ("%s:%s\n" % (item[0], item[1]))
    p.stdin.close ()
    if p.wait () != 0:
        for line in p.stderr.readlines ():
            print >> sys.stderr, line
    
"""

if "__main__" == __name__:
    eval (main)


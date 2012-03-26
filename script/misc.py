#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import random
import string
import os

def _call_cmd (cmd):
    res = os.system (cmd)
    if res != 0:
        raise Exception ("%s exit with %d" % (cmd, res))

def gen_password (length=10):
    return "".join ([ random.choice(string.hexdigits) for i in xrange (0, length) ])


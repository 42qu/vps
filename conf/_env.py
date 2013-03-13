#coding:utf-8
from os.path import dirname, normpath, abspath, join
PREFIX = dirname(abspath(__file__))

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append(PREFIX)

path_dict = dict ()
for path in sys.path:
    path_dict[path] = None
sys.path = path_dict.keys ()

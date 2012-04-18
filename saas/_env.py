#coding:utf-8

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import sys
from os.path import dirname, normpath, abspath, join
sys.path.append(normpath(join(dirname(abspath(__file__)),"gen-py")))



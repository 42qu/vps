#coding:utf-8
from os.path import dirname, normpath, abspath, join
PREFIX = dirname(dirname(abspath(__file__)))

import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.append(PREFIX)

from zkit.algorithm.unique import unique
sys.path = unique(sys.path)

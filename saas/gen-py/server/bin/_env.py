#coding:utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf-8')



from getpass import getuser

sys.path.append("/home/%s/zpage"%getuser())

from os.path import dirname, normpath, abspath, join
PREFIX = dirname(dirname(dirname(abspath(__file__))))
sys.path.append(PREFIX)

from zkit.algorithm.unique import unique
sys.path = unique(sys.path)

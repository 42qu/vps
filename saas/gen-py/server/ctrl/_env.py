import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from os.path import dirname, abspath, exists
from getpass import getuser

sys.path.append("/home/%s/zpage"%getuser())
sys.path.append(dirname(dirname(dirname(abspath(__file__)))))
from zkit.algorithm.unique import unique
sys.path = unique(sys.path)

import config
config.DISABLE_LOCAL_CACHED = True

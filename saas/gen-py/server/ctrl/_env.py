import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from os.path import dirname, abspath, exists
from getpass import getuser

sys.path.append("/home/%s/zpage"%getuser())
sys.path.append(dirname(dirname(dirname(abspath(__file__)))))

import config
config.DISABLE_LOCAL_CACHED = True

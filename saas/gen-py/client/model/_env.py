import sys
reload(sys)
sys.setdefaultencoding('utf-8')
from os.path import dirname, abspath, exists

sys.path.append(dirname(dirname(dirname(abspath(__file__)))))
from zkit.algorithm.unique import unique
sys.path = unique(sys.path)


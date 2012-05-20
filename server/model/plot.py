#coding:utf-8
import _env
from zsql.db import connection
connection.THREAD_SAFE = False
from zsql.db import sqlstore
from config import MYSQL_PORT, MYSQL_HOST, MYSQL_MAIN, MYSQL_USER, MYSQL_PASSWD
from _mysql_exceptions import ProgrammingError
from time import time

SQLSTORE = sqlstore.SqlStore(MYSQL_HOST , MYSQL_PORT, MYSQL_USER, MYSQL_PASSWD, db='zplot', charset='utf8')

PLOT_CID_VPS_NETFLOW_RX_1MIN ,\
PLOT_CID_VPS_NETFLOW_TX_1MIN,\
PLOT_CID_VPS_NETFLOW_1MIN ,\
PLOT_CID_VPS_NETFLOW_1MIN_HOST,\
PLOT_CID_VPS_NETFLOW_RX_1DAY ,\
PLOT_CID_VPS_NETFLOW_TX_1DAY,\
PLOT_CID_VPS_NETFLOW_1DAY ,\
PLOT_CID_VPS_NETFLOW_1DAY_HOST = range(1, 9)

CID2NAME = {
    PLOT_CID_VPS_NETFLOW_RX_1MIN   : 'VPS . 带宽图 . 流入 . 虚拟机. 每分钟',
    PLOT_CID_VPS_NETFLOW_TX_1MIN   : 'VPS . 带宽图 . 流出 . 虚拟机 . 每分钟',
    PLOT_CID_VPS_NETFLOW_1MIN      : 'VPS . 带宽图 . 虚拟机 . 每分钟',
    PLOT_CID_VPS_NETFLOW_1MIN_HOST : 'VPS . 带宽图 . 物理机 . 每分钟',

    PLOT_CID_VPS_NETFLOW_RX_1DAY   : 'VPS . 流量图 . 流入 . 虚拟机 . 每天',
    PLOT_CID_VPS_NETFLOW_TX_1DAY   : 'VPS . 流量图 . 流出 . 虚拟机 . 每天',
    PLOT_CID_VPS_NETFLOW_1DAY      : 'VPS . 流量图 . 虚拟机 . 每天',
    PLOT_CID_VPS_NETFLOW_1DAY_HOST : 'VPS . 流量图 . 物理机 . 每天',
}


def plot_point(cid, rid, limit, base=None):
    cursor = SQLSTORE.cursor()
    cursor.execute('select value from `%s` where rid=%%s order by id desc limit %s'%(int(cid), int(limit)), rid)
    if base is None:
        r = [i for i, in cursor.fetchall()]
    else:
        r = [i/base for i, in cursor.fetchall()]
    return r

def _plot( cid, rid, value, timestamp):
    cursor = SQLSTORE.cursor()
    cursor.execute('INSERT DELAYED INTO `%s` (rid, value, time) VALUES (%%s, %%s, %%s)'%int(cid), (rid, value, timestamp))

def plot( cid, rid, value):
    timestamp = int(time())
    try:
        _plot( cid, rid, value, timestamp)
    except ProgrammingError, e:
        if e.args and e.args[0] == 1146:
            cursor = SQLSTORE.cursor()
            cursor.execute(
"""
CREATE TABLE  `zplot`.`%s` (
`id` int(10) unsigned NOT NULL auto_increment,
`value` bigint unsigned NOT NULL,
`time` bigint unsigned NOT NULL,
`rid` int(10) unsigned NOT NULL,
PRIMARY KEY  (`id`),
KEY `index_2` (`rid`)
) ENGINE=MYISAM DEFAULT CHARSET=utf8;
"""%cid

            )
            _plot(cid, rid, value, timestamp)
        else:
            raise e

if __name__ == '__main__':
    pass
    print plot_point(PLOT_CID_VPS_NETFLOW_1MIN_HOST, 3, 1440, 1024*1024/8)
    print plot_point(PLOT_CID_VPS_NETFLOW_1MIN_HOST, 2, 1440, 1024*1024/8)
    print plot_point(PLOT_CID_VPS_NETFLOW_1MIN, 95, 1440, 1024*1024/8)
    print plot_point(PLOT_CID_VPS_NETFLOW_1MIN, 14, 1440, 1024*1024/8)

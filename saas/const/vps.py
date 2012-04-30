# -*- coding: utf-8 -*-

VPS_OS_DICT = {
    2: 'CentOS-6.2',
    1: 'CentOS-5.8',
    10003: 'Ubuntu-12.04',
    10002: 'Ubuntu-11.10',
    10001: 'Ubuntu-10.04',
    20001: 'Debian-6.0',
    30001: 'Arch',
    50001: 'Gentoo',
    60001: 'Fedora',
    70001: 'OpenSUSE',
    80001: 'Slackware',
    90001: 'Scientific',
   100001: 'NetBSD',
   110001: "FreeBSD",
}

VPS_STATE_RM = 0
VPS_STATE_PAY = 10
VPS_STATE_RUN = 15
VPS_STATE_CLOSE = 20

VPS_STATE2CN = {
    VPS_STATE_RM  : '已删除' ,
    VPS_STATE_RUN : '运行中' ,
    VPS_STATE_CLOSE : '被关闭' ,
    VPS_STATE_PAY : '未开通' ,
}

VPS_COUNTRY_DICT = {
    1: ('中国',
        {
            1   : '北京 双线BGP',
        },
       ),
    2: ('美国',
        {
            1001: 'Los Angeles 洛杉矶机房',
            1002: 'Las Vegas 拉斯维加斯1号机房',
            1003: 'Las Vegas 拉斯维加斯2号机房',
            1004: 'Orange County 加州 OC 机房',
            1005: 'San Jose',
        },
   ),
}

VPS_DATA_CENTER_CN = dict()
for __i in VPS_COUNTRY_DICT.itervalues():
    VPS_DATA_CENTER_CN.update(__i[1])



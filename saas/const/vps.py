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

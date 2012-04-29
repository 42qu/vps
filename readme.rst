私有文件
==============================

有一些私有的密钥文件 , 放在 https://bitbucket.org/zsp042/private/ 上 (因为github的私有仓库要收费)

首先邮件 zsp007@gmail.com , 索取仓库访问权限

编辑 ~/.ssh/config 文件 , 其中 id_rsa 为你在 bitbucket.org 上关联的 ssh keys ::

    Host bitbucket.org
     User 你的用户名 
     IdentityFile ~/.ssh/id_rsa

然后 在 saas目录 (也就是readme.txt所在的目录下) 执行::

    git clone git@bitbucket.org:zsp042/private.git


push 貌似要用 ::

    git push origin master


如熟悉Hg , 但是不太熟悉git的人 ,  可以配合hg-git插件, 用以下方式clone ::

    hg clone git+ssh://git@bitbucket.org:zsp042/private.git

程序结构
=============================================

接口的定义文件 : saas.thrift

启动线上服务器 (应该用 daemontools http://cr.yp.to/daemontools.html 之类的工具保证进程死掉以后自动重开) ::

    server/bin/vps.py 

启动开发服务器(当有文件改动的时候会自动重启) ::

    server/bin/vps.dev.py     

配置 :  conf/

主程序 :    server/ctrl/vps.py

VPS逻辑 :  ops/

脚本 : tools/


配置文件
============================================

为了开发调试的方便，每台机器可以有自己的配置选项

参见 :

    * conf/default.py  默认配置

    * conf/host/e1.py  其中 e1.py 的 e1 为当前机器的名称


模块依赖
=====================================

client :

    * paramiko
    
    * thrift (如果不需要生成代码，可以安装 http://pypi.python.org/pypi/thrift/1.0)


相关链接
====================================

Thrift教程 http://book.42qu.com/thrift.html

端口登记 http://book.42qu.com/42qu/saas.html 

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


相关链接
====================================

Thrift教程 http://book.42qu.com/thrift.html

端口登记 http://book.42qu.com/42qu/saas.html 

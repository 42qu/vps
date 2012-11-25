#!/bin/sh

if [ -z $1 ]; then
	echo "usage user@host"
	exit 1
fi

ssh $1 "cd /data/vps/code && sudo git pull && sudo /etc/init.d/vpsmgr restart"

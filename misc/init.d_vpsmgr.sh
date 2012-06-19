#!/bin/bash
#
# vpsmgr      This shell script takes care of starting and stopping
#                 vps manage daemon.
#
# chkconfig: - 13 87
# description: vpsmgr.
# probe: true

. /etc/rc.d/init.d/functions

BASE_PATH="/data/vps/code"
cmd="./vps_mgr.py"

function start() {
    cd $BASE_PATH && $cmd start
}

function stop() {
    cd $BASE_PATH && $cmd stop
}

function status() {
    cd $BASE_PATH && $cmd status
}

function restart() {
    stop
    start
}

case "$1" in
start)
        start
        ;;
stop)
        stop
        ;;
restart)
        restart
        ;;
status)
        status
        ;;
*)
        echo $"Usage: $0 {start|stop|status|restart}"
        RETVAL=2
esac

exit $RETVAL



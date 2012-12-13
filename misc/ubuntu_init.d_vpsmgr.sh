#!/bin/bash
#

### BEGIN INIT INFO
# Provides:             vpsmgr
# Required-Start:       $xend
# Required-Stop:        $xend
# Default-Start:        2 3 4 5
# Default-Stop:        0 1 6 
# Short-Description:   vpsmgr 
### END INIT INFO

set -e


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



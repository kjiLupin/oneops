#!/bin/bash

. /etc/init.d/functions
export PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/opt/node/bin

PROC_NAME="wd-oneops"
lockfile=/var/lock/subsys/${PROC_NAME}

function stop_all() {
	echo -n $"Stopping ${PROC_NAME} service:"
	ps aux |grep -E 'daphne|gunicorn|celery' |grep 'wdoneops' |grep -v grep | awk '{print $2}' | xargs kill -9 &> /dev/null
	sleep 1
	if ps aux |grep -v grep |grep 'python' |grep 'wdoneops' ;then
	    echo_failure
	    echo
	else
	    echo_success
	    echo
	    rm -f "$lockfile"
	fi
}

function stop_wdoneops() {
	echo -n $"Stopping ${PROC_NAME} service:"
	ps aux |grep -E 'daphne|gunicorn' |grep 'wdoneops' |grep -v grep | awk '{print $2}' | xargs kill -9 &> /dev/null
	sleep 1
	if ps aux |grep -v grep |grep -E 'daphne|gunicorn' |grep 'wdoneops' ;then
	    echo_failure
	    echo
	else
	    echo_success
	    echo
	    rm -f "$lockfile"
	fi
}

function stop_celery_worker() {
	echo -n $"Stopping celery worker:"
	ps aux |grep 'celery worker' |grep 'wdoneops' |grep -v grep | awk '{print $2}' | xargs kill -9 &> /dev/null
	sleep 1
	if ps aux |grep -v grep |grep 'celery worker' |grep 'wdoneops' ;then
	    echo_failure
	    echo
	else
	    echo_success
	    echo
	fi
}

function stop_celery_beat() {
	echo -n $"Stopping celery beat:"
	ps aux |grep 'celery beat' |grep 'wdoneops' |grep -v grep | awk '{print $2}' | xargs kill -9 &> /dev/null
	sleep 1
	if ps aux |grep -v grep |grep 'celery beat' |grep 'wdoneops' ;then
	    echo_failure
	    echo
	else
	    echo_success
	    echo
	fi
}

# See how we were called.
case "$1" in
  all)
        stop_all
        ;;
  wdoneops)
        stop_wdoneops
        ;;
  celery_worker)
        stop_celery_worker
        ;;
  celery_beat)
        stop_celery_beat
        ;;
  *)
        echo $"Usage: $0 {all|wdoneops|celery_worker|celery_beat}"
        exit 2
esac
#!/bin/bash
# wd-oneops      Startup script for the wd-oneops Server
#
# chkconfig: - 85 12
# description: Open source detecting system
# Date: 2015-04-12


. /etc/init.d/functions
export PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/opt/node/bin

base_dir=$(dirname $0)
PROC_NAME="wd-oneops"

lockfile=/var/lock/subsys/${PROC_NAME}

start() {

    if [ -f $lockfile ]; then
      echo "wd-oneops  is running..."
    else
      echo "Starting ${PROC_NAME} service."

      cd ${base_dir}
      source /usr/local/python36/bin/activate
      # gunicorn wdoneops.wsgi:application -c gunicorn.conf.py >> logs/gunicorn.error.log 2>&1
      nohup daphne -b 127.0.0.1 -p 8000 wdoneops.asgi:application --access-log logs/access.log 2>&1 &
      sleep 2
      echo -n "--starting wd-oneops:"
      if `netstat -lnpt|grep -qiE ':8000.*python'` ; then
         echo_success
         echo
      else
         echo_failure
         echo
         exit 1
      fi
      
      # celery 不允许创建子进程
      PYTHONOPTIMIZE=1 celery worker -A wdoneops -c 2 -l info >> logs/celery.log 2>&1 &
      sleep 2
      echo -n "--starting celery:"
      if `ps -ef | grep -v grep | grep -iqE 'celery\sworker\s-A'`; then
       echo_success
       echo
      else
       echo_failure
       echo
       exit 1
      fi

      celery beat -A wdoneops -l info -S django >> logs/celery_beat.log 2>&1 &
      sleep 2
      echo -n "--starting celery beat:"
      if `ps -ef | grep -v grep | grep -iqE 'celery\sbeat\s-A'`; then
       echo_success
       echo
      else
       echo_failure
       echo
       exit 1
      fi

      touch "$lockfile"
    fi
}


stop() {

    echo -n $"Stopping ${PROC_NAME} service:"

    ps aux | grep -E 'daphne|gunicorn'| grep 'wdoneops' | grep -v grep | awk '{print $2}' | xargs kill -9 &> /dev/null
    sleep 1
    if ps aux|grep -v grep|grep 'python' |grep -E 'wdoneops' ;then
      echo_failure
      echo
    else
      echo_success
      echo
      rm -f "$lockfile"
    fi
}


restart(){
    stop
    start
}

status(){
    if [ -f $lockfile ]; then
      echo "${PROC_NAME} is running..."
    else
      echo "${PROC_NAME} is stoped."
    fi
}

# See how we were called.
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
      echo $"Usage: $0 {start|stop|restart|status}"
      exit 2
esac


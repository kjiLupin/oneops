#!/bin/bash

. /etc/init.d/functions
export PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin:/opt/node/bin


base_dir=$(dirname $0)
PROC_NAME="wd-oneops"

lockfile=/var/lock/subsys/${PROC_NAME}

function start_all() {
  if [ -f $lockfile ]; then
      echo "wd-oneops  is running..."
  else
      echo "Starting ${PROC_NAME} service."

      cd ${base_dir}
      source /usr/local/python36/bin/activate
      # gunicorn wdoneops.wsgi:application -c gunicorn.conf.py >> logs/gunicorn.log 2>&1
      nohup daphne -b 127.0.0.1 -p 8000 wdoneops.asgi:application --access-log logs/access.log &
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

function start_wdoneops() {
  if [ -f $lockfile ]; then
      echo "wd-oneops  is running..."
  else
      echo "Starting ${PROC_NAME} service."

      cd ${base_dir}
      source /usr/local/python36/bin/activate
      # gunicorn wdoneops.wsgi:application -c gunicorn.conf.py >> logs/gunicorn.log 2>&1
      nohup daphne -b 127.0.0.1 -p 8000 wdoneops.asgi:application --access-log logs/access.log &
      sleep 5
      echo -n "--starting wd-oneops:"
      if `netstat -lnpt|grep -qiE ':8000.*python'` ; then
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

function start_celery_worker() {
  cd ${base_dir}
  source /usr/local/python36/bin/activate

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
}

function start_celery_beat() {
  cd ${base_dir}
  source /usr/local/python36/bin/activate

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
}

# See how we were called.
case "$1" in
  all)
        start_all
        ;;
  wdoneops)
        start_wdoneops
        ;;
  celery_worker)
        start_celery_worker
        ;;
  celery_beat)
        start_celery_beat
        ;;
  *)
        echo $"Usage: $0 {all|wdoneops|celery_worker|celery_beat}"
        exit 2
esac
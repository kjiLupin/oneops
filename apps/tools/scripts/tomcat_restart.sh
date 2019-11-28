#!/bin/bash
JAVA_NAME=$1
JAVA_PORT=$2
JAVA_TYPE=$3
JAVA_DO=$4

if [ "$JAVA_NAME" = "" ]; then
    echo "参数不为空，使用sh $0 JAVA_NAME JAVA_PORT JAVA_DO";exit 1
fi

if [ "$JAVA_PORT" = "" ]; then
    echo "参数不为空，使用sh $0 JAVA_NAME JAVA_PORT JAVA_DO";exit 1
fi

if [ "$JAVA_TYPE" = "" ]; then
    echo "参数不为空，使用sh $0 JAVA_NAME JAVA_PORT JAVA_DO";exit 1
fi

if [ "$JAVA_DO" = "" ]; then
    echo "参数不为空，使用sh $0 JAVA_NAME JAVA_PORT JAVA_DO";exit 1
fi


JAVA_KILL(){
	/bin/ps  aux | grep -w $JAVA_NAME | grep -v -w grep  | grep -w $JAVA_PORT | awk '{print $2}' |xargs kill -9
}

JAVA_START(){
	if [ "$JAVA_TYPE" = "war" ]; then
		nohup  sh /data/$JAVA_PORT-$JAVA_NAME/bin/startup.sh  2>&1 &
	elif [ "$JAVA_TYPE" = "jar" ]; then
		JAVA_DEBUG_OPTS=""
		JAVA_MEM_DIR=" -Duser.dir=$1 "
        JAVA_MEM_JMX=" -Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.port=2${java_port} -Dcom.sun.management.jmxremote.ssl=false -Dcom.sun.management.jmxremote.authenticate=false -Djava.rmi.server.hostname=${TOMCAT_IP} "
        JAVA_MEM_SIZE_OPTS="-Xms2548m -Xmx2548m  -XX:PermSize=64m -XX:MaxPermSize=256m -Dfile.encoding=UTF-8"
        JAVA_MEM_OPTS=" -server -XX:+DisableExplicitGC -XX:+UseConcMarkSweepGC -XX:+CMSParallelRemarkEnabled -XX:+UseCMSCompactAtFullCollection $JAVA_MEM_SIZE_OPTS $JAVA_MEM_JMX $JAVA_MEM_DIR"
		cd /tmp
		nohup /usr/local/jdk1.8/bin/java $JAVA_MEM_OPTS $JAVA_DEBUG_OPTS  -jar /data/$JAVA_PORT-$JAVA_NAME/$JAVA_NAME.jar >/dev/null 2>&1 &
		echo "[INFO]$JAVA_PORT-$JAVA_NAME deploy end"
    else
		echo "JAVA_TYPE error"
		exit 1
	fi
}

JAVA_RESTART(){
	JAVA_KILL
	sleep 3
	JAVA_START
}

JAVA_REDEPLOY(){
	JAVA_KILL
	sleep 3
	if [ "$JAVA_TYPE" = "war" ]; then
		nohup sh /jenkins/data/deploy_war.sh /data/$JAVA_PORT-$JAVA_NAME/	$JAVA_NAME.war 2>&1 &
	elif [ "$JAVA_TYPE" = "jar" ]; then
		nohup sh /jenkins/data/deploy_jar.sh /data/$JAVA_PORT-$JAVA_NAME/	$JAVA_NAME.jar 2>&1 &
	else
		echo "JAVA_TYPE error"
		exit 1
	fi
}

if [ "$JAVA_DO" = "kill" ]; then
	JAVA_KILL
	echo "killed"
elif  [ "$JAVA_DO" = "start" ]; then
	JAVA_START
	echo "started"
elif  [ "$JAVA_DO" = "restart" ]; then
	JAVA_RESTART
	echo "restarted"
elif  [ "$JAVA_DO" = "redeploy" ]; then
	JAVA_REDEPLOY
	echo "redeplayed"
else
	echo "do nothing"
	exit 1
fi

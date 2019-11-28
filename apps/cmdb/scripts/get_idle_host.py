#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import os
import re
import sys
import time
import django
from pprint import pprint

base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(base_dir)
os.environ['DJANGO_SETTINGS_MODULE'] = 'wdoneops.settings'
django.setup()

from cmdb.models.asset import Server
from common.utils.zabbix_api import get_access_token, get_host_ids, get_monitor_item_ids, get_history_data


if __name__ == "__main__":
    now_date = int(time.time())
    token = get_access_token()

    # with open("/tmp/1.csv", 'w+') as f:
    # ss = "%s,%s,%d核,%.1f%%,%dM,%.1f%%,%s,%s,%s\n" % (s.hostname, s.login_address, s.cpu_total,
    #     s.cpu_used, int(s.mem_total) / 1024 / 1024, s.mem_used, s.comment, s.app_env, s.date_last_checked)
    # f.write(ss)
    idle_host = list()
    for s in Server.objects.filter(mem_used__lte=50,cpu_used__lte=50).exclude(is_vm=1).exclude(comment='pod').exclude(status__in=['deleted', 'ots']):
        busy_flag = False
        host_ids = get_host_ids(token, [s.login_address.split(":")[0]])
        item_ids = get_monitor_item_ids(token, host_ids, 'vm.memory.size[pavailable]')
        if not host_ids or not item_ids:
            print('not exists.', s.hostname, s.login_address)
            continue
        for i in range(1, 8):
            for data in get_history_data(token, item_ids[host_ids[0]], 0, now_date - 86400 * i, now_date):
                # {'itemid': '46206', 'clock': '1572921966', 'value': '86.2654', 'ns': '966899000'}
                if float(data['value']) < 50:
                    busy_flag = True
                    break
            # 当有某个时刻超过阈值，就不再判断
            if busy_flag is True:
                break
        # 内存忙，无需再判断CPU使用率
        if busy_flag is True:
            continue

        if re.search(r'windows', s.os, re.I):
            item_ids = get_monitor_item_ids(token, host_ids, 'system.cpu.load[percpu,avg1]')
        else:
            item_ids = get_monitor_item_ids(token, host_ids, 'system.cpu.util[,user,avg1]')

        busy_count = 0
        max_cpu_used = 0.0
        for i in range(1, 8):
            for data in get_history_data(token, item_ids[host_ids[0]], 0, now_date - 86400 * i, now_date):
                # {'itemid': '46176', 'clock': '1572834396', 'value': '0.0693', 'ns': '572469063'}
                if max_cpu_used < float(data['value']):
                    max_cpu_used = float(data['value'])
                if float(data['value']) > 50:
                    busy_count += 1
            # 当有某个时刻超过阈值，就不再判断
            # if busy_count > 10:
            #     break

        ss = "%s,%s,%d核,%.1f%%,%d,%dM,%.1f%%,%s,%s,%s\n" % (
            s.hostname, s.login_address, s.cpu_total, max_cpu_used, busy_count, int(s.mem_total) / 1024 / 1024,
            s.mem_used, s.comment, s.app_env, s.date_last_checked)
        idle_host.append(ss)
    pprint(idle_host)

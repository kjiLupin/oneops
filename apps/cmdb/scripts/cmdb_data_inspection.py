#!/usr/bin/env python
# coding:utf-8

import os
import sys
import datetime
import traceback
import django
from pprint import pprint

base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(base_dir)
os.environ['DJANGO_SETTINGS_MODULE'] = 'wdoneops.settings'
django.setup()

from common.utils.base import send_msg_to_admin
from cmdb.models.base import Ip
from cmdb.models.asset import Server, NetDevice, Nic


def cmdb_agent_running_check():
    try:
        one_day_ago = (datetime.date.today() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d %H:%M:%S")

        one_day_no_updated = list()
        for s in Server.objects.filter(date_last_checked__lte=one_day_ago).exclude(uuid='').exclude(comment='pod').\
                exclude(status__in=['deleted', 'ots']):
            nic_list = Nic.objects.filter(server=s)
            ips = ['{}({})'.format(ip.ip, ip.last_detected) for nic in nic_list for ip in nic.ip.all()]

            if not ips:
                if not s.app.all() and not s.pre_app.all() and s.is_vm is True:
                    print(s.hostname, s.date_last_checked)
                    s.delete()
                    continue
            one_day_no_updated.append("%-20s\t%-20s\t%-20s\t%-20s\n" % (s.hostname, ','.join(ips),
                                                                        s.applicant, s.date_last_checked))
        if one_day_no_updated:
            num = 0
            while num < len(one_day_no_updated):
                pprint(one_day_no_updated[num: num + 500])
                send_msg_to_admin(
                    '以下服务器与cmdb失联超过1天，请确认cmdb_agent脚本正常执行：\n主机名\tIP\t申请人\t最后一次检测时间\n' + '\n'.join(one_day_no_updated[num:num + 500]))
                num += 500

    except Exception:
        send_msg_to_admin(str(traceback.print_exc()))


def no_binding_ip_check():
    try:
        no_device_binding = list()
        for ip in Ip.objects.all():
            if Nic.objects.filter(ip=ip).exists() or NetDevice.objects.filter(ip=ip).exists():
                continue
            if Server.objects.filter(manage_address=ip.ip).exists() or Server.objects.filter(
                    manage_address=ip.ip + ":22").exists():
                continue
            no_device_binding.append("%-20s\t%-20s\t%-20s" % (ip.ip, ip.comment, ip.last_detected))
        if no_device_binding:
            pprint(no_device_binding)
            send_msg_to_admin('以下ip没有与任何主机设备关联：\nIP\t备注\t最后一次检测时间\n' + '\n'.join(no_device_binding))
    except Exception:
        send_msg_to_admin(str(traceback.print_exc()))


def dead_ip_check():
    try:
        three_day_ago = (datetime.date.today() + datetime.timedelta(days=-3)).strftime("%Y-%m-%d %H:%M:%S")
        dead_ip_list = list()
        for ip in Ip.objects.filter(last_detected__lte=three_day_ago):
            dead_ip_list.append("%-20s\t%-20s\t%-20s" % (ip.ip, ip.comment, ip.last_detected))
        if dead_ip_list:
            pprint(dead_ip_list)
            send_msg_to_admin('以下ip3天未扫描到（请确定是否可以释放ip资源）：\nIP\t备注\t最后一次检测时间\n' + '\n'.join(dead_ip_list))
    except Exception:
        send_msg_to_admin(str(traceback.print_exc()))


def no_binding_and_dead_ip_check():
    no_device_binding = list()
    for ip in Ip.objects.all():
        if Nic.objects.filter(ip=ip).exists() or NetDevice.objects.filter(ip=ip).exists():
            continue
        if Server.objects.filter(manage_address=ip.ip).exists() or Server.objects.filter(
                manage_address=ip.ip + ":22").exists():
            continue
        no_device_binding.append("%-20s\t%-20s\t%-20s" % (ip.ip, ip.comment, ip.last_detected))
    three_day_ago = (datetime.date.today() + datetime.timedelta(days=-3)).strftime("%Y-%m-%d %H:%M:%S")
    dead_ip_list = list()
    for ip in Ip.objects.filter(last_detected__lte=three_day_ago):
        dead_ip_list.append("%-20s\t%-20s\t%-20s" % (ip.ip, ip.comment, ip.last_detected))
    # 两个list交集
    res = list(set(no_device_binding).intersection(set(dead_ip_list)))
    if res:
        pprint(res)
        send_msg_to_admin('以下ip未绑定设备，并且3天未扫描到：\nIP\t备注\t最后一次检测时间\n' + '\n'.join(res))

if __name__ == "__main__":
    cmdb_agent_running_check()
    # no_binding_and_dead_ip_check()
    # no_binding_ip_check()
    # dead_ip_check()

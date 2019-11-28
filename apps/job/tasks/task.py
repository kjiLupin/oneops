# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import traceback
import datetime
from celery import shared_task
from accounts.models import User
from job.models.job import Job
from cmdb.models.base import Ip
from cmdb.models.asset import Server, Pod, NetDevice, Nic
from cmdb.views.server import get_ips_by_server_id
from job.views.cmd_execute import exec_job
from common.utils.base import send_msg_to_admin


@shared_task
def periodic_job(job_id, user_id):
    job = Job.objects.get(id=job_id)
    user = User.objects.get(id=user_id)
    res = exec_job(job, user)
    print('Periodic Task:', res, job_id, user_id)


@shared_task
def no_binding_ip_check():
    try:
        no_device_binding_msg = ''
        for ip in Ip.objects.all():
            if Nic.objects.filter(ip=ip).exists() \
                    or Pod.objects.filter(ip=ip.ip).exists()\
                    or NetDevice.objects.filter(ip=ip).exists():
                pass
            else:
                no_device_binding_msg += "%-20s\t%-20s\t%-20s\n" % (ip.ip, ip.comment, ip.last_detected)
        if no_device_binding_msg:
            send_msg_to_admin('以下ip没有与任何主机设备关联：\nIP\t备注\t最后一次检测时间\n' + no_device_binding_msg)
    except Exception:
        send_msg_to_admin(str(traceback.print_exc()))


@shared_task
def host_alive_check():
    try:
        one_day_ago = (datetime.date.today() + datetime.timedelta(days=-1)).strftime("%Y-%m-%d %H:%M:%S")

        one_day_no_updated = ''
        for s in Server.objects.filter(date_last_checked__lte=one_day_ago):
            ips = get_ips_by_server_id(s.id)
            one_day_no_updated += "%-20s\t%-20s\t%-20s\t%-20s\n" % (s.hostname, ','.join(ips), s.applicant,
                                                                    s.date_last_checked)
        if one_day_no_updated:
            send_msg_to_admin('以下服务器与cmdb失联超过1天，请确认cmdb_agent.py脚本正常执行：\n主机名\tIP\t申请人\t最后一次检测时间\n' + one_day_no_updated)
    except Exception:
        send_msg_to_admin(str(traceback.print_exc()))

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import traceback
from django.urls import reverse_lazy
from celery import shared_task
from common.utils.base import ROOT_URL
from common.utils.email_api import MailSender
from workflow.models import Workflow, CommonFlow, CommonFlowArg, FlowStep


@shared_task
def expired_map_rule_notify():
    # 到期的端口映射 规则通知给网络管理员
    wf = Workflow.objects.get(code='cross_segment_access')
    for cf in CommonFlow.objects.filter(workflow=wf, status='ongoing'):
        invalid_time = CommonFlowArg.objects.get(cf=cf, arg='invalid_time').value
        if invalid_time and datetime.datetime.strptime(invalid_time, '%Y-%m-%d') < datetime.datetime.now():
            source_ip = CommonFlowArg.objects.get(cf=cf, arg='source_ip').value
            destination_ip = CommonFlowArg.objects.get(cf=cf, arg='destination_ip').value
            destination_port = CommonFlowArg.objects.get(cf=cf, arg='destination_port').value
            mail_to = list()
            next_fas = FlowStep.objects.get(workflow=wf, step=cf.current_step + 1)
            for u in next_fas.group.user_set.all():
                mail_to.append(u.email)
            cont = '源地址：{}\n目的地址：{}\n目的端口：{}\n失效时间：{}\n申请人：{}\n申请原因：{}\n工单地址：{}{}\n'.format(
                source_ip, destination_ip, destination_port, invalid_time, cf.applicant, cf.reason, ROOT_URL,
                reverse_lazy('workflow:flow-cross-segment-access-detail', kwargs={'flow_id': int(cf.id)}))
            date_today = datetime.datetime.now().strftime("%Y-%m-%d")
            print(date_today, cont)
            MailSender().send_email("跨网段端口访问申请已到期 %s" % date_today, cont,
                                    list_to_addr=list(set(mail_to)), list_cc_addr=list())

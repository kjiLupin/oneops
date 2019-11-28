# -*- coding: utf-8 -*-
import re
import datetime
import simplejson as json
from django.db.models import Q, F
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from common.mixins import JSONResponseMixin
from common.utils.email_api import MailSender
from common.utils.base import ROOT_URL
from workflow.models import Workflow, CommonFlow, CommonFlowArg, FlowStep, FlowStepLog


class CrossSegmentAccessView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/net_cross_segment_access.html"

    def get_context_data(self, **kwargs):
        wf = Workflow.objects.get(code='cross_segment_access')
        context = {
            "path1": "Workflow",
            "path2": "跨网段访问申请",
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        wf = Workflow.objects.get(code='cross_segment_access')
        if not FlowStep.objects.filter(workflow=wf).exists():
            return self.render_json_response({"code": -1, "errmsg": "该流程未配置工单步骤！"})
        fs = FlowStep.objects.get(workflow=wf, step=1)
        if fs.group and fs.group not in request.user.groups.all():
            return self.render_json_response({"code": -1, "errmsg": "您无权执行该流程！"})

        wf.counts = F('counts') + 1
        wf.save(update_fields=['counts'])
        date_today = datetime.datetime.now().strftime("%Y-%m-%d")

        map_type = request.POST.get('map_type')
        source_ip = request.POST.get('source_ip')
        destination_ip = request.POST.get('destination_ip')
        destination_port = request.POST.get('destination_port')
        invalid_time = request.POST.get('invalid_time')
        never = request.POST.get('never')
        reason = request.POST.get('reason')

        if not source_ip:
            source_ip = "允许所有来源地址"
        if not re.match(r'((25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))\.){3}(25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))', destination_ip):
            return self.render_json_response({"code": -1, "errmsg": "目的地址填写错误！"})

        if never:
            invalid_time = "永不过期"
        elif invalid_time:
            if datetime.datetime.strptime(invalid_time, '%Y-%m-%d') <= datetime.datetime.now():
                return self.render_json_response({"code": -1, "errmsg": "时间选择错误！"})
        else:
            return self.render_json_response({"code": -1, "errmsg": "请选择失效日期！"})

        print(map_type, source_ip, destination_ip, destination_port, invalid_time, never, reason)
        cont = '源地址：{}\n目的地址：{}\n目的端口：{}\n失效时间：{}\n申请人：{}\n申请原因：{}\n'.format(
            source_ip, destination_ip, destination_port, invalid_time, request.user.username, reason)

        cf = CommonFlow.objects.create(workflow=wf, applicant=request.user, content=cont, reason=reason, status='pending')
        CommonFlowArg.objects.filter(cf=cf).delete()
        cfas = list()
        cfas.append(CommonFlowArg(cf=cf, arg='map_type', value=map_type))
        cfas.append(CommonFlowArg(cf=cf, arg='source_ip', value=source_ip))
        cfas.append(CommonFlowArg(cf=cf, arg='destination_ip', value=destination_ip))
        cfas.append(CommonFlowArg(cf=cf, arg='destination_port', value=destination_port))
        cfas.append(CommonFlowArg(cf=cf, arg='invalid_time', value=invalid_time))
        CommonFlowArg.objects.bulk_create(cfas)

        mail_to = list()
        fas = FlowStep.objects.get(workflow=wf, step=2)
        if fas.group:
            for u in fas.group.user_set.all():
                mail_to.append(u.email)
            mail_cc = list([request.user.email])
            mail_cont = '{}工单地址：{}{}\n'.format(
                cont, ROOT_URL, reverse_lazy('workflow:flow-cross-segment-access-detail', kwargs={'flow_id': cf.id}))
            MailSender().send_email("申请跨网段ip端口访问 %s" % date_today, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))
        return self.render_json_response({"code": 0, "flow_id": cf.id})


class CrossSegmentAccessDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/net_cross_segment_access_detail.html"

    def get_context_data(self, **kwargs):
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)
        fsl_list = FlowStepLog.objects.filter(cf=cf).order_by('-id')
        context = {
            "path1": "Workflow",
            "path2": "跨网段访问申请",
            "wf_type": cf.workflow.get_wf_type_display(),
            "wf_name": cf.workflow.name,
            "flow_id": flow_id,
            "status": cf.status,
            "current_step": cf.current_step + 1,
            "fsl_list": fsl_list,
            "applicant": cf.applicant.username,
            "reason": cf.reason,
            "content": "申请人：{}\n{}".format(cf.applicant.username, cf.content),
            "result": cf.result,
            "update_time": cf.update_time
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        wf = Workflow.objects.get(code='cross_segment_access')
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)
        current_step = int(request.POST.get('current_step', 1))
        source_ip = CommonFlowArg.objects.get(cf=cf, arg='source_ip').value
        destination_ip = CommonFlowArg.objects.get(cf=cf, arg='destination_ip').value
        destination_port = CommonFlowArg.objects.get(cf=cf, arg='destination_port').value
        invalid_time = CommonFlowArg.objects.get(cf=cf, arg='invalid_time').value

        if request.POST.get('action') == "stop":
            flow_step = FlowStep.objects.get(workflow=wf, step=current_step)
            mail_to = [cf.applicant.email]
            mail_cc = list()
            for user in flow_step.group.user_set.all():
                mail_cc.append(user.email)
            mail_cont = """
            以下跨网段访问申请流程已被终止：
            源地址：{0}
            目的地址：{1}
            目的端口：{2}
            失效时间：{3}
            原因：{4}
            工单地址：{5}{6}
            """.format(source_ip, destination_ip, destination_port, invalid_time, cf.reason, ROOT_URL,
                       reverse_lazy('workflow:flow-cross-segment-access-detail', kwargs={'flow_id': int(flow_id)}))
            MailSender().send_email("跨网段访问申请流程已被终止！", mail_cont, list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))
            FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=request.user,
                                       is_passed=False, reply=mail_cont)
            cf.status = 'rejected'
            cf.current_step = current_step
            cf.save(update_fields=['status', 'current_step'])
            res = {'code': 0, "result": "跨网段访问申请流程已被终止！"}
        else:
            if current_step == 2:
                # 通知申请人，访问权限已开通
                flow_step = FlowStep.objects.get(workflow=wf, step=current_step)
                mail_to = [cf.applicant.email]
                mail_cc = list()
                for user in flow_step.group.user_set.all():
                    mail_cc.append(user.email)
                mail_cont = """
                以下跨网段访问申请流程已开通：
                源地址：{0}
                目的地址：{1}
                目的端口：{2}
                失效时间：{3}
                原因：{4}
                工单地址：{5}{6}
                """.format(source_ip, destination_ip, destination_port, invalid_time, cf.reason, ROOT_URL,
                           reverse_lazy('workflow:flow-cross-segment-access-detail', kwargs={'flow_id': int(flow_id)}))
                MailSender().send_email("应用创建流程已开通！", mail_cont, list_to_addr=list(set(mail_to)),
                                        list_cc_addr=list(set(mail_cc)))

                FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=request.user,
                                           is_passed=True, reply=mail_cont)
                cf.status = 'ongoing'
                cf.current_step = current_step
                cf.save(update_fields=['status', 'current_step'])
                res = {'code': 0, "result": "跨网段访问规则已经添加！"}
            elif current_step == 3:
                # 删除跨网段访问规则
                cf.status = 'end'
                cf.current_step = current_step
                cf.save(update_fields=['status', 'current_step'])
                res = {'code': 0, "result": "跨网段访问规则已经删除！"}
            else:
                res = {'code': -1, "result": "非法调用！"}
        return self.render_json_response(res)

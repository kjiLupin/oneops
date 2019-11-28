# -*- coding: utf-8 -*-
import datetime
import uuid
import traceback
import simplejson as json
from django.urls import reverse_lazy
from django.db.models import F, Max
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from wdoneops.celery import celery_app
from common.mixins import JSONResponseMixin
from common.utils.email_api import MailSender
from common.utils.base import ROOT_URL, send_msg_to_admin
from accounts.models import User
from workflow.models import Workflow, CommonFlow, CommonFlowArg, FlowStep, FlowStepLog
from job.tasks.ansible_api import AnsibleAPI
from job.tasks.gen_resource import GenResource
from cmdb.models.business import App
from cmdb.views.ip import get_ips_by_server_id


@celery_app.task
def run_tomcat(flow_id, user_id, app_id, hostname, step):
    cf = CommonFlow.objects.get(id=flow_id)
    wf = cf.workflow
    user = User.objects.get(id=user_id)
    app = App.objects.get(id=app_id)
    try:
        s = app.app_server.get(hostname=hostname)
        resource = GenResource.gen_host_list([s.id])
        ans = AnsibleAPI(0, str(uuid.uuid4()), resource=resource, hosts_file=None)
        date_now = datetime.datetime.now().strftime("%Y%m%d%H%M")
        file_name = "%s-%s" % (date_now, app.app_code)
        extra_vars = {"apphost": "default_group", "app_name": app.app_code,
                      "app_port": app.tomcat_port, "file_name": file_name}
        if cf.workflow.code == 'tomcat_dump':
            ans.run_playbook(playbook=["/data/ansible/playbook/admin/tomcat_dump.yml"], extra_vars=extra_vars)
            cont = "文件下载地址：{}/media/tomcat/{}.phrof".format(ROOT_URL, file_name)

            # 邮件发给当前流程的操作人，并抄送应用申请人 及 当前流程操作组中的其他人
            mail_to = [cf.applicant.email]
            flow_step = FlowStep.objects.get(workflow=wf, step=step)
            mail_cc = list()
            for email in app.primary.split(",") + app.secondary.split(","):
                mail_cc.append(email)
            for u in flow_step.group.user_set.all():
                mail_cc.append(u.email)
            mail_cont = """
                        应用名：{0}
                        端口：{1}
                        导出服务器：{2}
                        工单地址：{3}{4}
    
                        该Tomcat在线Dump流程已执行！
                        """.format(app.app_code, app.tomcat_port, hostname, ROOT_URL,
                                   reverse_lazy('workflow:flow-tomcat-dump-detail', kwargs={'flow_id': int(flow_id)}))
            MailSender().send_email("%s Tomcat在线Dump流程已执行" % app.app_code, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))
            FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=user,
                                       is_passed=True, reply=mail_cont)
        elif cf.workflow.code == 'tomcat_jstack':
            ans.run_playbook(playbook=["/data/ansible/playbook/admin/tomcat_jstack.yml"], extra_vars=extra_vars)
            cont = "文件下载地址：{}/media/tomcat/{}.jstack".format(ROOT_URL, file_name)
        cf.current_step = step
        cf.status = 'end'
        cf.save(update_fields=['current_step', 'status'])

        flow_step = FlowStep.objects.get(workflow=wf, step=step+1)
        FlowStepLog.objects.filter(cf=cf, flow_step=flow_step, operator=user).update(is_passed=True, reply=cont)
    except Exception as e:
        cf.result = traceback.print_exc()
        cf.save(update_fields=['result'])
        send_msg_to_admin(traceback.print_exc())


class TomcatDumpView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/tomcat_dump.html"

    def get_context_data(self, **kwargs):
        wf = Workflow.objects.get(code='tomcat_dump')
        context = {
            "path1": "Workflow",
            "path2": "Tomcat Dump",
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name,
            "app_list": [{"id": a.id, "code": a.app_code} for a in App.objects.filter(status=1)]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        wf = Workflow.objects.get(code='tomcat_dump')
        if not FlowStep.objects.filter(workflow=wf).exists():
            return self.render_json_response({"code": -1, "errmsg": "该流程未配置工单步骤！"})
        app_id = request.POST.get('app_id')
        hostname = request.POST.get('hostname')
        if app_id and hostname:
            app = App.objects.get(id=app_id)
            if app.app_server.filter(hostname=hostname).count() != 1:
                res = {'code': 1, "errmsg": "该主机名不唯一，请更改后重试！"}
                return self.render_json_response(res)
            s = app.app_server.get(hostname=hostname)
            ips = get_ips_by_server_id(s.id)
            date_today = datetime.datetime.now().strftime("%Y-%m-%d")
            cont = '应用编码：{}\n名称：{}\n端口：{}\n导出服务器：{} {}\n申请人：{}\n'.format(
                app.app_code, app.app_name, app.tomcat_port, hostname, ','.join(ips), request.user.username)
            cf = CommonFlow.objects.create(workflow=wf, applicant=request.user, content=cont, status='pending')
            CommonFlowArg.objects.filter(cf=cf).delete()
            CommonFlowArg.objects.create(cf=cf, arg='app_id', value=app_id)
            CommonFlowArg.objects.create(cf=cf, arg='hostname', value=hostname)

            mail_to = list()
            for fas in FlowStep.objects.filter(workflow=wf, step=2):
                if fas.group is None:
                    continue
                for u in fas.group.user_set.all():
                    mail_to.append(u.email)
            mail_cc = [request.user.email]
            for email in app.primary.split(",") + app.secondary.split(","):
                mail_cc.append(email)
            mail_cont = '{}工单地址：{}{}\n'.format(
                cont, ROOT_URL, reverse_lazy('workflow:flow-tomcat-dump-detail', kwargs={'flow_id': cf.id}))
            MailSender().send_email("Tomcat应用在线Dump申请 %s" % date_today, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))
            wf.counts = F('counts') + 1
            wf.save(update_fields=['counts'])
            res = {'code': 0, 'result': "申请已提交成功！", 'flow_id': cf.id}
        else:
            res = {'code': 1, "errmsg": "非法调用！"}
        return self.render_json_response(res)


class TomcatDumpDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/tomcat_dump_detail.html"

    def get_context_data(self, **kwargs):
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)
        fsl_list = FlowStepLog.objects.filter(cf=cf).order_by('-id')

        app_id = CommonFlowArg.objects.get(cf=cf, arg='app_id').value
        app = App.objects.get(id=app_id)
        app_detail = {'id': app_id, 'app_code': app.app_code, 'app_type': app.app_type,
                      'tomcat_port': app.tomcat_port, 'comment': app.comment}

        context = {
            "path1": "Workflow",
            "path2": "Tomcat Dump",
            "wf_type": cf.workflow.get_wf_type_display(),
            "wf_name": cf.workflow.name,
            "flow_id": flow_id,
            "status": cf.status,
            "current_step": cf.current_step + 1,
            "app_detail": app_detail,
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
        wf = Workflow.objects.get(code='tomcat_dump')
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)

        app_id = CommonFlowArg.objects.get(cf=cf, arg='app_id').value
        hostname = CommonFlowArg.objects.get(cf=cf, arg='hostname').value
        if request.POST.get('action') == "stop":
            app = App.objects.get(id=app_id)
            mail_to = [cf.applicant.email]
            flow_step = FlowStep.objects.get(workflow=wf, step=2)
            mail_cc = list()
            for email in app.primary.split(",") + app.secondary.split(","):
                mail_cc.append(email)
            for user in flow_step.group.user_set.all():
                mail_cc.append(user.email)
            mail_cont = """
            以下Tomcat在线Dump流程已被终止：
            应用名：{0}
            端口：{1}
            导出服务器：{2}
            工单地址：{3}{4}
            """.format(app.app_code, app.tomcat_port, hostname, ROOT_URL,
                       reverse_lazy('workflow:flow-tomcat-dump-detail', kwargs={'flow_id': int(flow_id)}))

            MailSender().send_email("%s Tomcat在线Dump流程已被终止" % app.app_code, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))
            FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=request.user,
                                       is_passed=False, reply=mail_cont)
            cf.status = 'rejected'
            cf.current_step = 2
            cf.save(update_fields=['status', 'current_step'])
            res = {'code': 0, "result": "该Tomcat在线Dump流程已终止！"}
            return self.render_json_response(res)

        current_step = int(request.POST.get('current_step', 1))
        if current_step == 1:
            res = {'code': 1, "errmsg": "非法调用！"}
        elif current_step == 2:
            run_tomcat.delay(flow_id, request.user.id, app_id, hostname, current_step)

            flow_step = FlowStep.objects.get(workflow=wf, step=3)
            FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=request.user,
                                       is_passed=True, reply="脚本执行中，请稍后查看……")
            res = {'code': 0, "result": "Tomcat在线Dump流程后台执行中……请等待邮件通知！"}
        else:
            res = {'code': 1, "errmsg": "非法调用！"}
        return self.render_json_response(res)


class TomcatProcessExplorerView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/tomcat_jstack.html"

    def get_context_data(self, **kwargs):
        wf = Workflow.objects.get(code='tomcat_jstack')
        context = {
            "path1": "Workflow",
            "path2": "Tomcat ProcessExplorer",
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name,
            "app_list": [{"id": a.id, "code": a.app_code} for a in App.objects.filter(status=1)]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        wf = Workflow.objects.get(code='tomcat_jstack')
        if not FlowStep.objects.filter(workflow=wf).exists():
            return self.render_json_response({"code": -1, "errmsg": "该流程未配置工单步骤！"})
        app_id = request.POST.get('app_id')
        hostname = request.POST.get('hostname')
        if app_id and hostname:
            app = App.objects.get(id=app_id)
            if app.app_server.filter(hostname=hostname).count() != 1:
                res = {'code': 1, "errmsg": "该主机名不唯一，请更改后重试！"}
                return self.render_json_response(res)
            s = app.app_server.get(hostname=hostname)
            ips = get_ips_by_server_id(s.id)
            cont = '应用编码：{}\n名称：{}\n端口：{}\n服务器：{} {}\n申请人：{}\n'.format(
                app.app_code, app.app_name, app.tomcat_port, hostname, ','.join(ips), request.user.username)
            cf = CommonFlow.objects.create(workflow=wf, applicant=request.user, content=cont, status='ongoing')

            run_tomcat.delay(cf.id, request.user.id, app_id, hostname, 2)
            flow_step = FlowStep.objects.get(workflow=wf, step=3)
            FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=request.user,
                                       is_passed=True, reply="脚本执行中，请稍后查看……")

            wf.counts = F('counts') + 1
            wf.save(update_fields=['counts'])
            res = {'code': 0, 'result': "申请已提交成功！", 'flow_id': cf.id}
        else:
            res = {'code': 1, "errmsg": "非法调用！"}
        return self.render_json_response(res)


class TomcatProcessExplorerDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/tomcat_jstack_detail.html"

    def get_context_data(self, **kwargs):
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)
        fsl_list = FlowStepLog.objects.filter(cf=cf).order_by('-id')

        context = {
            "path1": "Workflow",
            "path2": "Tomcat ProcessExplorer",
            "wf_type": cf.workflow.get_wf_type_display(),
            "wf_name": cf.workflow.name,
            "flow_id": flow_id,
            "status": cf.status,
            "current_step": cf.current_step + 1,
            "applicant": cf.applicant.username,
            "reason": cf.reason,
            "fsl_list": fsl_list,
            "content": "申请人：{}\n{}".format(cf.applicant.username, cf.content),
            "result": cf.result,
            "update_time": cf.update_time
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

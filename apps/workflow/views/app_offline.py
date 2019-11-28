# -*- coding: utf-8 -*-
import datetime
import re
import simplejson as json
from django.urls import reverse_lazy
from django.db.models import F, Max
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from common.mixins import JSONResponseMixin
from common.utils.email_api import MailSender
from common.utils.base import ROOT_URL
from workflow.models import Workflow, CommonFlow, CommonFlowArg, FlowStep, FlowStepLog
from cmdb.models.business import App


class AppOfflineView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/app_offline.html"

    def get_context_data(self, **kwargs):
        wf = Workflow.objects.get(code='app_offline')
        context = {
            "path1": "Workflow",
            "path2": "App Offline",
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name,
            "app_list": [{"id": a.id, "code": a.app_code} for a in App.objects.filter(status=1)]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        wf = Workflow.objects.get(code='app_offline')
        if not FlowStep.objects.filter(workflow=wf).exists():
            return self.render_json_response({"code": -1, "errmsg": "该流程未配置工单步骤！"})
        app_id = request.POST.get('app_id')
        if app_id:
            app = App.objects.get(id=app_id)
            date_today = datetime.datetime.now().strftime("%Y-%m-%d")
            cont = '应用编码：{}\n名称：{}\n端口：{}\n类型：{}\n仓库：{}\n业务部门：{}\n重要性：{}\n描述：{}\n申请人：{}\n'.format(
                app.app_code, app.app_name, app.tomcat_port, app.app_type, app.scm_url, app.biz_mgt_dept.dept_name,
                app.importance, app.comment, request.user.username)
            cf = CommonFlow.objects.create(workflow=wf, applicant=request.user, content=cont, status='pending')
            CommonFlowArg.objects.filter(cf=cf).delete()
            CommonFlowArg.objects.create(cf=cf, arg='app_id', value=app_id)

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
                cont, ROOT_URL, reverse_lazy('workflow:flow-app-offline-detail', kwargs={'flow_id': cf.id}))
            MailSender().send_email("旧应用下线申请 %s" % date_today, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))
            wf.counts = F('counts') + 1
            wf.save(update_fields=['counts'])
            res = {'code': 0, 'result': "申请已提交成功！", 'flow_id': cf.id}
        else:
            res = {'code': 1, "errmsg": "非法调用！"}
        return self.render_json_response(res)


class AppOfflineDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/app_offline_detail.html"

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
            "path2": "App Offline",
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
        wf = Workflow.objects.get(code='app_offline')
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)
        current_step = int(request.POST.get('current_step', 1))
        if request.POST.get('action') == "stop":
            app_id = request.POST.get('app_id')
            app = App.objects.get(id=app_id)
            app.status = 1
            app.save(update_fields=['status'])

            mail_to = [cf.applicant.email]
            flow_step = FlowStep.objects.get(workflow=wf, step=current_step)
            mail_cc = list()
            for email in app.primary.split(",") + app.secondary.split(","):
                mail_cc.append(email)
            for user in flow_step.group.user_set.all():
                mail_cc.append(user.email)
            mail_cont = """
            以下应用下线流程已被终止：
            应用名：{0}
            端口：{1}
            描述：{2}
            工单地址：{3}{4}
            """.format(app.app_code, app.tomcat_port, app.comment, ROOT_URL,
                       reverse_lazy('workflow:flow-app-offline-detail', kwargs={'flow_id': int(flow_id)}))

            MailSender().send_email("%s 应用下线流程已被终止！" % app.app_code, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))
            FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=request.user,
                                       is_passed=False, reply=mail_cont)
            cf.status = 'rejected'
            cf.current_step = current_step
            cf.save(update_fields=['status', 'current_step'])
            res = {'code': 0, "result": "该应用下线流程已终止！"}
            return self.render_json_response(res)

        if current_step == 1:
            res = {'code': 1, "errmsg": "非法调用！"}
        elif current_step == 2:
            app_id = request.POST.get('app_id')
            app = App.objects.get(id=app_id)
            app.status = 2
            app.save(update_fields=['status'])

            # 邮件发给当前流程的操作人，并抄送应用申请人 及 当前流程操作组中的其他人
            mail_to = [cf.applicant.email]
            flow_step = FlowStep.objects.get(workflow=wf, step=current_step)
            mail_cc = list()
            for email in app.primary.split(",") + app.secondary.split(","):
                mail_cc.append(email)
            for user in flow_step.group.user_set.all():
                mail_cc.append(user.email)
            mail_cont = """
            应用名：{0}
            端口：{1}
            描述：{2}
            项目部署路径：/data/{1}-{0}
            工单地址：{3}{4}
            
            已将该应用在 Dubbo / Nginx 下线！
            """.format(app.app_code, app.tomcat_port, app.comment, ROOT_URL,
                       reverse_lazy('workflow:flow-app-offline-detail', kwargs={'flow_id': int(flow_id)}))
            MailSender().send_email("%s 应用下线Dubbo/Nginx" % app.app_code, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))
            FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=request.user,
                                       is_passed=True, reply=mail_cont)
            cf.status = 'ongoing'
            cf.current_step = current_step
            cf.save(update_fields=['status', 'current_step'])
            res = {'code': 0, "result": "已将该应用在 Dubbo / Nginx 下线！"}
        elif current_step == 3:
            # Zabbix 禁用
            app_id = request.POST.get('app_id')
            app = App.objects.get(id=app_id)

            # zabbix api todo
            app.status = 3
            app.save(update_fields=['status'])
            # app.app_server.clear()
            # app.pre_app_server.clear()

            mail_to = [cf.applicant.email]
            mail_cc = [email for email in app.primary.split(",") + app.secondary.split(",")]
            mail_cont = """
            应用名：{0}
            端口：{1}
            描述：{2}
            项目部署路径：/data/{1}-{0}
            工单地址：{3}{4}
            
            恭喜：该应用下线完毕！
            """.format(app.app_code, app.tomcat_port, app.comment, ROOT_URL,
                       reverse_lazy('workflow:flow-app-apply-detail', kwargs={'flow_id': int(flow_id)}))
            MailSender().send_email("%s 旧应用下线完毕" % app.app_code, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))

            fas = FlowStep.objects.get(workflow=wf, step=current_step)
            FlowStepLog.objects.create(cf=cf, flow_step=fas, operator=request.user,
                                       is_passed=True, reply=mail_cont)
            cf.current_step = current_step
            cf.save(update_fields=['current_step'])
            res = {'code': 0, "result": "旧应用下线完毕！"}
        elif current_step == 4:
            # 停止应用进程，备份应用代码，执行 playbook 作业
            app_id = request.POST.get('app_id')
            app = App.objects.get(id=app_id)
            # todo
            cf.status = 'end'
            cf.current_step = current_step
            cf.save(update_fields=['status', 'current_step'])
            res = {'code': 0, "result": "停止应用进程，备份应用代码的作业后台执行中......"}
        else:
            res = {'code': 1, "errmsg": "非法调用！"}
        return self.render_json_response(res)

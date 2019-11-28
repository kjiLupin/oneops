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
from cmdb.models.asset import Server
from cmdb.views.business import AppListView, AppAuditListView
from cmdb.views.ip import get_ips_by_server_id


class AppApplyView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/app_apply.html"

    def get_context_data(self, **kwargs):
        wf = Workflow.objects.get(code='app_apply')
        context = {
            "path1": "Workflow",
            "path2": "App Apply",
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        wf = Workflow.objects.get(code='app_apply')
        if not FlowStep.objects.filter(workflow=wf).exists():
            return self.render_json_response({"code": -1, "errmsg": "该流程未配置工单步骤！"})
        fs = FlowStep.objects.get(workflow=wf, step=1)
        if fs.group and fs.group not in request.user.groups.all():
            return self.render_json_response({"code": -1, "errmsg": "您无权执行该流程！"})
        res = json.loads(AppListView().post(request=request).content)
        if res['code'] == 0:
            wf.counts = F('counts') + 1
            wf.save(update_fields=['counts'])
            app = App.objects.get(id=res['id'])
            date_today = datetime.datetime.now().strftime("%Y-%m-%d")
            cont = '应用编码：{}\n名称：{}\n端口：{}\n类型：{}\n仓库：{}\n业务部门：{}\n重要性：{}\n描述：{}\n申请人：{}\n'.format(
                app.app_code, app.app_name, app.tomcat_port, app.app_type, app.scm_url, app.biz_mgt_dept.dept_name,
                app.importance, app.comment, request.user.username)
            cf = CommonFlow.objects.create(workflow=wf, applicant=request.user, content=cont, status='pending')
            CommonFlowArg.objects.filter(cf=cf).delete()
            cfas = list()
            cfas.append(CommonFlowArg(cf=cf, arg='app_id', value=res['id']))
            cfas.append(CommonFlowArg(cf=cf, arg='app_code', value=app.app_code))
            cfas.append(CommonFlowArg(cf=cf, arg='app_name', value=app.app_name))
            cfas.append(CommonFlowArg(cf=cf, arg='app_type', value=app.app_type))
            cfas.append(CommonFlowArg(cf=cf, arg='tomcat_port', value=app.tomcat_port))
            cfas.append(CommonFlowArg(cf=cf, arg='comment', value=app.comment))
            CommonFlowArg.objects.bulk_create(cfas)
            res['flow_id'] = cf.id

            mail_to = list()
            fas = FlowStep.objects.get(workflow=wf, step=2)
            if fas.group:
                for u in fas.group.user_set.all():
                    mail_to.append(u.email)
                mail_cc = list([request.user.email])
                for email in app.primary.split(",") + app.secondary.split(","):
                    mail_cc.append(email)
                mail_cont = '{}工单地址：{}{}\n'.format(
                    cont, ROOT_URL, reverse_lazy('workflow:flow-app-apply-detail', kwargs={'flow_id': cf.id}))
                MailSender().send_email("申请创建新应用 %s" % date_today, mail_cont,
                                        list_to_addr=list(set(mail_to)),
                                        list_cc_addr=list(set(mail_cc)))
        return self.render_json_response(res)


class AppApplyDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/app_apply_detail.html"

    def get_context_data(self, **kwargs):
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)

        app_detail = {'id': 0, 'app_code': '', 'app_type': '', 'tomcat_port': '', 'comment': ''}
        for cfa in CommonFlowArg.objects.filter(cf=cf):
            if cfa.arg == "app_id":
                app_detail["id"] = cfa.value
            else:
                app_detail[cfa.arg] = cfa.value
        fsl_list = FlowStepLog.objects.filter(cf=cf).order_by('-id')
        context = {
            "path1": "Workflow",
            "path2": "App Apply",
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
        wf = Workflow.objects.get(code='app_apply')
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)
        current_step = int(request.POST.get('current_step', 1))
        if request.POST.get('action') == "stop":
            app_id = request.POST.get('app_id')
            app = App.objects.get(id=app_id)

            flow_step = FlowStep.objects.get(workflow=wf, step=current_step)
            mail_to = [cf.applicant.email]
            mail_cc = list()
            for email in app.primary.split(",") + app.secondary.split(","):
                mail_cc.append(email)
            for user in flow_step.group.user_set.all():
                mail_cc.append(user.email)
            mail_cont = """
            以下应用创建流程已被终止：
            应用名：{0}
            端口：{1}
            描述：{2}
            工单地址：{3}{4}
            """.format(app.app_code, app.tomcat_port, app.comment, ROOT_URL,
                       reverse_lazy('workflow:flow-app-apply-detail', kwargs={'flow_id': int(flow_id)}))
            MailSender().send_email("%s 应用创建流程已被终止！" % app.app_code, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))
            FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=request.user,
                                       is_passed=False, reply=mail_cont)
            cf.status = 'cancel' if current_step == 3 else 'rejected'
            cf.current_step = current_step
            cf.save(update_fields=['status', 'current_step'])
            if current_step == 5:
                # 通知DBA，删除数据库账户
                if CommonFlowArg.objects.filter(cf=cf, arg='db_hostname').exists():
                    db_hostname = CommonFlowArg.objects.get(cf=cf, arg='db_hostname').value
                    db_port = CommonFlowArg.objects.get(cf=cf, arg='db_port').value
                    db_user = CommonFlowArg.objects.get(cf=cf, arg='db_user').value
                else:
                    db_hostname, db_port, db_user = "", "", ""

                flow_step = FlowStep.objects.get(workflow=wf, step=current_step - 1)
                mail_to = [cf.applicant.email]
                mail_cc = list()
                for email in app.primary.split(",") + app.secondary.split(","):
                    mail_cc.append(email)
                for user in flow_step.group.user_set.all():
                    mail_cc.append(user.email)
                mail_cont = """
                以下应用创建流程已被终止，请DBA自行删除其数据库账户！
                应用名：{0}
                端口：{1}
                描述：{2}
                数据库地址/账号：{3}:{4}/{5}
                工单地址：{6}{7}
                """.format(app.app_code, app.tomcat_port, app.comment, db_hostname, db_port, db_user, ROOT_URL,
                           reverse_lazy('workflow:flow-app-apply-detail', kwargs={'flow_id': int(flow_id)}))
                MailSender().send_email("%s 应用创建流程已被终止！" % app.app_code, mail_cont,
                                        list_to_addr=list(set(mail_to)),
                                        list_cc_addr=list(set(mail_cc)))
            if current_step >= 3:
                app.app_server.clear()
                app.pre_app_server.clear()
            app.delete()
            res = {'code': 0, "result": "该应用申请流程已终止！"}
            return self.render_json_response(res)

        if current_step == 1:
            res = {'code': 1, "errmsg": "非法调用！"}
        elif current_step == 2:
            res = json.loads(AppAuditListView().post(request).content)
            if res['code'] == 0:
                app_id = request.POST.get('app_id')
                app = App.objects.get(id=app_id)
                prod_host_list = request.POST.getlist('prod_host')
                beta_host_list = request.POST.getlist('beta_host')
                pre_host_list = request.POST.getlist('pre_host')
                test_host_list = request.POST.getlist('test_host')
                prod_host, beta_host, pre_host, test_host = list(), list(), list(), list()
                for s_id in prod_host_list:
                    s = Server.objects.get(id=s_id)
                    s.pre_app.add(app)
                    ips = get_ips_by_server_id(s.id)
                    prod_host.append(ips[0] if ips else s.hostname)
                for s_id in beta_host_list:
                    s = Server.objects.get(id=s_id)
                    s.pre_app.add(app)
                    ips = get_ips_by_server_id(s.id)
                    beta_host.append(ips[0] if ips else s.hostname)
                for s_id in pre_host_list:
                    s = Server.objects.get(id=s_id)
                    s.pre_app.add(app)
                    ips = get_ips_by_server_id(s.id)
                    pre_host.append(ips[0] if ips else s.hostname)
                for s_id in test_host_list:
                    s = Server.objects.get(id=s_id)
                    s.pre_app.add(app)
                    if re.match(r'^mdc-yunwei-k8s-.+', s.hostname, re.I):
                        test_host.append("ip未知，稳定环境构建后才会创建Pod。")
                    else:
                        ips = get_ips_by_server_id(s.id)
                        test_host.append(ips[0] if ips else s.hostname)

                # 邮件发给下一个流程的操作人，并抄送应用申请人 及 当前流程的用户组中所有人
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
                正式服务器：{3}
                Beta服务器：{4}
                预发服务器：{5}
                测试服务器：{6}
                工单地址：{7}{8}
                """.format(app.app_code, app.tomcat_port, app.comment, ",".join(prod_host), ",".join(beta_host),
                           ",".join(pre_host), ",".join(test_host), ROOT_URL,
                           reverse_lazy('workflow:flow-app-apply-detail', kwargs={'flow_id': int(flow_id)}))

                MailSender().send_email("%s 服务器资源分配完成" % app.app_code, mail_cont,
                                        list_to_addr=list(set(mail_to)),
                                        list_cc_addr=list(set(mail_cc)))
                FlowStepLog.objects.create(cf=cf, flow_step=flow_step, operator=request.user,
                                           is_passed=True, reply=mail_cont)
                cf.status = 'ongoing'
                cf.current_step = current_step
                cf.save(update_fields=['status', 'current_step'])
            else:
                pass
        elif current_step == 3:
            # 开发申请创建数据库账户
            app_id = request.POST.get('app_id')
            app = App.objects.get(id=app_id)
            database = request.POST.get('database')

            next_fs = FlowStep.objects.get(workflow=wf, step=current_step + 1)
            mail_to = [u.email for u in next_fs.group.user_set.all()]
            mail_cc = [cf.applicant.email]
            for email in app.primary.split(",") + app.secondary.split(","):
                mail_cc.append(email)

            last_fs = FlowStep.objects.get(workflow=wf, step=current_step - 1)
            fsl = FlowStepLog.objects.filter(cf=cf, flow_step=last_fs)
            if fsl:
                mail_cont = """
                开发填写的数据库名：{0}{1}
                """.format(database, fsl[0].reply)
            else:
                servers = Server.objects.filter(pre_app=app)
                prod_host = servers.filter(app_env='prod').values('login_address')
                beta_host = servers.filter(app_env='beta').values('login_address')
                pre_host = servers.filter(app_env='pre').values('login_address')
                test_host = servers.filter(app_env='test').values('login_address')
                mail_cont = """
                开发填写的数据库名：{0}
                应用名：{1}
                描述：{2}
                正式服务器：{3}
                Beta服务器：{4}
                预发服务器：{5}
                测试服务器：{6}
                工单地址：{7}{8}
                """.format(
                    database,
                    app.app_code,
                    app.comment,
                    ",".join([s['login_address'] for s in prod_host]),
                    ",".join([s['login_address'] for s in beta_host]),
                    ",".join([s['login_address'] for s in pre_host]),
                    ",".join([s['login_address'] for s in test_host]),
                    ROOT_URL,
                    reverse_lazy('workflow:flow-app-apply-detail', kwargs={'flow_id': int(flow_id)})
                )
            MailSender().send_email("%s 应用申请上线，请创建数据库账户" % app.app_code, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))

            fs = FlowStep.objects.get(workflow=wf, step=current_step - 1)
            FlowStepLog.objects.create(cf=cf, flow_step=fs, operator=request.user,
                                       is_passed=True, reply="已通知DBA创建数据库账户! 您欲创建的数据库名：%s" % database)
            cf.current_step = current_step
            cf.save(update_fields=['current_step'])
            res = {'code': 0, "result": "已通知DBA创建数据库账户！"}
        elif current_step == 4:
            # DBA 填写并提交数据库、账户等信息
            app_id = request.POST.get('app_id')
            app = App.objects.get(id=app_id)

            db_hostname = request.POST.get('db_hostname')
            db_port = request.POST.get('db_port')
            db_name = request.POST.get('db_name')
            db_user = request.POST.get('db_user')
            db_password = request.POST.get('db_password')

            cfas = list()
            cfas.append(CommonFlowArg(cf=cf, arg='db_hostname', value=db_hostname))
            cfas.append(CommonFlowArg(cf=cf, arg='db_port', value=db_port))
            cfas.append(CommonFlowArg(cf=cf, arg='db_name', value=db_name))
            cfas.append(CommonFlowArg(cf=cf, arg='db_user', value=db_user))
            cfas.append(CommonFlowArg(cf=cf, arg='db_password', value=db_password))
            CommonFlowArg.objects.bulk_create(cfas)

            next_fas = FlowStep.objects.get(workflow=wf, step=current_step + 1)
            mail_to = [u.email for u in next_fas.group.user_set.all()]
            mail_cc = [cf.applicant.email]
            mail_cc.extend([email for email in app.primary.split(",") + app.secondary.split(",")])
            mail_cont = """
            应用名：{0}
            端口：{1}
            描述：{2}
            数据库Ip：{3}
            数据库端口：{4}
            数据库名：{5}
            数据库用户：{6}
            数据库密码（已加密）：{7}
            工单地址：{8}{9}
            """.format(app.app_code, app.tomcat_port, app.comment, db_hostname, db_port, db_name, db_user, db_password,
                       ROOT_URL, reverse_lazy('workflow:flow-app-apply-detail', kwargs={'flow_id': int(flow_id)}))
            MailSender().send_email("%s 应用申请上线，请添加数据库账户" % app.app_code, mail_cont,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))

            fas = FlowStep.objects.get(workflow=wf, step=current_step)
            FlowStepLog.objects.create(cf=cf, flow_step=fas, operator=request.user,
                                       is_passed=True, reply=mail_cont)
            cf.current_step = current_step
            cf.save(update_fields=['current_step'])
            res = {'code': 0, "result": "已将数据库账户信息通知运维！"}
        elif current_step == 5:
            app_id = request.POST.get('app_id')
            app = App.objects.get(id=app_id)

            mail_to = [cf.applicant.email]
            for email in app.primary.split(",") + app.secondary.split(","):
                mail_to.append(email)
            fas = FlowStep.objects.get(workflow=wf, step=current_step)
            mail_cc = [u.email for u in fas.group.user_set.all()]

            MailSender().send_email("%s 应用创建完毕，可进行发布操作" % app.app_code, cf.content,
                                    list_to_addr=list(set(mail_to)),
                                    list_cc_addr=list(set(mail_cc)))

            cf.status = 'end'
            cf.current_step = current_step
            cf.save(update_fields=['status', 'current_step'])
            res = {'code': 0, "result": "应用创建完成，已通知申请人可进行发布！"}
        else:
            res = {'code': 1, "errmsg": "非法调用！"}
        return self.render_json_response(res)

# -*- coding: utf-8 -*-
import datetime
import re
import traceback
from django.shortcuts import render, get_object_or_404
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, Max
from django.http import QueryDict, JsonResponse

from common.mixins import JSONResponseMixin
from common.utils.magicbox_api import get_user_detail_from_mb
from cmdb.utils.jenkins_api import build_job
from cmdb.utils.wex_api import application_update
from cmdb.utils.gitlib import get_gitlib_group_list
from cmdb.models.business import BizMgtDept, Process, App
from cmdb.models.asset import Server, Nic
from cmdb.forms import BizMgtDeptForm, AppForm


class BizDeptView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_business_view'
    template_name = "cmdb/biz_mgt_dept.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': '业务部门'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class BizDeptListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_business_view'

    def get(self, request, **kwargs):
        node_id = request.GET.get("node_id", None)
        result = list()
        if node_id == '0':
            # 当 node_id 等于0时，直接返回 业务部门和App信息，用于初始化树状展示
            for o in BizMgtDept.objects.all():
                result.append({'id': o.id, 'name': o.dept_name, 'parent_id': o.parent_id})
            for o in App.objects.all():
                result.append({
                    'id': 'a' + str(o.id),
                    'name': '{}({},{})'.format(o.app_code, str(o.tomcat_port), o.app_name),
                    'parent_id': o.biz_mgt_dept.id
                })
            return self.render_json_response(result)
        elif node_id is None:
            obj_list = BizMgtDept.objects.get_queryset()
        else:
            obj_list = BizMgtDept.objects.filter(id=node_id)

        for o in obj_list:
            result.append({'id': o.id, 'name': o.dept_name, 'parent_id': o.parent_id})
        return self.render_json_response(result)

    def post(self, request):
        if not request.user.has_perm('auth.perm_cmdb_business_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        form = BizMgtDeptForm(request.POST)
        if form.is_valid():
            form.save()
            res = {'code': 0, 'result': '添加成功！'}
        else:
            # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
            res = {'code': 1, 'errmsg': form.errors}
        return self.render_json_response(res)


class BizDeptDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_business_view', 'perm_cmdb_business_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            p = BizMgtDept.objects.get(pk=pk)
            value = {'id': p.id, 'dept_name': p.dept_name, 'parent_id': p.parent_id, 'comment': p.comment}
            res = {'code': 0, 'result': value}
        except BizMgtDept.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        p = get_object_or_404(BizMgtDept, pk=pk)
        form = BizMgtDeptForm(QueryDict(request.body), instance=p)
        if form.is_valid():
            form.save()
            res = {"code": 0, "result": "更新成功"}
        else:
            res = {"code": 1, "errmsg": form.errors}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = BizMgtDept.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)


class AppView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_business_view'
    template_name = "cmdb/app.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': '应用'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


def get_total_dept_child_node_id(node_id):
    node_id_list = [node_id]
    dept_list = BizMgtDept.objects.filter(parent_id=node_id)
    for dept in dept_list:
            node_id_list.extend(get_total_dept_child_node_id(dept.id))
    return node_id_list


class AppListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_business_view'

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset'))
        sort_order = request.GET.get("sortOrder", 'desc')
        sort_name = request.GET.get("sortName", 'tomcat_port')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name
        status = request.GET.get("status", 1)

        dept_id = request.GET.get("dept_id", None)
        if dept_id is None:
            obj_list = App.objects.filter(status=status).order_by(sort_name)
        elif re.match(r'a\d+', dept_id):
            # dept_id 为 a+数字，则说明点击的是App
            obj_list = App.objects.filter(id=dept_id[1:]).order_by(sort_name)
        else:
            # dept_id 遍历其所有子部门，列出该部门以及包含子部门所有app
            sub_dept_ids = get_total_dept_child_node_id(dept_id)
            obj_list = App.objects.filter(biz_mgt_dept__id__in=sub_dept_ids, status=status).order_by(sort_name)

        search = request.GET.get("search", None)
        if search is not None:
            obj_list = obj_list.filter(Q(app_code__contains=search) | Q(app_name__contains=search) |
                                       Q(tomcat_port__contains=search) | Q(primary__contains=search) |
                                       Q(secondary__contains=search) | Q(comment__contains=search)).distinct()

        res = [{
            'id': o.id, 'app_code': o.app_code, 'app_name': o.app_name, 'app_type': o.app_type,
            'importance': o.importance, 'jdk': o.jdk, 'tomcat_port': o.tomcat_port, 'scm_url': o.scm_url,
            'domain_name': o.domain_name, 'primary': o.primary, 'secondary': o.secondary,
            'comment': o.comment, 'status': o.get_status_display()
        } for o in obj_list[offset:(offset + limit)]]
        return self.render_json_response({"total": obj_list.count(), "rows": res})

    def post(self, request, **kwargs):
        post_data = request.POST.copy()
        dept_id = post_data.pop('dept_id')
        status = int(post_data.get('status'))
        if status == 0:
            # 申请新建应用，需分配一个新端口
            app_code, scm_url = post_data.get('app_code'), post_data.get('scm_url')
            if '/' + app_code + '.git' not in scm_url:
                return self.render_json_response({'code': 1, 'errmsg': '应用编码(xxx)与仓库名(xxx.git)必须相同！'})
            scm_owner = re.findall(r'\S*:(\S+)/\S+', scm_url, re.I)[0]
            if scm_owner not in get_gitlib_group_list():
                return self.render_json_response({'code': 1, 'errmsg': '请将仓库移动到公共组！'})
            maximum_port = App.objects.get_queryset().aggregate(Max('tomcat_port'))
            post_data['tomcat_port'] = maximum_port['tomcat_port__max'] + 1 if maximum_port else 8080
        else:
            # 补录应用
            if not request.user.has_perm('auth.perm_cmdb_business_edit'):
                return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法补录应用！'})
        # 校验 git地址是否合法
        git_pattern = re.compile(r'^git@git\.\w+\.\S+:[a-zA-Z0-9\-]+/[a-zA-Z0-9\-]+.git')
        if not git_pattern.match(post_data['scm_url']):
            return self.render_json_response({'code': 1, 'errmsg': 'Git地址填写错误！'})
        # 校验第一、第二负责人 是否真实存在
        email_pattern = re.compile(r'^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,4}$')
        email_primary = post_data['primary']
        email_secondary = ",".join(request.POST.getlist('secondary', []))
        for email in email_primary.split(",") + email_secondary.split(","):
            if email_pattern.match(email):
                if get_user_detail_from_mb(email) is None:
                    return self.render_json_response({'code': 1, 'errmsg': '第一、第二负责人未找到，请再次确认！'})
            else:
                return self.render_json_response({'code': 1, 'errmsg': '请正确填写第一、第二负责人的邮箱！'})

        form = AppForm(post_data)
        if form.is_valid():
            app = form.save(commit=False)
            bgd = BizMgtDept.objects.get(id=dept_id[0])
            if bgd.id < 3:
                return self.render_json_response({'code': 1, 'errmsg': '请勿选择根部门！'})
            app.biz_mgt_dept = bgd
            if Process.objects.filter(name='java').exists():
                app.process = Process.objects.get(name='java')
            app.applicant = request.user.username
            app.save()
            if status == 0:
                res = {'code': 0, 'id': app.id, 'result': '新应用申请已提交，请等待管理员审核！'}
            else:
                res = {'code': 0, 'result': '添加成功！'}
        else:
            # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
            res = {'code': 1, 'errmsg': form.errors}
        return self.render_json_response(res)


class AppDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_business_view'

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            p = App.objects.get(pk=pk)
            value = {'id': p.id, 'app_code': p.app_code, 'app_name': p.app_name, 'app_type': p.app_type,
                     'importance': p.importance, 'tomcat_port': p.tomcat_port, 'biz_mgt_dept': p.biz_mgt_dept.dept_name,
                     'dept_id': p.biz_mgt_dept.id, 'scm_url': p.scm_url, 'domain_name': p.domain_name,
                     'primary': p.primary, 'secondary': p.secondary,
                     'modify_date': p.modify_date, 'parent_id': p.parent_id, 'comment': p.comment}
            res = {'code': 0, 'result': value}
        except App.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        p = get_object_or_404(App, pk=pk)
        if p.status is True:
            # 当status为False时，表示该应用还在申请阶段，允许用户修改部分属性
            if not request.user.has_perm('auth.perm_cmdb_business_edit'):
                return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法修改！'})
        post_data = QueryDict(request.body).dict()
        # 应用下线
        if "action" in post_data and post_data.pop("action") == "off":
            app = App.objects.get(pk=pk)
            if Server.objects.filter(app=app).exists():
                res = {"code": 1, "errmsg": "请先去服务器移除该应用！"}
            else:
                # for s in Server.objects.filter(app=app):
                #     s.app.remove(app)
                for s in Server.objects.filter(pre_app=app):
                    s.pre_app.remove(app)
                App.objects.filter(pk=pk).update(status=3)
                res = {"code": 0, "result": "下线成功"}
            return JsonResponse(res, safe=True)

        dept_id = post_data.pop('dept_id')
        # 校验 git地址是否合法
        git_pattern = re.compile(r'^git@git\.\w+\.\S+:[a-zA-Z0-9\-]+/[a-zA-Z0-9\-]+.git')
        if not git_pattern.match(post_data['scm_url']):
            return self.render_json_response({'code': 1, 'errmsg': 'Git地址填写错误！'})
        # 校验第一、第二负责人 是否真实存在
        email_pattern = re.compile(r'^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,4}$')
        email_primary = post_data['primary']
        email_secondary = post_data['secondary']
        for email in email_primary.split(",") + email_secondary.split(","):
            if email_pattern.match(email):
                if get_user_detail_from_mb(email) is None:
                    return self.render_json_response({'code': 1, 'errmsg': '第一、第二负责人未找到，请再次确认！'})
            else:
                return self.render_json_response({'code': 1, 'errmsg': '请正确填写第一、第二负责人的邮箱！'})
        post_data['status'] = p.status
        form = AppForm(post_data, instance=p)
        if form.is_valid():
            app = form.save(commit=False)
            app.biz_mgt_dept = BizMgtDept.objects.get(id=dept_id)
            app.save()
            application_update(post_data)
            res = {"code": 0, "result": "更新成功"}
        else:
            res = {"code": 1, "errmsg": form.errors}
        return JsonResponse(res, safe=True)

    def delete(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            if request.user.has_perm('auth.perm_cmdb_business_edit'):
                obj = App.objects.filter(pk=pk).delete()
            elif App.objects.filter(pk=pk, status=0).exists():
                obj = App.objects.filter(pk=pk).delete()
            else:
                # 当用户没有应用编辑，但想要删除非"待创建应用"时，返回报错
                res = {"code": 1, "result": "您无删除权限！"}
                return JsonResponse(res, safe=True)
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)


class AppAudit(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_business_view'
    template_name = "cmdb/app_audit.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': '待创建新应用'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AppAuditListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_business_view'

    def get(self, request, **kwargs):
        if request.user.has_perm('auth.perm_cmdb_business_edit'):
            obj_list = App.objects.filter(status=0)
        else:
            obj_list = App.objects.filter(status=0, applicant=request.user.username)
        # search = request.GET.get("search", None)
        # if search is not None:
        #     obj_list = obj_list.filter(Q(app_code__contains=search) | Q(app_name__contains=search) |
        #                                Q(tomcat_port__contains=search) | Q(primary__contains=search) |
        #                                Q(secondary__contains=search) | Q(scm_url__contains=search) |
        #                                Q(domain_name__contains=search) | Q(comment__contains=search))

        res = obj_list.values('id', 'app_code', 'app_name', 'app_type', 'importance', 'scm_url', 'domain_name',
                              'tomcat_port', 'primary', 'secondary', 'comment')
        return self.render_json_response([o for o in res])

    def post(self, request):
        if not request.user.has_perm('auth.perm_cmdb_business_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        try:
            app_id = request.POST.get('app_id')
            test_host_list = request.POST.getlist('test_host')

            app = App.objects.get(id=app_id)
            # ip_list = {'dailytest': '192.168.21.98', 'wdaitest': '172.20.100.173', 'prod': '172.20.1.48'}
            ip_list = {'wdaitest': '172.20.100.173', 'prod': '172.20.1.48'}
            if test_host_list:
                test_host = Server.objects.get(id=test_host_list[0])
                if re.match(r'^mdc-yunwei-k8s-.+', test_host.hostname, re.I):
                    ip_list['wdaitest_k8s'] = '0.0.0.0'
                for nic in Nic.objects.filter(server=test_host):
                    for ip in nic.ip.all():
                        ip_list['wdaitest'] = ip.ip
            for k in sorted(ip_list.keys(), reverse=True):
                svn_json = {
                    "JDK_VERSION": "JDK1.8" if app.app_type == "jar" else "JDK1.7",
                    "LANGUAGE": "java",
                    "DESCRIPTION": app.comment,
                    "PACKAGE_TYPE": app.app_type,
                    "GIT_URL": app.scm_url,
                    "ENV": k,
                    "DEPLOY_IP": ip_list[k],
                    "TOMCAT_DIR": "/data/{}-{}".format(app.tomcat_port, app.app_code),
                    "OWNER": app.primary,
                }
                build_job('create_java_job', svn_json)
            app.status = 1
            app.save(update_fields=['status'])
            res = {'code': 0, 'result': '创建成功！'}
        except Exception as e:
            print(traceback.print_exc())
            res = {'code': 1, 'errmsg': str(e)}
        return self.render_json_response(res)

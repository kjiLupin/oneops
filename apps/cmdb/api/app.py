# -*- coding: utf-8 -*-
import traceback
import re
import os
import subprocess
import datetime
import simplejson as json
import xlrd
from openpyxl import Workbook
from django.db.models import Q
from django.http import QueryDict, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from wsgiref.util import FileWrapper
from django.views.generic import View
from cmdb.models.business import BizMgtDept, Process, App
from cmdb.models.asset import Server, Nic
from common.utils.base import BASE_DIR
from common.utils.magicbox_api import get_user_detail_from_mb
from common.mixins import RPCIpWhiteMixin, JSONResponseMixin
from cmdb.utils.wex_api import application_update


@method_decorator(csrf_exempt, name='dispatch')
class ProcessListAPIView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            result = [{"name": p.name, "version_arg": p.version_arg} for p in Process.objects.all()]
            res = {'code': 0, 'result': result}
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)


@method_decorator(csrf_exempt, name='dispatch')
class AppTemplateView(PermissionRequiredMixin, JSONResponseMixin, View):
    permission_required = 'auth.perm_cmdb_business_edit'

    def get(self, request, *args, **kwargs):
        try:
            filename = 'app_template.xls'
            export_file = os.path.join(BASE_DIR, 'cmdb', 'docs', filename)
            if os.path.isfile(export_file):
                wrapper = FileWrapper(open(export_file, "rb"))
                response = HttpResponse(wrapper, content_type='application/vnd.ms-excel')
                response['Content-Length'] = os.path.getsize(export_file)
                response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
                return response
            else:
                return HttpResponse('模板文件不存在！')
        except Exception as e:
            return HttpResponse('模板文件下载失败：' + str(e))

    def post(self, request, *args, **kwargs):
        import_files = request.FILES.getlist('files', None)
        if len(import_files) == 0:
            return self.render_json_response({'code': 1, 'msg': '文件为空，或上传错误！'})
        date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        file_dir = os.path.join(BASE_DIR, 'cmdb', 'docs')
        created, updated, failed = [], [], []
        attr = ['id', 'app_name', 'app_code', 'importance', 'app_type', 'tomcat_port', 'biz_mgt_dept',
                'scm_url', 'domain_name', 'primary', 'secondary', 'comment']
        for im_file in import_files:
            file_name = im_file.name
            file_path = os.path.join(file_dir, request.user.username + '_' + date_now + '_' + file_name)
            with open(file_path, 'wb') as f:
                for chunk in im_file.chunks():
                    f.write(chunk)
            if not os.path.isfile(file_path):
                failed.append('{}：文件为空，或上传错误！'.format(file_name))
                continue
            if not re.match(r'application/vnd\.(ms-excel|ms-office)',
                            subprocess.getoutput('file -b --mime-type ' + file_path)):
                failed.append('{}：请上传excel文件!'.format(im_file))
                continue

            data = xlrd.open_workbook(file_path)
            data.sheet_names()
            sheet = data.sheet_by_index(0)
            for i in range(2, sheet.nrows):
                row = list()
                for j in range(sheet.ncols):
                    # ctype：0 empty, 1 string, 2 number, 3 date, 4 boolean, 5 error
                    ctype = sheet.cell(i, j).ctype
                    cell = sheet.cell_value(i, j)
                    if ctype == 1:
                        cell = cell.strip()
                    elif ctype == 2 and cell % 1 == 0:  # 如果是整形
                        cell = int(cell)
                    elif ctype == 3:  # 转成datetime对象
                        date = datetime.datetime(*xlrd.xldate_as_tuple(cell, 0))
                        cell = date.strftime('%Y-%m-%d %H:%M:%S')
                    elif ctype == 4:
                        cell = True if cell == 1 else False
                    row.append(cell)
                dict_raw = dict(zip(attr, row))
                _id = dict_raw.pop('id')
                if not _id and not (dict_raw['app_code'] and dict_raw['app_type']):
                    # id列值为空，则说明是新增。则应用编码、应用类型是必填项
                    failed.append('{} {}行：应用编码、应用类型是必填项'.format(file_name, str(i + 1)))
                    continue
                try:
                    biz_mgt_dept = dict_raw.pop('biz_mgt_dept')
                    if BizMgtDept.objects.filter(dept_name=biz_mgt_dept).exists():
                        dict_raw['biz_mgt_dept'] = BizMgtDept.objects.get(dept_name=biz_mgt_dept)

                    # 批量导入应用，默认视为这些应用之前已经创建过
                    dict_raw['status'] = True
                    if not _id:
                        # id列值为空，则说明是新增记录
                        App.objects.create(**dict_raw)
                        created.append('{} {}行：{}'.format(file_name, str(i + 1), dict_raw['app_code']))
                    else:
                        # id列不为空，则更新id为它的记录
                        if App.objects.filter(id=_id).exists():
                            App.objects.filter(id=_id).update(**dict_raw)
                            updated.append('{} {}行：{}'.format(file_name, str(i + 1), dict_raw['app_code']))
                        else:
                            failed.append('{} {}行：该id {}在数据库中未找到。'.format(file_name, str(i + 1), _id))
                except Exception as e:
                    print(traceback.print_exc())
                    failed.append('{} {}行：{}。'.format(file_name, str(i + 1), str(e)))
        data = {
            'code': 0,
            'created': created,
            'created_info': 'Created {}'.format(len(created)),
            'updated': updated,
            'updated_info': 'Updated {}'.format(len(updated)),
            'failed': failed,
            'failed_info': 'Failed {}'.format(len(failed)),
            'msg': 'Created: {}. Updated: {}, Error: {}'.format(
                len(created), len(updated), len(failed))
        }
        return self.render_json_response(data)


# 导出所有 app 信息为Excel
class AppExportView(PermissionRequiredMixin, JSONResponseMixin, View):
    permission_required = 'auth.perm_cmdb_business_view'

    def get(self, request, *args, **kwargs):
        try:
            filename = 'app_total.xlsx'
            export_file = os.path.join(BASE_DIR, 'logs', filename)
            if os.path.exists(export_file):
                os.remove(export_file)

            wb = Workbook()
            ws = wb.active
            ws.append(["名称", "编码", "端口", "类型", "重要性", "域名", "部门", "第一负责人", "第二负责人", "备注", "状态"])
            for app in App.objects.all():
                try:
                    ws.append([app.app_name, app.app_code, app.tomcat_port, app.app_type, app.importance,
                               app.domain_name, app.biz_mgt_dept.dept_name, app.primary, app.secondary,
                               app.comment, app.status])
                except:
                    print(app.app_name, app.app_code, app.tomcat_port, app.app_type, app.importance,
                          app.domain_name, app.biz_mgt_dept.dept_name, app.primary, app.secondary,
                          app.comment, app.status)
                    traceback.print_exc()
            wb.save(export_file)
            wrapper = FileWrapper(open(export_file, "rb"))
            response = HttpResponse(wrapper, content_type='application/vnd.ms-excel')
            response['Content-Length'] = os.path.getsize(export_file)
            response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
            return response
        except Exception as e:
            traceback.print_exc()
            return HttpResponse('文件导出失败：' + str(e))


@method_decorator(csrf_exempt, name='dispatch')
class AppListAPIView(JSONResponseMixin, RPCIpWhiteMixin, View):
    """
    新增应用接口：提供给其他系统远程调用
    """
    url_name = 'api-app-list'

    def get(self, request, *args, **kwargs):
        try:
            unix_ts = request.GET.get('timestamp', None)
            if unix_ts:
                date = datetime.datetime.fromtimestamp(int(unix_ts))
                app_list = App.objects.filter(modify_date__gte=date).order_by('-tomcat_port')
            else:
                app_list = App.objects.get_queryset().order_by('-tomcat_port')
            result = list()
            for app in app_list:
                prod, beta, pre, test = list(), list(), list(), list()
                obj_list = Server.objects.exclude(status__in=['deleted', 'ots']).filter(app=app)
                for obj in obj_list:
                    nic_list = Nic.objects.filter(server=obj)
                    ips = [ip.ip for nic in nic_list for ip in nic.ip.all()]
                    if obj.app_env == "prod":
                        prod.append({"hn": obj.hostname, "ip": ips})
                    elif obj.app_env == "beta":
                        beta.append({"hn": obj.hostname, "ip": ips})
                    elif obj.app_env == "pre":
                        pre.append({"hn": obj.hostname, "ip": ips})
                    elif obj.app_env == "test":
                        test.append({"hn": obj.hostname, "ip": ips})
                # for pod in Pod.objects.filter(app=app):
                #     if pod.app_env == "test":
                #         test.append({"hn": pod.hostname, "ip": pod.ip})
                result.append(
                    {"app_code": app.app_code, "host": {"prod": prod, "beta": beta, "pre": pre, "test": test}})
            res = {'code': 0, 'result': result}
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)

    def post(self, request, *args, **kwargs):
        try:
            post = json.loads(request.body)['params']
            biz_mgt_dept = BizMgtDept.objects.get(id=1)
            dept_name = post.pop('biz_mgt_dept_name').split(',')
            parent = BizMgtDept.objects.filter(dept_name=dept_name[0])
            if parent:
                bgd = BizMgtDept.objects.filter(dept_name=dept_name[1], parent_id=parent[0].id)
                if bgd:
                    biz_mgt_dept = bgd[0]
            App.objects.create(
                app_code=post['biz_code'],
                app_name=post['biz_name'],
                app_type=post['biz_type'],
                importance=post['importance'],
                tomcat_port=post['tomcat_port'],
                biz_mgt_dept=biz_mgt_dept,
                primary=post['primary'],
                secondary=post['secondary'],
                comment=post['comment']
            )
            res = {'code': 0, 'result': '添加成功！'}
        except Exception as e:
            # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
            res = {'code': 1, 'errmsg': str(e)}
        return self.render_json_response(res)


@method_decorator(csrf_exempt, name='dispatch')
class AppDetailAPIView(JSONResponseMixin, RPCIpWhiteMixin, View):
    url_name = 'api-app-detail'

    def get(self, request, **kwargs):
        code = kwargs.get('code')
        ret_format = request.GET.get('format', None)
        try:
            prod, beta, pre, test = list(), list(), list(), list()
            app = App.objects.get(app_code=code)
            obj_list = Server.objects.exclude(status__in=['deleted', 'ots']).filter(app=app)
            for obj in obj_list:
                nic_list = Nic.objects.filter(server=obj)
                ips = [ip.ip for nic in nic_list for ip in nic.ip.all()]
                if obj.app_env == "prod":
                    prod.append({"hn": obj.hostname, "ip": ips})
                elif obj.app_env == "beta":
                    beta.append({"hn": obj.hostname, "ip": ips})
                elif obj.app_env == "pre":
                    pre.append({"hn": obj.hostname, "ip": ips})
                elif obj.app_env == "test":
                    test.append({"hn": obj.hostname, "ip": ips})
            # for pod in Pod.objects.filter(app=app):
            #     if pod.app_env == "test":
            #         test.append({"hn": pod.hostname, "ip": pod.ip})

            if ret_format == "text":
                res = 'app_name {}\napp_code {}\ntype {}\nport {}\njdk {}\nxms {}\nxmx {}\nscm_url {}\ndomain_name {}\n' \
                      'domain_name_test {}\ndept_name {}\nimportance {}\nprimary {}\nsecondary {}\ncomment {}\n' \
                      'prod {}\nbeta {}\npre {}\ntest {}\n'.format(app.app_name, app.app_code, app.app_type,
                                                                   app.tomcat_port, app.jdk, app.xms, app.xmx,
                                                                   app.scm_url, app.domain_name, app.domain_name_test,
                                                                   app.biz_mgt_dept.dept_name, app.importance,
                                                                   app.primary, app.secondary, app.comment,
                                                                   " ".join([" ".join(p["ip"]) for p in prod]),
                                                                   " ".join([" ".join(p["ip"]) for p in beta]),
                                                                   " ".join([" ".join(p["ip"]) for p in pre]),
                                                                   " ".join([" ".join(p["ip"]) for p in test]),)
                return HttpResponse(res)
            else:
                app_info = {
                    "app_name": app.app_name,
                    "app_code": app.app_code,
                    "type": app.app_type,
                    "port": app.tomcat_port,
                    "jdk": app.jdk,
                    "xms": app.xms,
                    "xmx": app.xmx,
                    "scm_url": app.scm_url,
                    "domain_name": app.domain_name,
                    "domain_name_test": app.domain_name_test,
                    "dept_name": app.biz_mgt_dept.dept_name,
                    "importance": app.importance,
                    "primary": app.primary,
                    "secondary": app.secondary,
                    "comment": app.comment,
                    "prod": prod,
                    "beta": beta,
                    "pre": pre,
                    "test": test
                }
                res = {'code': 0, 'result': app_info}
        except App.DoesNotExist:
            res = {'code': 1, 'errmsg': 'App未找到！'}
        return self.render_json_response(res)

    # 修改 app 属性
    def post(self, request, **kwargs):
        app_code = kwargs.get('code')
        try:
            app = App.objects.get(app_code=app_code)
            post_data = json.loads(request.body)
            if post_data.get('type', None):
                post_data['app_type'] = post_data.pop('type')
            if post_data.get('port', None):
                post_data['tomcat_port'] = post_data.pop('port')
            email_primary = post_data.get('primary', '')
            email_secondary = post_data.get('secondary', '')

            # 校验第一、第二负责人 是否真实存在
            email_pattern = re.compile(r'^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,4}$')
            for email in email_primary.split(",") + email_secondary.split(","):
                if email_pattern.match(email):
                    if get_user_detail_from_mb(email) is None:
                        return self.render_json_response({'code': 1, 'errmsg': '第一、第二负责人未找到，请再次确认！'})
                else:
                    return self.render_json_response({'code': 1, 'errmsg': '请正确填写第一、第二负责人的邮箱！'})

            App.objects.filter(app_code=app_code).update(**post_data)
            res = {'code': 0, 'result': '更新成功'}
        except App.DoesNotExist:
            res = {'code': 1, 'errmsg': 'App未找到！'}
        return self.render_json_response(res)


class AppPortDetailAPIView(JSONResponseMixin, RPCIpWhiteMixin, View):
    url_name = 'api-app-port-detail'

    # 根据 app 端口获取 app 信息
    def get(self, request, **kwargs):
        tomcat_port = kwargs.get('port')
        try:
            results = list()
            for app in App.objects.filter(tomcat_port=tomcat_port):
                prod, beta, pre, test = list(), list(), list(), list()
                obj_list = Server.objects.exclude(status__in=['deleted', 'ots']).filter(app=app)
                for obj in obj_list:
                    nic_list = Nic.objects.filter(server=obj)
                    ips = [ip.ip for nic in nic_list for ip in nic.ip.all()]
                    if obj.app_env == "prod":
                        prod.append({"hn": obj.hostname, "ip": ips})
                    elif obj.app_env == "beta":
                        beta.append({"hn": obj.hostname, "ip": ips})
                    elif obj.app_env == "pre":
                        pre.append({"hn": obj.hostname, "ip": ips})
                    elif obj.app_env == "test":
                        test.append({"hn": obj.hostname, "ip": ips})
                # for pod in Pod.objects.filter(app=app):
                #     if pod.app_env == "test":
                #         test.append({"hn": pod.hostname, "ip": pod.ip})
                results.append({
                    "app_name": app.app_name,
                    "app_code": app.app_code,
                    "type": app.app_type,
                    "port": app.tomcat_port,
                    "jdk": app.jdk,
                    "scm_url": app.scm_url,
                    "domain_name": app.domain_name,
                    "dept_name": app.biz_mgt_dept.dept_name,
                    "importance": app.importance,
                    "primary": app.primary,
                    "secondary": app.secondary,
                    "prod": prod,
                    "beta": beta,
                    "pre": pre,
                    "test": test
                })
            res = {'code': 0, 'result': results}
        except App.DoesNotExist:
            res = {'code': 1, 'errmsg': 'App未找到！'}
        return self.render_json_response(res)


@method_decorator(csrf_exempt, name='dispatch')
class AppGitDetailAPIView(JSONResponseMixin, RPCIpWhiteMixin, View):
    url_name = 'api-app-git-detail'

    def get(self, request, **kwargs):
        scm_url = kwargs.get('url')
        try:
            result = list()
            for app in App.objects.filter(scm_url=scm_url):
                result.append({
                    "app_name": app.app_name,
                    "app_code": app.app_code,
                    "type": app.app_type,
                    "port": app.tomcat_port,
                    "jdk": app.jdk,
                    "scm_url": app.scm_url,
                    "domain_name": app.domain_name,
                    "dept_name": app.biz_mgt_dept.dept_name,
                    "importance": app.importance,
                    "primary": app.primary,
                    "secondary": app.secondary,
                    "comment": app.comment
                })
            res = {'code': 0, 'result': result}
        except App.DoesNotExist:
            res = {'code': 1, 'errmsg': 'App未找到！'}
        return self.render_json_response(res)

    # 根据 app git获取 app 信息
    def post(self, request, **kwargs):
        scm_url = kwargs.get('url')
        post_data = json.loads(request.body)
        email_primary = post_data.pop('primary', None)
        email_secondary = post_data.pop('secondary', None)

        # 校验第一、第二负责人 是否真实存在
        email_pattern = re.compile(r'^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,4}$')
        for email in email_primary.split(",") + email_secondary.split(","):
            if email_pattern.match(email):
                if get_user_detail_from_mb(email) is None:
                    return self.render_json_response({'code': 1, 'errmsg': '第一、第二负责人未找到，请再次确认！'})
            else:
                return self.render_json_response({'code': 1, 'errmsg': '请正确填写第一、第二负责人的邮箱！'})

        if App.objects.filter(scm_url=scm_url).exists():
            app_codes = list()
            for app in App.objects.filter(scm_url=scm_url):
                app_codes.append(app.app_code)
                if email_primary:
                    app.primary = email_primary
                if email_secondary:
                    app.secondary = email_secondary
                app.save(update_fields=['primary', 'secondary'])
                application_update({"app_code": app.app_code, "primary": email_primary, "secondary": email_secondary})
            res = {'code': 0, 'result': '%s 更新成功' % ','.join(app_codes)}
        else:
            res = {'code': 1, 'errmsg': 'App未找到！'}
        return self.render_json_response(res)


class AppPresortServerAPIView(PermissionRequiredMixin, JSONResponseMixin, View):
    permission_required = 'auth.perm_cmdb_business_view'

    def get(self, request, *args, **kwargs):
        # 根据应用获取可分配的 prod、beta、pre、test主机
        try:
            app_id = kwargs.get('id')
            app = App.objects.get(id=app_id)
            # 获取该应用所在 大部门，查找该大部门下的闲余主机
            if app.biz_mgt_dept.parent_id == 2:
                l2_dept = app.biz_mgt_dept
            else:
                # 因为部门树最深只有3层，所以往上一层就可以取到 大部门
                parent_dept_id = app.biz_mgt_dept.parent_id
                l2_dept = BizMgtDept.objects.get(id=parent_dept_id)
            prod_host, beta_host, pre_host, test_host = list(), list(), list(), list()
            if app.importance == "a":
                # 核心应用，则部署在包含 W1 主机名的主机，每台主机可部署4个Tomcat
                for s in Server.objects.exclude(status__in=['deleted', 'ots']).filter(department=l2_dept,
                                                                                      app_env='prod',
                                                                                      hostname__contains="-prod-W1-"):
                    installed_app_num = s.app.count() + s.pre_app.count()
                    if installed_app_num < 4:
                        prod_host.append({"id": s.id, "hn": '{}({})'.format(s.hostname, str(installed_app_num))})
                for s in Server.objects.exclude(status__in=['deleted', 'ots']).filter(department=l2_dept,
                                                                                      app_env='beta',
                                                                                      hostname__contains="-prod-beta-W1-"):
                    installed_app_num = s.app.count() + s.pre_app.count()
                    if installed_app_num < 4:
                        beta_host.append({"id": s.id, "hn": '{}({})'.format(s.hostname, str(installed_app_num))})

            else:
                # 普通应用，则部署在包含 W2 主机名的主机，每台主机可部署6个Tomcat
                for s in Server.objects.filter(department=l2_dept, app_env='prod').filter(Q(hostname__contains="-prod-W2-") |
                                                                                          Q(hostname__contains="-prod-o1-")):
                    installed_app_num = s.app.count() + s.pre_app.count()
                    if installed_app_num < 6:
                        prod_host.append({"id": s.id, "hn": '{}({})'.format(s.hostname, str(installed_app_num))})
                for s in Server.objects.exclude(status__in=['deleted', 'ots']).filter(department=l2_dept,
                                                                                      app_env='beta',
                                                                                      hostname__contains="-prod-beta-W2-"):
                    installed_app_num = s.app.count() + s.pre_app.count()
                    if installed_app_num < 6:
                        beta_host.append({"id": s.id, "hn": '{}({})'.format(s.hostname, str(installed_app_num))})

            for s in Server.objects.exclude(status__in=['deleted', 'ots']).filter(department=l2_dept, app_env='pre',
                                                                                  hostname__contains="-pre-"):
                installed_app_num = s.app.count() + s.pre_app.count()
                pre_host.append({"id": s.id, "hn": '{}({})'.format(s.hostname, str(installed_app_num))})

            # wry-stable-weit02/wry-stable-weit19/wry-stable-weit20 特殊添加 @包海涛
            for s in Server.objects.exclude(status__in=['deleted', 'ots']).filter(app_env='test').filter(
                                            Q(hostname__startswith="mdc-stable-app-") |
                                            Q(hostname='wry-stable-weit02') |
                                    Q(hostname='wry-stable-weit19') |
                            Q(hostname='wry-stable-weit20') |
                            Q(hostname__startswith='mdc-yunwei-k8s-node')).distinct():
                installed_app_num = s.app.count() + s.pre_app.count()
                test_host.append({"id": s.id, "hn": '{}({})'.format(s.hostname, str(installed_app_num))})
            # prod_host, beta_host = [{"id": 1, "hn": "h1"}, {"id": 2, "hn": "h2"}], [{"id": 8, "hn": "h9"}]
            # pre_host, test_host = [{"id": 3, "hn": "h3"}, {"id": 4, "hn": "h4"}], [{"id": 5, "hn": "h5"}]
            result = {"prod_host": prod_host, "beta_host": beta_host, "pre_host": pre_host, "test_host": test_host}
            return self.render_json_response({'code': 0, 'result': result})
        except Exception as e:
            return self.render_json_response({'code': 1, 'errmsg': str(e)})

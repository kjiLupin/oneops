# -*- coding: utf-8 -*-
import uuid
import requests
import simplejson as json
from pprint import pprint
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from common.mixins import JSONResponseMixin
from common.utils.zabbix_api import get_access_token, get_host_ids, get_monitor_item_ids, update_monitor_item
from cmdb.models.asset import Server
from cmdb.models.business import App, BizMgtDept
from cmdb.views.ip import get_ips_by_server_id
from workflow.models import CommonFlow, CommonFlowArg
from ssh.models.host_user import HostUserAsset

from job.tasks.ansible_api import AnsibleAPI


class AnsibleHostsGroupInitAPIView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            flow_id = kwargs.get('flow_id')
            cf = CommonFlow.objects.get(id=flow_id)
            app_id = CommonFlowArg.objects.get(cf=cf, arg='app_id').value
            app = App.objects.get(id=app_id)
            dept = app.biz_mgt_dept
            while True:
                if dept.parent_id == 2:
                    dept_code = dept.dept_code
                    break
                else:
                    dept = BizMgtDept.objects.get(id=dept.parent_id)
            pre_host = [s.hostname for s in Server.objects.filter(pre_app=app, app_env='pre')]
            beta_host = [s.hostname for s in Server.objects.filter(pre_app=app, app_env='beta')]
            prod_host = [s.hostname for s in Server.objects.filter(pre_app=app, app_env='prod')]
            result = '''[{0}-{1}-pre]\n{2}\n[{0}-{1}-beta]\n{3}\n[{0}-{1}-prod]\n{4}\n'''.format(
                dept_code, app.app_code, '\n'.join(pre_host), '\n'.join(beta_host), '\n'.join(prod_host))
            res = {'code': 0, 'result': result}
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)


class OpsProjectCreateAPIView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            flow_id = kwargs.get('flow_id')
            cf = CommonFlow.objects.get(id=flow_id)
            app_id = CommonFlowArg.objects.get(cf=cf, arg='app_id').value
            app = App.objects.get(id=app_id)
            dept = app.biz_mgt_dept
            while True:
                if dept.parent_id == 2:
                    dept_code = dept.dept_code
                    break
                else:
                    dept = BizMgtDept.objects.get(id=dept.parent_id)
            data = {
                "app_code": "prod_" + app.app_code,
                "app_type": app.app_type.upper(),
                "comment": app.comment,
                "p_script": "/jenkins/data/deploy_war.sh" if app.app_type == 'war' else "/jenkins/data/deploy_jar.sh",
                "p_tomcat": '/data/{}-{}'.format(app.tomcat_port, app.app_code),
                "p_war": app.app_code,
                "p_prehost": '{0}-{1}-pre'.format(dept_code, app.app_code),
                "p_host1": '{0}-{1}-beta'.format(dept_code, app.app_code),
                "p_host2": '{0}-{1}-prod'.format(dept_code, app.app_code)
            }
            res = {'code': 0, 'result': data}
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)

    def post(self, request, *args, **kwargs):
        try:
            post_data = request.POST.copy().dict()
            p_group = ','.join(request.POST.getlist('p_group', []))
            print(p_group, post_data)
            post_data['p_group'] = p_group
            post_data['principal'] = "1"
            post_data['p_user'] = "1"
            headers = {"Content-Type": "application/json"}
            data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "project.create2",
                "params": post_data
            }
            pprint(data)
            ret = requests.post("http://opsapi.yadoom.com/api", headers=headers, json=data)
            res = json.loads(json.loads(ret.text)['result'])
            pprint(res)
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)


class OpsRoleListAPIView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "role.getlist2",
                "params": {}
            }
            ret = requests.post("http://opsapi.yadoom.com/api", headers=headers, json=data)
            res = json.loads(ret.text)
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)


class AppOfflineCodeBackupAPIView(LoginRequiredMixin, JSONResponseMixin, View):

    def post(self, request, *args, **kwargs):
        try:
            app_id = kwargs.get('app_id')
            app = App.objects.get(id=app_id)
            for host in app.app_server.all():
                ips = get_ips_by_server_id(host.id)
                if not ips:
                    print(host.hostname, host.login_address, " 没有关联ip地址！")
                    continue
                hua = HostUserAsset.objects.filter(asset=host, host_user__username='root')
                if hua:
                    hu = hua[0].host_user
                    kwargs = {
                        'resource': list(),
                        'hosts_file': ["/data/ansible/inventory/public/hosts_all"],
                        'host_user': hu.id
                    }
                    playbook = ["/data/ansible/playbook/admin/app_offline.yml"]
                    extra_vars = {"apphost": host.login_address.split(":")[0], "app_code": app.app_code,
                                  "tomcat_port": app.tomcat_port, "app_type": app.app_type}

                    ansible_api = AnsibleAPI(0, str(uuid.uuid4()), **kwargs)
                    print(ansible_api.run_playbook(playbook, extra_vars))
                else:
                    print(host.hostname, host.login_address, " 未绑定用户为root的HostUser！")
            res = {'code': 0, 'result': '任务已提交，请再手动确认是否执行成功！'}
        except Exception as e:
            res = {'code': 1, 'result': str(e)}
        return self.render_json_response(res)


class AppOfflineDisableMonitorAPIView(LoginRequiredMixin, JSONResponseMixin, View):

    def post(self, request, *args, **kwargs):
        try:
            app_code = kwargs.get('app_code')
            app = App.objects.get(app_code=app_code)
            ip_list = []
            for host in app.app_server.all():
                ips = get_ips_by_server_id(host.id)
                if ips:
                    ip_list.append(ips[0])
            tk = get_access_token()
            host_ids = get_host_ids(tk, ip_list)
            item_ids = get_monitor_item_ids(tk, host_ids, 'status[%d]' % app.tomcat_port)
            print(tk, ip_list, host_ids, item_ids)
            update_monitor_item(tk, item_ids, 0)
            res = {'code': 0, 'result': '已经禁用！'}
        except Exception as e:
            res = {'code': 1, 'result': str(e)}
        return self.render_json_response(res)

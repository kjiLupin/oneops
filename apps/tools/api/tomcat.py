# -*- coding: utf-8 -*-
"""
使用该功能条件：
1. hosts 文件中必须包含主机名
2. playbook 准备好
"""
import uuid
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from common.mixins import JSONResponseMixin

from job.tasks.ansible_api import AnsibleAPI
from ssh.models.host_user import HostUserAsset
from cmdb.models.asset import Server
from cmdb.models.business import App


class TomcatAPIView(LoginRequiredMixin, JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            do = request.GET.get('do', None)
            host_id = request.GET.get('host_id', None)
            app_id = request.GET.get('app_id', None)
            if do is None or host_id is None or app_id is None:
                res = {'code': 1, 'result': '错误调用！'}
                return self.render_json_response(res)
            host = Server.objects.get(id=host_id)
            hua = HostUserAsset.objects.filter(asset=host, host_user__username='root')
            if hua:
                hu = hua[0].host_user
                app = App.objects.get(id=app_id)
                if host.app_env == "test":
                    kwargs = {
                        'resource': list(),
                        'hosts_file': "/data/ansible/inventory/admin/hosts",
                        'host_user': hu.id
                    }
                    playbook = ["/data/ansible/playbook/admin/tomcat_restart.yml"]
                    if do == "restart":
                        extra_vars = {"apphost": host.hostname, "app_code": app.app_code,
                                      "tomcat_port": app.tomcat_port, "app_type": app.app_type, "do": "restart"}
                    elif do == "redeploy":
                        extra_vars = {"apphost": host.hostname, "app_code": app.app_code,
                                      "tomcat_port": app.tomcat_port, "app_type": app.app_type, "do": "redeploy"}
                    else:
                        res = {'code': 1, 'result': '非法调用！'}
                        return self.render_json_response(res)
                    ansible_api = AnsibleAPI(0, str(uuid.uuid4()), **kwargs)
                    print(ansible_api.run_playbook(playbook, extra_vars))
                    res = {'code': 0, 'result': '任务已提交，请再手动确认是否执行成功！'}
                else:
                    res = {'code': 1, 'result': '非法调用！该主机非测试主机！'}
            else:
                res = {'code': 1, 'result': '该主机未绑定用户为root的HostUser！'}
        except Exception as e:
            res = {'code': 1, 'result': str(e)}
        return self.render_json_response(res)

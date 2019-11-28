
import simplejson as json
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from django.http import QueryDict
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin
from common.utils.base import get_ip_by_request
from common.utils.cryptor import cryptor
from common.utils.http_api import http_request
from tools.utils.workflowops_api import workflowops_host_api, get_workflowops_token


@method_decorator(csrf_exempt, name='dispatch')
class NetSurfingListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_tools_net_surfing'
    template_name = 'tools/net_surfing.html'

    def get(self, request, **kwargs):
        context = {
            'path1': '小工具',
            'path2': '科学上网',
            'id': '',
            'client_ip': '',
            'last_client_ip': '',
            'apply_time': '',
            'expire_time': '',
            'status': 'UnKnow!',
            'errmsg': ''
        }
        try:
            client_ip = get_ip_by_request(request)
            if client_ip:
                username, password = request.user.username, cryptor.decrypt(request.user.password2)
                token = get_workflowops_token(username, password)
                headers = {'Authorization': 'JWT ' + token}
                url = "{}/science-surfing/online-user/?username={}".format(workflowops_host_api, username)
                status, ret = http_request.get(url, headers)
                if status is True:
                    print(ret)
                    s = json.loads(ret)
                    if s["count"] > 0:
                        online_info = s['results'][0]
                        last_client_ip = online_info['ip']
                        context.update({'id': online_info['id'], 'last_client_ip': last_client_ip})
                        if client_ip != last_client_ip:
                            errmsg = """提示：您的申请未失效，但检测到您的ip已经变化！若需要更新，请手动下线后重新申请！""".format(client_ip)
                            context.update({'errmsg': errmsg})
                        apply_time = online_info['apply_time']
                        expire_time = online_info['expire_time']
                        status = 'online'
                    else:
                        apply_time, expire_time = '无', '无'
                        status = 'offline'

                    context.update({'client_ip': client_ip, 'apply_time': apply_time,
                                    'expire_time': expire_time, 'status': status})
                else:
                    raise Exception("调用WorkflowOps系统失败，若您刚修改过OA密码，请退出重新登录！")
            else:
                context.update({'errmsg': "无法获取到您的ip，请联系管理员！"})
        except Exception as e:
            context.update({'errmsg': str(e)})
        context.update(**kwargs)
        return self.render_to_response(context)

    def post(self, request, **kwargs):
        try:
            client_ip = get_ip_by_request(request)
            username, password = request.user.username, cryptor.decrypt(request.user.password2)
            token = get_workflowops_token(username, password)
            headers = {'Authorization': 'JWT ' + token}
            url = "{}/science-surfing/apply/".format(workflowops_host_api)
            status, ret = http_request.post(url, {'ip': client_ip}, headers)
            if status is True:
                res = {'code': 0, 'data': 'ok'}
            else:
                res = {'code': -1, 'errmsg': ret}
        except Exception as e:
            res = {'code': -1, 'errmsg': str(e)}
        return self.render_json_response(res)


@method_decorator(csrf_exempt, name='dispatch')
class NetSurfingDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_tools_net_surfing'

    def put(self, request, **kwargs):
        try:
            pk = kwargs.get('pk')
            put_data = QueryDict(request.body).copy()
            url = "{}/science-surfing/{}/{}/".format(workflowops_host_api, put_data['action'], pk)
            username, password = request.user.username, cryptor.decrypt(request.user.password2)
            token = get_workflowops_token(username, password)
            headers = {'Authorization': 'JWT ' + token}
            status, ret = http_request.put(url, {}, headers)
            if status is True:
                print(json.loads(ret))
                res = {'code': 0, 'data': json.loads(ret)}
            else:
                res = {'code': -1, 'errmsg': ret}
        except Exception as e:
            res = {'code': -1, 'errmsg': str(e)}
        return self.render_json_response(res)


class NetSurfingLogsView(PermissionRequiredMixin, JSONResponseMixin, View):
    permission_required = 'auth.perm_tools_net_surfing'

    def get(self, request, *args, **kwargs):
        try:
            page = int(request.GET.get('page', 0)) + 1
            page_size = request.GET.get('page_size', 1)
            username, password = request.user.username, cryptor.decrypt(request.user.password2)
            token = get_workflowops_token(username, password)
            headers = {'Authorization': 'JWT ' + token}
            url = "{}/science-surfing/logs/?username={}&page={}&page_size={}".\
                format(workflowops_host_api, username, page, page_size)
            status, ret = http_request.get(url, headers)
            if status is True:
                res = json.loads(ret)
                res = {'total': res['count'], 'rows': res['results']}
            else:
                res = {'code': -1, 'errmsg': ret}
            return self.render_json_response(res)
        except Exception as e:
            return self.render_json_response({'code': 1, 'errmsg': str(e)})

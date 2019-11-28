
from django.views.generic import View
from django.http import HttpResponse
from tools.utils.qizhi_api import create_host


class QiZhiCreateHostAPIView(View):

    def post(self, request, *args, **kwargs):
        try:
            group_ids = request.POST.getlist('group', [])
            hostname = request.POST.get('hostname', None)
            ip = request.POST.get('ip', None)
            print(group_ids, hostname, ip)
            if group_ids and hostname and ip:
                res = create_host(group_ids, hostname, ip)
            else:
                res = '组、主机名、ip 不允许为空！'
        except Exception as e:
            res = str(e)
        return HttpResponse(res)

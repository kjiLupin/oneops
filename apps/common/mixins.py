# coding: utf-8
from IPy import IP
import simplejson as json
from django.contrib.auth.mixins import AccessMixin, UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from common.utils.json_encoder import DjangoOverRideJSONEncoder
from common.utils.base import get_ip_by_request
from common.models import RPCIpWhite


class AdminUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        elif not self.request.user.is_superuser:
            self.raise_exception = True
            return False
        return True


class RPCIpWhiteMixin(AccessMixin):
    """Verify that the rpc client ip is authenticated."""
    url_name = ""

    def dispatch(self, request, *args, **kwargs):
        client_ip = get_ip_by_request(request)
        # print(client_ip, self.url_name)
        if not RPCIpWhite.objects.filter(url_name=self.url_name).exists():
            return super().dispatch(request, *args, **kwargs)
        for rpc_ip_white in RPCIpWhite.objects.filter(url_name=self.url_name):
            for ip in rpc_ip_white.ip_list.split(','):
                if ip == "*" or client_ip == ip or client_ip in IP(ip):
                    return super().dispatch(request, *args, **kwargs)
        return JsonResponse({"code": -1, "errmsg": "Your ip Not in white list."})


class JSONResponseMixin(object):
    """JSON mixin"""
    @staticmethod
    def render_json_response(context):
        # return HttpResponse(context, content_type='application/json')
        return HttpResponse(json.dumps(context, cls=DjangoOverRideJSONEncoder, bigint_as_string=True),
                            content_type='application/json')

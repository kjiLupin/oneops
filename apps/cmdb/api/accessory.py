# -*- coding: utf-8 -*-
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from common.mixins import JSONResponseMixin
from common.utils.base import send_msg_to_admin
from cmdb.models.accessory import Accessory


@method_decorator(csrf_exempt, name='dispatch')
class AccessoryResidualAPIView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            mode = request.GET.get("mode", '')
            mode_id = request.GET.get("mode_id", '')
            idc_id = request.GET.get("idc_id", '')
            if not mode or not mode_id or not idc_id:
                print(mode, mode_id, idc_id)
                res = {'code': 1, 'errmsg': '非法调用！'}
            else:
                residual = Accessory.objects.filter(storehouse__id=idc_id, mode=mode, mode_id=mode_id, is_active=True).count()
                res = {'code': 0, 'result': residual}
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)

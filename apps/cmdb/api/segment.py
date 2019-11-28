# -*- coding: utf-8 -*-
import json
import re
from django.views.generic import View
from cmdb.models.base import IDC, VLan, NetworkSegment
from common.mixins import JSONResponseMixin
from common.utils.base import send_msg_to_admin


class SegmentListAPIView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            idc_name = request.GET.get('idc', None)
            vlan_num = request.GET.get('vlan', None)
            result = list()
            if idc_name and vlan_num:
                if not IDC.objects.filter(idc_name=idc_name).exists():
                    return self.render_json_response({'code': 1, 'result': "IDC未找到！"})
                idc = IDC.objects.get(idc_name=idc_name)
                if not VLan.objects.filter(idc=idc, vlan_num=vlan_num).exists():
                    return self.render_json_response({'code': 1, 'result': "vlan未找到！"})
                vlan = VLan.objects.get(idc=idc, vlan_num=vlan_num)
                for segment in NetworkSegment.objects.filter(vlan=vlan):
                    result.append("{}/{}".format(segment.segment, segment.netmask))
            elif idc_name:
                if not IDC.objects.filter(idc_name=idc_name).exists():
                    return self.render_json_response({'code': 1, 'result': "IDC未找到！"})
                idc = IDC.objects.get(idc_name=idc_name)
                for vlan in VLan.objects.filter(idc=idc):
                    for segment in NetworkSegment.objects.filter(vlan=vlan):
                        result.append("{}/{}".format(segment.segment, segment.netmask))
            elif vlan_num:
                if not VLan.objects.filter(vlan_num=vlan_num).exists():
                    return self.render_json_response({'code': 1, 'result': "vlan未找到！"})
                for vlan in VLan.objects.filter(vlan_num=vlan_num):
                    for segment in NetworkSegment.objects.filter(vlan=vlan):
                        result.append("{}/{}".format(segment.segment, segment.netmask))
            else:
                for idc in IDC.objects.get_queryset():
                    for vlan in VLan.objects.filter(idc=idc):
                        for segment in NetworkSegment.objects.filter(vlan=vlan):
                            result.append("{}/{}".format(segment.segment, segment.netmask))
            res = {'code': 0, 'result': result}
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)

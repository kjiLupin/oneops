# -*- coding: utf-8 -*-
import re
import traceback
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, F
from django.http import QueryDict, JsonResponse
from common.mixins import JSONResponseMixin
from common.utils.base import dict_list_duplicate_delete

from cmdb.models.base import IDC
from cmdb.models.accessory import Caddy, Accessory, UseRecord, InventoryRecord

#
# class CaddyView(PermissionRequiredMixin, TemplateView):
#     permission_required = 'auth.perm_cmdb_accessory_view'
#     template_name = "cmdb/caddy.html"
#
#     def get_context_data(self, **kwargs):
#         caddy_list = Caddy.objects.get_queryset()
#         context = {
#             'path1': '配件',
#             'path2': '硬盘托架',
#             'idc_list': [{"id": i.id, "name": i.idc_name} for i in IDC.objects.get_queryset()],
#             'dimensions_list': dict_list_duplicate_delete([
#                 {'key': obj.dimensions, 'value': obj.get_dimensions_display()} for obj in caddy_list]),
#             'version_list': [{'id': obj.id, 'version': obj.get_dimensions_display()} for obj in caddy_list]
#         }
#         kwargs.update(context)
#         return super().get_context_data(**kwargs)


class CaddyListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_accessory_view'

    def get(self, request, **kwargs):
        limit = request.GET.get('limit')
        offset = request.GET.get('offset')
        is_active = request.GET.get("is_active", 1)
        sort_order = request.GET.get("sortOrder", '')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        mode_id_list = list()
        mode_id = request.GET.get("mode_id", '')
        if mode_id:
            mode_id_list.append(int(mode_id))
            obj = Caddy.objects.get(id=mode_id)
            acc_detail = {
                obj.id: {
                    'version': obj.get_dimensions_display(), 'dimensions': obj.get_dimensions_display()
                }
            }
        else:
            if re.match(r'-?dimensions', sort_name, re.I):
                obj_list = Caddy.objects.get_queryset().order_by(sort_name)
            else:
                obj_list = Caddy.objects.get_queryset()
            dimensions = request.GET.get("dimensions", '')
            if dimensions:
                obj_list = obj_list.filter(dimensions=dimensions)

            acc_detail = dict()
            for obj in obj_list:
                mode_id_list.append(obj.id)
                acc_detail[obj.id] = {
                    'version': obj.get_dimensions_display(), 'dimensions': obj.get_dimensions_display()
                }

        idc_id = request.GET.get("idc_id", '')
        if idc_id:
            idc = IDC.objects.get(id=idc_id)
            if not re.match(r'-?dimensions', sort_name, re.I):
                accessory_list = Accessory.objects.filter(storehouse=idc, mode='caddy', mode_id__in=mode_id_list,
                                                          is_active=is_active).order_by(sort_name)
            else:
                accessory_list = Accessory.objects.filter(storehouse=idc, mode='caddy', mode_id__in=mode_id_list,
                                                          is_active=is_active)
        else:
            if not re.match(r'-?dimensions', sort_name, re.I):
                accessory_list = Accessory.objects.filter(mode='caddy', mode_id__in=mode_id_list,
                                                          is_active=is_active).order_by(sort_name)
            else:
                accessory_list = Accessory.objects.filter(mode='caddy', mode_id__in=mode_id_list, is_active=is_active)

        search = request.GET.get("search", '')
        if search:
            accessory_list = accessory_list.filter(Q(manufacturer=search) | Q(sn=search) |
                                                   Q(vendor=search) | Q(comment__contains=search)).distinct()

        result = list()
        for acc in accessory_list[int(offset):int(offset + limit)]:
            receive = list()
            for rev in UseRecord.objects.filter(accessory=acc).order_by('-id'):
                receive.append('%s %s %s' % (rev.created_date, rev.server.login_address, rev.get_operate_display()))
            result.append({
                'id': acc.id,
                'storehouse': acc.storehouse.idc_name,
                'version': acc_detail[acc.mode_id]['version'],
                'dimensions': acc_detail[acc.mode_id]['dimensions'],
                'receive': receive,
                'manufacturer': acc.manufacturer,
                'sn': acc.sn,
                'vendor': acc.vendor,
                'trade_date': acc.trade_date,
                'expired_date': acc.expired_date,
                'comment': acc.comment,
                'is_active': acc.is_active,
                'created_date': acc.created_date
            })
        res = {"total": accessory_list.count(), "rows": result}
        return self.render_json_response(res)


class CaddyDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_accessory_view', 'auth.perm_cmdb_accessory_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = Caddy.objects.get(id=pk)
            result = {
                'accessory': 'caddy',
                'version': obj.get_dimensions_display()
            }
            res = {'code': 0, 'result': result}
        except Caddy.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            caddy = Caddy.objects.get(id=pk)
            put_data = QueryDict(request.body, mutable=True)
            idc_id = put_data.pop('idc_id')[0]
            count = put_data.pop('count')[0]
            acc_list = Accessory.objects.filter(storehouse__id=idc_id, mode='caddy', mode_id=caddy.id, is_active=True)
            if acc_list.count() < int(count):
                res = {"code": 1, "errmsg": "可用数量不足！"}
                return JsonResponse(res, safe=True)
            for a in acc_list[:int(count)]:
                a.is_active = False
                a.save(update_fields=['is_active'])
            InventoryRecord.objects.create(accessory='caddy', operate='receive',
                                           content='{0} 硬盘托架 {1} 个！'.format(caddy.get_dimensions_display(), count),
                                           user=request.user)

            res = {"code": 0, "result": "领用成功"}
        except Exception as e:
            res = {"code": 1, "errmsg": "领用错误：%s" % str(e)}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = Caddy.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)

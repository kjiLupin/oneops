# -*- coding: utf-8 -*-
import datetime
import traceback
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from common.mixins import JSONResponseMixin

from accounts.models import User
from cmdb.models.accessory import accessory_item, InventoryRecord


class InventoryRecordView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_accessory_view'
    template_name = "cmdb/inventory_record.html"

    def get_context_data(self, **kwargs):
        user_id_list = InventoryRecord.objects.get_queryset().values('user_id').distinct()
        context = {
            'path1': '配件',
            'path2': '进货与消耗',
            'acc_item': accessory_item,
            'user_list': [{'id': u.id, 'name': u.display} for u in User.objects.filter(id__in=user_id_list)]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class InventoryRecordListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_accessory_view'

    def get(self, request, **kwargs):
        limit = request.GET.get('limit')
        offset = request.GET.get('offset')
        date_from = request.GET.get("date_from", None)
        date_to = request.GET.get("date_to", None)

        if date_from and date_to:
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
            obj_list = InventoryRecord.objects.filter(created_date__gte=date_from, created_date__lte=date_to).order_by('-id')
        elif date_from:
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
            obj_list = InventoryRecord.objects.filter(created_date__gte=date_from).order_by('-id')
        elif date_to:
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
            obj_list = InventoryRecord.objects.filter(created_date__lte=date_to).order_by('-id')
        else:
            thirty_day_ago = datetime.datetime.now() + datetime.timedelta(days=-30)
            obj_list = InventoryRecord.objects.filter(created_date__gte=thirty_day_ago).order_by('-id')

        accessory = request.GET.get("accessory", '')
        if accessory:
            obj_list = obj_list.filter(accessory=accessory)
        operate = request.GET.get("operate", '')
        if operate:
            obj_list = obj_list.filter(operate=operate)
        user_id = request.GET.get("user_id", '')
        if user_id:
            obj_list = obj_list.filter(user_id=int(user_id))

        search = request.GET.get("search", '')
        if search:
            obj_list = obj_list.filter(Q(server__login_address__contains=search) |
                                       Q(net_device__login_address__contains=search) |
                                       Q(content__contains=search)).distinct()

        result = list()
        for obj in obj_list[int(offset):int(offset + limit)]:
            if obj.server:
                asset = obj.server.login_address
            elif obj.net_device:
                asset = obj.net_device.login_address
            else:
                asset = ''
            result.append({
                'id': obj.id,
                'accessory': obj.get_accessory_display(),
                'asset': asset,
                'operate': obj.get_operate_display(),
                'content': obj.content,
                'user': obj.user.display,
                'created_date': obj.created_date
            })
        res = {"total": obj_list.count(), "rows": result}
        return self.render_json_response(res)

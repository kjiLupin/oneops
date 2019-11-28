# -*- coding: utf-8 -*-
import datetime
import traceback
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from common.mixins import JSONResponseMixin

from accounts.models import User
from cmdb.models.asset import Maintenance


class MaintenanceView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_asset_view'
    template_name = "cmdb/maintenance.html"

    def get_context_data(self, **kwargs):
        user_id_list = Maintenance.objects.get_queryset().values('user_id').distinct()
        context = {
            'path1': 'CMDB',
            'path2': '维保记录',
            'user_list': [{'id': u.id, 'name': u.display} for u in User.objects.filter(id__in=user_id_list)]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class MaintenanceListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_asset_view'

    def get(self, request, **kwargs):
        limit = request.GET.get('limit')
        offset = request.GET.get('offset')
        date_from = request.GET.get("date_from", None)
        date_to = request.GET.get("date_to", None)

        if date_from and date_to:
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
            obj_list = Maintenance.objects.filter(created_date__gte=date_from, created_date__lte=date_to).order_by('-id')
        elif date_from:
            date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
            obj_list = Maintenance.objects.filter(created_date__gte=date_from).order_by('-id')
        elif date_to:
            date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
            obj_list = Maintenance.objects.filter(created_date__lte=date_to).order_by('-id')
        else:
            thirty_day_ago = datetime.datetime.now() + datetime.timedelta(days=-30)
            obj_list = Maintenance.objects.filter(created_date__gte=thirty_day_ago).order_by('-id')

        asset = request.GET.get("asset", '')
        if asset == 'server':
            obj_list = obj_list.exclude(server=None)
        elif asset == 'net_device':
            obj_list = obj_list.exclude(net_device=None)

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
                asset = '服务器'
                ip = obj.server.login_address
            elif obj.net_device:
                asset = '网络设备'
                ip = obj.net_device.login_address
            else:
                asset, ip = '', ''
            result.append({
                'id': obj.id,
                'asset': asset,
                'ip': ip,
                'content': obj.content,
                'user': obj.user.display,
                'created_date': obj.created_date
            })
        res = {"total": obj_list.count(), "rows": result}
        return self.render_json_response(res)

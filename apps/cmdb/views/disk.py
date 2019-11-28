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
from cmdb.models.asset import Server
from cmdb.models.accessory import Disk, Accessory, UseRecord, InventoryRecord


class DiskView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_accessory_view'
    template_name = "cmdb/disk.html"

    def get_context_data(self, **kwargs):
        disk_list = Disk.objects.get_queryset()
        context = {
            'path1': '配件',
            'path2': '硬盘',
            'idc_list': [{"id": i.id, "name": i.idc_name} for i in IDC.objects.get_queryset()],
            'device_type_list': dict_list_duplicate_delete([
                {'key': obj.device_type, 'value': obj.get_device_type_display()} for obj in disk_list]),
            'capacity_list': [obj['capacity'] for obj in disk_list.values('capacity').distinct()],
            'rpm_list': [obj['rpm'] for obj in disk_list.values('rpm').distinct()],
            'dimensions_list': dict_list_duplicate_delete([
                {'key': obj.dimensions, 'value': obj.get_dimensions_display()} for obj in disk_list]),
            'version_list': [{
                'id': obj.id,
                'version': '%s|%dG|%d转/s|%s' % (
                    obj.get_device_type_display(), obj.capacity, obj.rpm, obj.get_dimensions_display()),
            } for obj in disk_list]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DiskListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
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
            obj = Disk.objects.get(id=mode_id)
            acc_detail = {
                obj.id: {
                    'version': '%s|%dG|%d转/s|%s' % (
                        obj.get_device_type_display(), obj.capacity, obj.rpm, obj.get_dimensions_display()),
                    'device_type': obj.get_device_type_display(), 'capacity': obj.capacity, 'rpm': obj.rpm,
                    'dimensions': obj.get_dimensions_display()
                }
            }
        else:
            device_type = request.GET.get("device_type", '')
            capacity = request.GET.get("capacity", '')
            dimensions = request.GET.get("dimensions", '')
            if re.match(r'-?device_type|-?capacity|-?rpm|-?dimensions', sort_name, re.I):
                obj_list = Disk.objects.get_queryset().order_by(sort_name)
            else:
                obj_list = Disk.objects.get_queryset()
            if device_type:
                obj_list = obj_list.filter(device_type=device_type)
            if capacity:
                obj_list = obj_list.filter(capacity=capacity)
            if dimensions:
                obj_list = obj_list.filter(dimensions=dimensions)

            acc_detail = dict()
            for obj in obj_list:
                mode_id_list.append(obj.id)
                acc_detail[obj.id] = {
                    'version': '%s|%dG|%d转/s|%s' % (
                        obj.get_device_type_display(), obj.capacity, obj.rpm, obj.get_dimensions_display()),
                    'device_type': obj.get_device_type_display(), 'capacity': obj.capacity, 'rpm': obj.rpm,
                    'dimensions': obj.get_dimensions_display()
                }

        idc_id = request.GET.get("idc_id", '')
        if idc_id:
            idc = IDC.objects.get(id=idc_id)
            if not re.match(r'-?device_type|-?capacity|-?rpm|-?dimensions', sort_name, re.I):
                accessory_list = Accessory.objects.filter(storehouse=idc, mode='disk', mode_id__in=mode_id_list,
                                                          is_active=is_active).order_by(sort_name)
            else:
                accessory_list = Accessory.objects.filter(storehouse=idc, mode='disk', mode_id__in=mode_id_list,
                                                          is_active=is_active)
        else:
            if not re.match(r'-?device_type|-?capacity|-?rpm|-?dimensions', sort_name, re.I):
                accessory_list = Accessory.objects.filter(mode='disk', mode_id__in=mode_id_list,
                                                          is_active=is_active).order_by(sort_name)
            else:
                accessory_list = Accessory.objects.filter(mode='disk', mode_id__in=mode_id_list, is_active=is_active)

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
                'device_type': acc_detail[acc.mode_id]['device_type'],
                'capacity': acc_detail[acc.mode_id]['capacity'],
                'rpm': acc_detail[acc.mode_id]['rpm'],
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


class DiskDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_accessory_view', 'auth.perm_cmdb_accessory_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('acc_id')
        try:
            acc = Accessory.objects.get(pk=pk)
            obj = Disk.objects.get(id=acc.mode_id)
            server_list = list()
            for s in Server.objects.filter(is_vm=False).exclude(status__in=['deleted', 'ots']):
                server_list.append({'id': s.id, 'name': s.hostname, 'ip': s.login_address})
            result = {
                'id': acc.id,
                'storehouse': acc.storehouse.idc_name,
                'version': '%s|%dG|%d转/s|%s' % (
                    obj.get_device_type_display(), obj.capacity, obj.rpm, obj.get_dimensions_display()),
                'device_type': obj.get_device_type_display(),
                'capacity': obj.capacity,
                'rpm': obj.rpm,
                'dimensions': obj.get_dimensions_display(),
                'manufacturer': acc.manufacturer,
                'sn': acc.sn,
                'vendor': acc.vendor,
                'trade_date': acc.trade_date,
                'expired_date': acc.expired_date,
                'comment': acc.comment,
                'asset_list': server_list,
                'is_active': acc.is_active,
                'created_date': acc.created_date
            }
            res = {'code': 0, 'result': result}
        except Disk.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('acc_id')
        try:
            acc = Accessory.objects.get(pk=pk)
            disk = Disk.objects.get(id=acc.mode_id)
            disk_version = '%s|%dG|%d转/s|%s' % (
                disk.get_device_type_display(), disk.capacity, disk.rpm, disk.get_dimensions_display()),
            put_data = QueryDict(request.body, mutable=True)
            server_id = put_data.pop('asset_id')[0]
            if acc.is_active:
                res = {"code": 0, "result": "领用成功"}
            else:
                rev = UseRecord.objects.filter(accessory=acc).last()
                if rev and rev.operate == 'install':
                    UseRecord.objects.create(accessory=acc, server=rev.server, operate='remove')

                InventoryRecord.objects.create(accessory='disk', server=rev.server, operate='revert',
                                               content=disk_version, user=request.user)
                res = {"code": 0, "errmsg": "变更成功！"}
            acc.is_active = False
            acc.save(update_fields=['is_active'])
            UseRecord.objects.create(accessory=acc, server_id=server_id, operate='install')
            InventoryRecord.objects.create(accessory='disk', server_id=server_id, operate='receive',
                                           content=disk_version, user=request.user)
        except Exception as e:
            res = {"code": 1, "errmsg": "领用错误：%s" % str(e)}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('acc_id')
        try:
            obj = Accessory.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)

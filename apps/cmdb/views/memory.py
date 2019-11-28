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
from cmdb.models.accessory import Memory, Accessory, UseRecord, InventoryRecord


class MemoryView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_accessory_view'
    template_name = "cmdb/memory.html"

    def get_context_data(self, **kwargs):
        mem_list = Memory.objects.get_queryset()
        context = {
            'path1': '配件',
            'path2': '内存',
            'idc_list': [{"id": i.id, "name": i.idc_name} for i in IDC.objects.get_queryset()],
            'ram_type_list': dict_list_duplicate_delete([
                {'key': mem.ram_type, 'value': mem.get_ram_type_display()} for mem in mem_list]),
            'ram_size_list': [mem['ram_size'] for mem in mem_list.values('ram_size').distinct()],
            'speed_list': [mem['speed'] for mem in mem_list.values('speed').distinct()],
            'version_list': [{
                'id': mem.id,
                'version': '{0}|{1}G|{2}MT/s'.format(mem.get_ram_type_display(), str(mem.ram_size), str(mem.speed))
            } for mem in mem_list]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class MemoryListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
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
            obj = Memory.objects.get(id=mode_id)
            acc_detail = {
                obj.id: {
                    'version': '%s|%dG|%dMT/s' % (obj.get_ram_type_display(), obj.ram_size, obj.speed),
                    'ram_type': obj.ram_type, 'ram_size': obj.ram_size, 'speed': obj.speed
                }
            }
        else:
            ram_type = request.GET.get("ram_type", '')
            ram_size = request.GET.get("ram_size", '')
            speed = request.GET.get("speed", '')
            if re.match(r'-?ram_type|-?ram_size|-?speed', sort_name, re.I):
                obj_list = Memory.objects.get_queryset().order_by(sort_name)
            else:
                obj_list = Memory.objects.get_queryset()
            if ram_type:
                obj_list = obj_list.filter(ram_type=ram_type)
            if ram_size:
                obj_list = obj_list.filter(ram_size=ram_size)
            if speed:
                obj_list = obj_list.filter(speed=speed)

            acc_detail = dict()
            for obj in obj_list:
                mode_id_list.append(obj.id)
                acc_detail[obj.id] = {
                    'version': '%s|%dG|%dMT/s' % (obj.get_ram_type_display(), obj.ram_size, obj.speed),
                    'ram_type': obj.ram_type, 'ram_size': obj.ram_size, 'speed': obj.speed
                }

        idc_id = request.GET.get("idc_id", '')
        if idc_id:
            idc = IDC.objects.get(id=idc_id)
            if not re.match(r'-?ram_type|-?ram_size|-?speed', sort_name, re.I):
                accessory_list = Accessory.objects.filter(storehouse=idc, mode='memory', mode_id__in=mode_id_list,
                                                          is_active=is_active).order_by(sort_name)
            else:
                accessory_list = Accessory.objects.filter(storehouse=idc, mode='memory', mode_id__in=mode_id_list,
                                                          is_active=is_active)
        else:
            if not re.match(r'-?ram_type|-?ram_size|-?speed', sort_name, re.I):
                accessory_list = Accessory.objects.filter(mode='memory', mode_id__in=mode_id_list,
                                                          is_active=is_active).order_by(sort_name)
            else:
                accessory_list = Accessory.objects.filter(mode='memory', mode_id__in=mode_id_list, is_active=is_active)

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
                'ram_type': acc_detail[acc.mode_id]['ram_type'],
                'ram_size': acc_detail[acc.mode_id]['ram_size'],
                'speed': acc_detail[acc.mode_id]['speed'],
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


class MemoryDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_accessory_view', 'auth.perm_cmdb_accessory_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('acc_id')
        try:
            acc = Accessory.objects.get(pk=pk)
            obj = Memory.objects.get(id=acc.mode_id)
            server_list = list()
            for s in Server.objects.filter(is_vm=False).exclude(status__in=['deleted', 'ots']):
                server_list.append({'id': s.id, 'name': s.hostname, 'ip': s.login_address})
            result = {
                'id': acc.id,
                'storehouse': acc.storehouse.idc_name,
                'version': '%s|%dG|%dMT/s' % (obj.get_ram_type_display(), obj.ram_size, obj.speed),
                'ram_type': obj.get_ram_type_display(),
                'ram_size': obj.ram_size,
                'speed': obj.speed,
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
        except Memory.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('acc_id')
        try:
            acc = Accessory.objects.get(pk=pk)
            mem = Memory.objects.get(id=acc.mode_id)
            mem_version = '%s|%dG|%dMT/s' % (mem.get_ram_type_display(), mem.ram_size, mem.speed),
            put_data = QueryDict(request.body, mutable=True)
            server_id = put_data.pop('asset_id')[0]
            if acc.is_active:
                res = {"code": 0, "result": "领用成功"}
            else:
                rev = UseRecord.objects.filter(accessory=acc).last()
                if rev and rev.operate == 'install':
                    UseRecord.objects.create(accessory=acc, server=rev.server, operate='remove')

                InventoryRecord.objects.create(accessory='memory', server=rev.server, operate='revert',
                                               content=mem_version, user=request.user)
                res = {"code": 0, "errmsg": "变更成功！"}
            acc.is_active = False
            acc.save(update_fields=['is_active'])
            UseRecord.objects.create(accessory=acc, server_id=server_id, operate='install')
            InventoryRecord.objects.create(accessory='memory', server_id=server_id, operate='receive',
                                           content=mem_version, user=request.user)
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

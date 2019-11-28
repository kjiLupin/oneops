# -*- coding: utf-8 -*-
import os
import subprocess
import xlrd
import datetime
import re
import traceback
from wsgiref.util import FileWrapper

from django.shortcuts import get_object_or_404
from django.views.generic import View, ListView, TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, F
from django.http import JsonResponse, HttpResponse, QueryDict
from common.mixins import JSONResponseMixin
from common.utils.base import BASE_DIR

from cmdb.models.base import IDC, Cabinet, Ip
from cmdb.models.asset import NetDevice, Maintenance
from cmdb.forms import NetDeviceForm
from cmdb.api.ip import get_or_create_ip_obj


network_device_key_map = {
    'aid': 'asset_id', 'hn': 'hostname', 'lt': 'login_type', 'la': 'login_address', 'snmp': 'snmp',
    'type': 'type', 'mfr': 'manufacturer', 'os': 'os', 'pn': 'product_name', 'td': 'trade_date',
    'ed': 'expired_date', 'sn': 'sn', 'mod': 'model', 'ver': 'version', 'spl': 'supplier',
    'sp': 'supplier_phone', 'idc': 'idc__idc_name', 'cab': 'cabinet__name', 'cp': 'cabinet_pos',
    'cmt': 'comment', 'stat': 'status', 'dc': 'date_created', 'dlc': 'date_last_checked',
}


class NetDeviceView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_asset_view'
    template_name = "cmdb/network_device.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': '网络设备',
            'idc_list': IDC.objects.all(),
            'ndf': NetDeviceForm()
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class NetDeviceListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_asset_view'

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset'))

        sort_order = request.GET.get("sortOrder", 'asc')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = network_device_key_map.get(sort_name, 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        idc_id = request.GET.get("idc_id", '')
        status = request.GET.get("status", '')
        if idc_id and status:
            obj_list = NetDevice.objects.filter(idc_id=idc_id, status=status).order_by(sort_name)
        elif idc_id:
            obj_list = NetDevice.objects.filter(idc_id=idc_id).order_by(sort_name)
        elif status:
            obj_list = NetDevice.objects.filter(status=status).order_by(sort_name)
        else:
            obj_list = NetDevice.objects.get_queryset().order_by(sort_name)

        search = request.GET.get("search", None)
        if search is not None:
            ips = Ip.objects.filter(ip__contains=search)
            obj_list = obj_list.filter(Q(ip__in=ips) | Q(sys_name__contains=search) | Q(os__contains=search) |
                                       Q(manufacturer__contains=search) | Q(product_name__contains=search) |
                                       Q(snmp__contains=search) | Q(login_address__contains=search)).distinct()

        result = list()
        for o in obj_list[offset:(offset + limit)]:
            ips = ' '.join([ip.ip for ip in o.ip.all()])
            maint = ['%s %s %s' % (m.created_date, m.user.display, m.content) for m in Maintenance.objects.filter(net_device=o)]
            result.append({
                'id': o.id,
                'aid': o.asset_id,
                'sn': o.sys_name,
                'lt': o.get_login_type_display(),
                'la': o.login_address,
                'snmp': o.snmp,
                'type': o.get_type_display(),
                'mfr': o.get_manufacturer_display(),
                'os': o.os,
                'pn': o.product_name,
                'mod': o.model,
                'ver': o.version,
                'cab': o.cabinet.name if o.cabinet else '-',
                'cp': o.cabinet_pos,
                'spl': o.supplier,
                'sp': o.supplier_phone,
                'stat': o.get_status_display(),
                'cmt': o.comment,
                'idc': o.idc.idc_name,
                'maint': '\n'.join(maint),
                'ip': ips
            })
        res = {"total": obj_list.count(), "rows": result}
        return self.render_json_response(res)

    def post(self, request):
        if not request.user.has_perm('auth.perm_cmdb_asset_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        form = NetDeviceForm(request.POST)
        if form.is_valid():
            form.save()
            res = {'code': 0, 'result': '添加成功！'}
        else:
            # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
            res = {'code': 1, 'errmsg': form.errors}
        return self.render_json_response(res)


class NetDeviceDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_asset_view', 'auth.perm_cmdb_asset_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            o = NetDevice.objects.get(pk=pk)
            result = {
                'id': o.id,
                'asset_id': o.asset_id,
                'sys_name': o.sys_name,
                'login_type': o.login_type,
                'login_address': o.login_address,
                'snmp': o.snmp,
                'type': o.type,
                'manufacturer': o.manufacturer,
                'os': o.os,
                'product_name': o.product_name,
                'model': o.model,
                'version': o.version,
                'idc': o.idc_id,
                'cabinet': o.cabinet_id,
                'cabinet_pos': o.cabinet_pos,
                'supplier': o.supplier,
                'supplier_phone': o.supplier_phone,
                'status': o.status,
                'comment': o.comment
            }
            res = {'code': 0, 'result': result}
        except NetDevice.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        p = get_object_or_404(NetDevice, pk=pk)
        post_data = QueryDict(request.body).copy()
        if 'maint' in post_data:
            Maintenance.objects.create(net_device=p, content=post_data['content'], user=request.user)
            res = {'code': 0, 'result': '添加成功！'}
            return JsonResponse(res, safe=True)
        form = NetDeviceForm(post_data, instance=p)
        if form.is_valid():
            form.save()
            res = {"code": 0, "result": "更新成功"}
        else:
            res = {"code": 1, "errmsg": form.errors}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            # 是否要跟服务器一样，添加deleted状态。修改状态，不删除数据。
            obj = NetDevice.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)


@method_decorator(csrf_exempt, name='dispatch')
class NetDeviceTemplateView(PermissionRequiredMixin, JSONResponseMixin, View):
    permission_required = 'auth.perm_cmdb_asset_edit'

    def get(self, request, *args, **kwargs):
        try:
            filename = 'network_devices_template.xls'
            export_file = os.path.join(BASE_DIR, 'cmdb', 'docs', filename)
            if os.path.isfile(export_file):
                wrapper = FileWrapper(open(export_file, "rb"))
                response = HttpResponse(wrapper, content_type='application/vnd.ms-excel')
                response['Content-Length'] = os.path.getsize(export_file)
                response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
                return response
            else:
                return HttpResponse('模板文件不存在！')
        except Exception as e:
            return HttpResponse('模板文件下载失败：' + str(e))

    def post(self, request, *args, **kwargs):
        import_files = request.FILES.getlist('files', None)
        if len(import_files) == 0:
            return self.render_json_response({'code': 1, 'msg': '文件为空，或上传错误！'})
        date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        file_dir = os.path.join(BASE_DIR, 'cmdb', 'docs')
        created, updated, failed = [], [], []
        attr = ['id', 'sys_name', 'ips', 'login_type', 'login_address', 'snmp', 'type', 'manufacturer', 'os', 'product_name',
                'model', 'version', 'idc', 'cabinet', 'cabinet_pos', 'supplier', 'supplier_phone', 'status', 'comment']
        for im_file in import_files:
            file_name = im_file.name
            file_path = os.path.join(file_dir, request.user.username + '_' + date_now + '_' + file_name)
            with open(file_path, 'wb') as f:
                for chunk in im_file.chunks():
                    f.write(chunk)
            if not os.path.isfile(file_path):
                failed.append('{}：文件为空，或上传错误！'.format(file_name))
                continue
            if not re.match(r'application/vnd\.(ms-excel|ms-office)', subprocess.getoutput('file -b --mime-type ' + file_path)):
                failed.append('{}：请上传excel文件!'.format(im_file))
                continue

            data = xlrd.open_workbook(file_path)
            data.sheet_names()
            sheet = data.sheet_by_index(0)
            for i in range(2, sheet.nrows):
                row = list()
                for j in range(sheet.ncols):
                    # ctype：0 empty, 1 string, 2 number, 3 date, 4 boolean, 5 error
                    ctype = sheet.cell(i, j).ctype
                    cell = sheet.cell_value(i, j)
                    if ctype == 1:
                        cell = cell.strip()
                    elif ctype == 2 and cell % 1 == 0:  # 如果是整形
                        cell = int(cell)
                    elif ctype == 3:  # 转成datetime对象
                        # date_value = xlrd.xldate_as_tuple(cell, data.datemode)
                        # cell = datetime.date(*date_value[:3]).strftime('%Y-%m-%d')
                        date = datetime.datetime(*xlrd.xldate_as_tuple(cell, 0))
                        cell = date.strftime('%Y-%m-%d %H:%M:%S')
                    elif ctype == 4:
                        cell = True if cell == 1 else False
                    row.append(cell)
                dict_raw = dict(zip(attr, row))
                _id = dict_raw.pop('id')
                if not _id and not (dict_raw['login_type'] and dict_raw['login_address'] and dict_raw['snmp']):
                    # id列值为空，则说明是新增。则登陆方式、登陆地址和snmp是必填项
                    failed.append('{} {}行：登陆方式、登陆地址和snmp是必填项'.format(file_name, str(i + 1)))
                    continue
                try:
                    ips = dict_raw.pop('ips')
                    idc, cabinet = dict_raw.pop('idc'), dict_raw.pop('cabinet')
                    if IDC.objects.filter(idc_name=idc).exists():
                        dict_raw['idc'] = IDC.objects.get(idc_name=idc)
                    else:
                        failed.append('{} {}行：该IDC "{}"未找到。'.format(file_name, str(i + 1), idc))
                        continue
                    if Cabinet.objects.filter(name=cabinet).exists():
                        dict_raw['cabinet'] = Cabinet.objects.get(name=cabinet)
                    else:
                        failed.append('{} {}行：该机柜 "{}"未找到。'.format(file_name, str(i + 1), cabinet))
                        continue
                    if dict_raw['cabinet_pos'] == "":
                        dict_raw.pop('cabinet_pos')
                    if dict_raw['model'] == "":
                        dict_raw.pop('model')

                    dict_raw['type'] = dict_raw['type'].lower()
                    dict_raw['product_name'] = str(dict_raw['product_name'])
                    dict_raw['status'] = 'used' if dict_raw['status'] == '已上架' else 'unused'
                    if not _id:
                        # id列值为空，则说明是新增记录
                        nd = NetDevice.objects.create(**dict_raw)
                        ip_create_failed = list()
                        for ip in ips.split(','):
                            ipo = get_or_create_ip_obj(dict_raw['idc'], None, ip)
                            if ipo is not None:
                                nd.ip.add(ipo)
                            else:
                                ip_create_failed.append(ip)
                        if ip_create_failed:
                            created.append('{} {}行：无法创建IP：{}'.format(file_name, str(i + 1), ','.join(ip_create_failed)))
                        else:
                            created.append('{} {}行：{}'.format(file_name, str(i + 1), dict_raw['login_address']))
                    else:
                        # id列不为空，则更新id为它的记录
                        if NetDevice.objects.filter(id=_id).exists():
                            NetDevice.objects.filter(id=_id).update(**dict_raw)
                            nd = NetDevice.objects.get(id=_id)
                            ip_create_failed = list()
                            for ip in ips.split(','):
                                ipo = get_or_create_ip_obj(dict_raw['idc'], None, ip)
                                ipo_list = list()
                                if ipo is not None:
                                    ipo_list.append(ipo)
                                else:
                                    ip_create_failed.append(ip)
                                nd.ip = ipo_list
                                nd.save()
                            if ip_create_failed:
                                created.append(
                                    '{} {}行：无法创建IP：{}'.format(file_name, str(i + 1), ','.join(ip_create_failed)))
                            else:
                                updated.append('{} {}行：{}'.format(file_name, str(i + 1), dict_raw['login_address']))
                        else:
                            failed.append('{} {}行：该id {}在数据库中未找到。'.format(file_name, str(i + 1), _id))
                except Exception as e:
                    print(traceback.print_exc())
                    failed.append('{} {}行：{}。'.format(file_name, str(i + 1), str(e)))
        data = {
            'code': 0,
            'created': created,
            'created_info': 'Created {}'.format(len(created)),
            'updated': updated,
            'updated_info': 'Updated {}'.format(len(updated)),
            'failed': failed,
            'failed_info': 'Failed {}'.format(len(failed)),
            'msg': 'Created: {}. Updated: {}, Error: {}'.format(
                len(created), len(updated), len(failed))
        }
        return self.render_json_response(data)

# -*- coding: utf-8 -*-
import re
import os
import subprocess
import xlrd
import datetime
import traceback
from wsgiref.util import FileWrapper

from IPy import IP
from django.shortcuts import render, get_object_or_404
from django.views.generic import View, ListView, TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, F
from django.http import JsonResponse, HttpResponse, QueryDict
from common.mixins import JSONResponseMixin
from common.utils.base import BASE_DIR

from cmdb.models.base import IDC, Cabinet, VLan, NetworkSegment, Ip
from cmdb.models.asset import Server, Nic, Maintenance, ServerResource
from cmdb.models.business import App
from cmdb.forms import PhysicalServerForm, VirtualServerForm
from .business import get_total_dept_child_node_id
from .ip import get_ips_by_server_id
from cmdb.api.ip import get_or_create_ip_obj

server_key_map = {
    'aid': 'asset_id', 'hn': 'hostname', 'uuid': 'uuid', 'ct': 'cpu_total', 'cu': 'cpu_used', 'mt': 'mem_total',
    'mu': 'mem_used', 'disk': 'disk', 'os': 'os', 'la': 'login_address', 'ma': 'manage_address', 'mod': 'model',
    'mfr': 'manufacturer', 'pn': 'product_name', 'rd': 'release_date', 'td': 'trade_date', 'ed': 'expired_date',
    'sn': 'sn', 'spl': 'supplier', 'sp': 'supplier_phone', 'vc': 'vm_count', 'idc': 'idc__idc_name',
    'cab': 'cabinet__name', 'cp': 'cabinet_pos', 'apt': 'applicant', 'cmt': 'comment', 'stat': 'status',
    'dc': 'date_created', 'dlc': 'date_last_checked', 'app_env': 'app_env',
}


def get_server_ids_by_ip(ip):
    if Ip.objects.filter(ip=ip).exists():
        ipo = Ip.objects.get(ip=ip)
        return [nic.server.id for nic in ipo.nic_set.all()]
    return []


class VirtualMachineView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_asset_view'
    template_name = "cmdb/virtual_machine.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': '虚拟机列表',
            'idc_list': IDC.objects.all(),
            'machine_list': Server.objects.filter(is_vm=0)
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class PhysicalMachineView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_asset_view'
    template_name = "cmdb/physical_machine.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': '物理机列表',
            'idc_list': IDC.objects.all()
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AppServerView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_appserver_view'
    template_name = "cmdb/app_server.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': '应用服务器列表'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class ServerListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):

    def has_permission(self):
        return self.request.user.has_perm('auth.perm_cmdb_appserver_view') or \
               self.request.user.has_perm('auth.perm_cmdb_asset_view')

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset'))

        sort_order = request.GET.get("sortOrder", 'asc')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = server_key_map.get(sort_name, 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        is_vm = request.GET.get("is_vm", None)
        app_env = request.GET.get("app_env", '')
        node_id = request.GET.get("node_id", None)
        dept_id = request.GET.get("dept_id", None)
        if node_id == 'null':
            # 应用服务器 界面初始化，未选择部门或应用，返回空列表
            obj_list = Server.objects.filter(id=-1)
        elif node_id:
            if re.match(r'a\d+', node_id):
                # node_id 为 a+数字，则说明点击的是具体App，否则点击的是部门
                app_list = App.objects.filter(id=node_id[1:])
            else:
                # node_id 遍历其所有子部门，列出该部门以及包含子部门所有app
                sub_dept_ids = get_total_dept_child_node_id(node_id)
                app_list = App.objects.filter(biz_mgt_dept__id__in=sub_dept_ids)
            if app_env:
                if app_env == "prod":
                    obj_list = Server.objects.filter(Q(app__in=app_list) | Q(pre_app__in=app_list)).filter(
                        app_env__in=['prod', 'beta']).exclude(status__in=['deleted', 'ots']).distinct().order_by(sort_name)
                else:
                    obj_list = Server.objects.filter(Q(app__in=app_list) | Q(pre_app__in=app_list)).filter(
                        app_env=app_env).exclude(status__in=['deleted', 'ots']).distinct().order_by(sort_name)
            else:
                obj_list = Server.objects.filter(Q(app__in=app_list) | Q(pre_app__in=app_list)).exclude(status__in=['deleted', 'ots']).distinct().order_by(sort_name)
        elif dept_id is not None:
            # dept_id 为空，也进入该代码中
            pct_range = request.GET.get("pct_range", "0-100%").replace('%', '').split("-")
            if dept_id == "":
                obj_list = Server.objects.filter(
                    mem_used__gte=pct_range[0], mem_used__lte=pct_range[1]).exclude(
                    status__in=['deleted', 'ots']).distinct().order_by(sort_name)
            else:
                sub_dept_ids = get_total_dept_child_node_id(dept_id)
                obj_list = Server.objects.filter(
                    department_id__in=sub_dept_ids, mem_used__gte=pct_range[0], mem_used__lte=pct_range[1]).exclude(
                    status__in=['deleted', 'ots']).distinct().order_by(sort_name)
        else:
            # 虚拟机、物理机管理界面
            idc_id = request.GET.get("idc_id", '')
            status = request.GET.get("status", '')
            if idc_id == '':
                if status == '':
                    # 未筛选 IDC 和 主机状态，则默认排除 deleted和ots状态的主机
                    if is_vm is None:
                        obj_list = Server.objects.exclude(status__in=['deleted', 'ots']).order_by(sort_name)
                    else:
                        obj_list = Server.objects.filter(is_vm=is_vm).exclude(status__in=['deleted', 'ots']).order_by(sort_name)
                else:
                    if is_vm is None:
                        obj_list = Server.objects.filter(status=status).order_by(sort_name)
                    else:
                        obj_list = Server.objects.filter(status=status).filter(is_vm=is_vm).order_by(sort_name)
            else:
                if status == '':
                    if is_vm is None:
                        obj_list = Server.objects.filter(idc__id=idc_id).exclude(status__in=['deleted', 'ots']).order_by(sort_name)
                    else:
                        obj_list = Server.objects.filter(idc__id=idc_id).filter(is_vm=is_vm).exclude(status__in=['deleted', 'ots']).order_by(sort_name)
                else:
                    if is_vm is None:
                        obj_list = Server.objects.filter(idc__id=idc_id).filter(status=status).order_by(sort_name)
                    else:
                        obj_list = Server.objects.filter(idc__id=idc_id).filter(status=status).filter(is_vm=is_vm).order_by(sort_name)

        search = request.GET.get("search", None)
        if search is not None:
            ips = Ip.objects.filter(ip__contains=search)
            server_ids = [nic.server.id for ip in ips for nic in ip.nic_set.all()]
            obj_list = obj_list.filter(Q(id__in=server_ids) | Q(hostname__contains=search) |
                                       Q(applicant__contains=search) | Q(product_name__contains=search) |
                                       Q(login_address__contains=search) | Q(manage_address__contains=search) |
                                       Q(cabinet__name__contains=search) | Q(sn__contains=search) |
                                       Q(comment__contains=search) |
                                       Q(pre_app__app_code__contains=search) |
                                       Q(app__app_code__contains=search)).distinct()

        result = list()
        if node_id is not None:
            # 返回按部门或App查看的服务器信息
            for o in obj_list[offset:(offset + limit)]:
                ips = get_ips_by_server_id(o.id)
                apps = [a.app_code for a in o.app.all()]
                pre_apps = [a.app_code for a in o.pre_app.all()]
                apps_detail = """已部署应用：{}\n待部署应用：{}""".format(' '.join(apps), ' '.join(pre_apps))
                result.append({
                    'id': o.id,
                    'aid': o.asset_id,
                    'hn': o.hostname,
                    'ct': o.cpu_total,
                    'cu': o.cpu_used,
                    'mt': o.mem_total,
                    'mu': o.mem_used,
                    'disk': o.disk,
                    'la': o.login_address,
                    'pi': o.parent_id,
                    'apt': o.applicant,
                    'stat': o.status,
                    'dlc': o.date_last_checked,
                    'biz': o.department.dept_name if o.department else "未指定",
                    'ips': ' '.join(ips),
                    'app_env': o.get_app_env_display(),
                    'apps': ' '.join(apps),
                    'pre_apps': ' '.join(pre_apps),
                    'apps_detail': apps_detail
                })
        elif is_vm == '0':
            # 返回物理机信息
            for o in obj_list[offset:(offset + limit)]:
                ips = get_ips_by_server_id(o.id)
                cpu_allocated = 0
                for s in Server.objects.filter(parent_id=o.id):
                    cpu_allocated += s.cpu_total if s.cpu_total else 0
                maint = ['%s %s %s' % (m.created_date, m.user.display, m.content) for m in Maintenance.objects.filter(server=o)]
                result.append({
                    'id': o.id,
                    'aid': o.asset_id,
                    'hn': o.hostname,
                    'sn': o.sn,
                    'uuid': o.uuid,
                    'ct': o.cpu_total,
                    'cu': o.cpu_used,
                    'ca': cpu_allocated,
                    'mt': o.mem_total,
                    'mu': o.mem_used,
                    'disk': o.disk,
                    'os': o.os,
                    'la': o.login_address,
                    'ma': o.manage_address,
                    'mod': o.model,
                    'mfr': o.manufacturer,
                    'pn': o.product_name,
                    'vc': o.vm_count,
                    'idc': o.idc.idc_name if o.idc else '-',
                    'cab': o.cabinet.name if o.cabinet else '-',
                    'cp': o.cabinet_pos,
                    'stat': o.status,
                    'rd': o.release_date,
                    'td': o.trade_date,
                    'ed': o.expired_date,
                    'biz': o.department.dept_name if o.department else "未指定",
                    'dc': o.date_created,
                    'dlc': o.date_last_checked,
                    'cmt': o.comment,
                    'maint': '\n'.join(maint),
                    'ips': ' '.join(ips)
                })
        else:
            # 返回虚拟机信息
            for o in obj_list[offset:(offset + limit)]:
                ips = get_ips_by_server_id(o.id)
                # 获取宿主机的ip
                parent_ips = get_ips_by_server_id(o.parent_id)
                apps = [a.app_code for a in o.app.all()]
                result.append({
                    'id': o.id,
                    'aid': o.asset_id,
                    'hn': o.hostname,
                    'sn': o.sn,
                    'uuid': o.uuid,
                    'ct': o.cpu_total,
                    'cu': o.cpu_used,
                    'mt': o.mem_total,
                    'mu': o.mem_used,
                    'disk': o.disk,
                    'os': o.os,
                    'mfr': o.manufacturer,
                    'pn': o.product_name,
                    'iv': o.is_vm,
                    'pi': o.parent_id,
                    'apt': o.applicant,
                    'stat': o.status,
                    'dc': o.date_created,
                    'cmt': o.comment,
                    'dlc': o.date_last_checked,
                    'biz': o.department.dept_name if o.department else "未指定",
                    'ips': ' '.join(ips),
                    'pips': ' '.join(parent_ips),
                    'app_env': o.get_app_env_display(),
                    'apps': ' '.join(apps)
                })
        res = {"total": obj_list.count(), "rows": result}
        return self.render_json_response(res)

    def post(self, request):
        if not request.user.has_perm('auth.perm_cmdb_asset_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        post_data = request.POST.copy()
        ip = post_data.get('ip')
        if ip:
            segment_id = post_data.get('segment')
            segment = NetworkSegment.objects.get(id=segment_id)
            if segment.segment != str(IP(ip).make_net(segment.netmask).net()):
                res = {'code': 1, 'errmsg': '此ip不在该网段内！'}
                return self.render_json_response(res)
            mac_address = post_data.get('mac_address').strip()
            if not re.match(r'([a-fA-F0-9]{2}[:-]){5}[a-fA-F0-9]{2}', mac_address, re.I):
                res = {'code': 1, 'errmsg': '请认真填写mac地址！'}
                return self.render_json_response(res)
        sn = post_data.get('sn')
        if sn and Server.objects.filter(sn=sn).exists():
            server = Server.objects.get(sn=sn)
            if post_data.get('hostname'):
                server.hostname = post_data.get('hostname')
            if post_data.get('idc'):
                server.idc_id = post_data.get('idc')
            if post_data.get('login_address'):
                server.login_address = post_data.get('login_address')
            if post_data.get('manage_address'):
                server.manage_address = post_data.get('manage_address')
            if post_data.get('supplier'):
                server.supplier = post_data.get('supplier')
            if post_data.get('supplier_phone'):
                server.supplier_phone = post_data.get('supplier_phone')
            if post_data.get('trade_date'):
                server.trade_date = post_data.get('trade_date')
            if post_data.get('expired_date'):
                server.expired_date = post_data.get('expired_date')
            if post_data.get('model'):
                server.model = post_data.get('model')
            if post_data.get('cabinet'):
                server.cabinet_id = post_data.get('cabinet')
            if post_data.get('cabinet_pos'):
                server.cabinet_pos = post_data.get('cabinet_pos')
            if post_data.get('product_name'):
                server.product_name = post_data.get('product_name')
            if post_data.get('applicant'):
                server.applicant = post_data.get('applicant')
            if post_data.get('comment'):
                server.comment = post_data.get('comment')
            server.save()
            if ip:
                ip = Ip.objects.get_or_create(segment=segment, ip=ip)[0]
                if Nic.objects.filter(mac_address=mac_address).exists():
                    nic = Nic.objects.get(mac_address=mac_address)
                    if nic.server_id == server.id:
                        pass
                    else:
                        Nic.objects.filter(mac_address=mac_address).delete()
                nic = Nic.objects.create(nic_name=post_data.get('hostname'), mac_address=mac_address, server=server)
                nic.ip.add(ip)
                nic.save()
            res = {'code': 0, 'result': '你想要添加的主机已存在，已修改其属性值！'}
        else:
            post_data['is_vm'] = int(post_data.get('is_vm'))
            if post_data.get('is_vm') == 0:
                form = PhysicalServerForm(post_data)
            else:
                form = VirtualServerForm(post_data)
            if form.is_valid():
                server = form.save()
                if ip:
                    ip = Ip.objects.get_or_create(segment=segment, ip=ip)[0]
                    Nic.objects.filter(mac_address=mac_address).delete()
                    nic = Nic.objects.create(nic_name=post_data.get('hostname'), mac_address=mac_address, server=server)
                    nic.ip.add(ip)
                res = {'code': 0, 'result': '添加成功！'}
            else:
                # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
                res = {'code': 1, 'errmsg': form.errors}
        return self.render_json_response(res)


class ServerDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_asset_view'

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            p = Server.objects.get(pk=pk)
            ip, mac_address, segment, vlan = None, None, None, None
            for nic in Nic.objects.filter(server=p):
                mac_address = nic.mac_address
                for ip in nic.ip.all():
                    segment = ip.segment_id
                    vlan = ip.segment.vlan_id
                    ip = ip.ip

            result = {
                'id': p.id, 'hostname': p.hostname, 'sn': p.sn, 'uuid': p.uuid, 'cpu_total': p.cpu_total,
                'cpu_used': p.cpu_used, 'mem_total': p.mem_total, 'mem_used': p.mem_used, 'disk': p.disk,
                'os': p.os, 'login_address': p.login_address, 'manage_address': p.manage_address,
                'product_name': p.product_name, 'release_date': p.release_date, 'trade_date': p.trade_date,
                'expired_date': p.expired_date, 'supplier': p.supplier, 'supplier_phone': p.supplier_phone,
                'is_vm': p.is_vm, 'vm_count': p.vm_count, 'parent_id': p.parent_id, 'model': p.model, 'idc_id': p.idc_id,
                'cabinet_id': p.cabinet_id, 'cabinet_pos': p.cabinet_pos, 'applicant': p.applicant, 'cmt': p.comment,
                'status': p.status, 'date_created': p.date_created, 'date_last_checked': p.date_last_checked,
                'department_id': p.department_id, 'ip': ip, 'mac_address': mac_address, 'segment_id': segment, 'vlan_id': vlan
            }
            res = {'code': 0, 'result': result}
        except Server.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        if not request.user.has_perm('auth.perm_cmdb_asset_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法修改！'})
        pk = kwargs.get('pk')
        p = get_object_or_404(Server, pk=pk)
        post_data = QueryDict(request.body).copy()
        if 'maint' in post_data:
            Maintenance.objects.create(server=p, content=post_data['content'], user=request.user)
            res = {'code': 0, 'result': '添加成功！'}
            return JsonResponse(res, safe=True)
        ip = post_data.get('ip')
        if ip:
            idc = IDC.objects.get(id=post_data['idc'])
            vlan = VLan.objects.get(id=post_data['vlan'])
            ipo = get_or_create_ip_obj(idc.idc_name, vlan.vlan_num, ip)
            segment_id = post_data.get('segment')
            segment = NetworkSegment.objects.get(id=segment_id)
            if segment.segment != str(IP(ip).make_net(segment.netmask).net()):
                res = {'code': 1, 'errmsg': '此ip不在该网段内！'}
                return self.render_json_response(res)
            mac_address = post_data.get('mac_address').strip()
            if not re.match(r'([a-fA-F0-9]{2}[:-]){5}[a-fA-F0-9]{2}', mac_address, re.I):
                res = {'code': 1, 'errmsg': '请认真填写mac地址！'}
                return self.render_json_response(res)

            if Nic.objects.filter(mac_address=mac_address, ip=ipo).exists():
                for nic in Nic.objects.filter(mac_address=mac_address, ip=ipo):
                    # 说明修改了该资产的mac和ip。网卡表关联新该服务器
                    if nic.server != p:
                        nic.server = p
                        nic.save()
            elif Nic.objects.filter(mac_address=mac_address).exists():
                nic = Nic.objects.get(mac_address=mac_address)
                nic.ip.add(ipo)
            else:
                nic = Nic.objects.create(nic_name=p.hostname, mac_address=mac_address, server=p)
                nic.ip.add(ipo)

        post_data['is_vm'] = int(post_data.get('is_vm'))
        if post_data.get('is_vm') == 0:
            form = PhysicalServerForm(post_data, instance=p)
        else:
            form = VirtualServerForm(post_data, instance=p)
        if form.is_valid():
            form.save()
            res = {"code": 0, "result": "更新成功"}
        else:
            res = {"code": 1, "errmsg": form.errors}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        if not self.request.user.is_superuser:
            res = {"code": 1, "errmsg": "只有超级管理才能删除服务器，你可以执行下架！"}
            return JsonResponse(res, safe=True)
        pk = kwargs.get('pk')
        try:
            obj = Server.objects.get(pk=pk)
            obj.status = 'deleted'
            obj.app.clear()
            obj.pre_app.clear()
            obj.save()
            res = {"code": 0, "result": "删除成功"}
        except Server.DoesNotExist:
            res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)


@method_decorator(csrf_exempt, name='dispatch')
class ServerTemplateView(PermissionRequiredMixin, JSONResponseMixin, View):
    permission_required = 'auth.perm_cmdb_asset_edit'

    def get(self, request, *args, **kwargs):
        try:
            filename = 'server_template.xls'
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
        attr = ['idc', 'ip', 'hostname', 'login_address', 'manage_address', 'model', 'sn', 'trade_date', 'expired_date',
                'cabinet', 'cabinet_pos', 'supplier', 'supplier_phone', 'applicant', 'comment']
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
                    elif ctype == 2 and cell % 1 == 0:          # 如果是整形
                        cell = int(cell)
                    elif ctype == 3:                           # 转成datetime对象
                        date_value = xlrd.xldate_as_tuple(cell, data.datemode)
                        cell = datetime.date(*date_value[:3]).strftime('%Y-%m-%d')
                    elif ctype == 4:
                        cell = True if cell == 1 else False
                    row.append(cell)
                dict_raw = dict(zip(attr, row))
                if not (dict_raw['idc'] and dict_raw['ip']):
                    # idc 或 ip列值为空，则无法确定主机
                    failed.append('{} {}行：IDC和IP字段是必填项'.format(file_name, str(i + 1)))
                    continue
                try:
                    ip, idc, cabinet = dict_raw.pop('ip').strip(), dict_raw.pop('idc').strip(), dict_raw.pop('cabinet')
                    if IDC.objects.filter(idc_name=idc).exists():
                        dict_raw['idc'] = IDC.objects.get(idc_name=idc)
                    else:
                        failed.append('{} {}行：该IDC "{}"未找到。'.format(file_name, str(i + 1), idc))
                        continue
                    ipo = Ip.objects.filter(segment__vlan__idc__idc_name=idc).filter(ip=ip)
                    if not ipo:
                        failed.append('{} {}行：IDC {} 中IP "{}"未找到。'.format(file_name, str(i + 1), idc, ip))
                        continue
                    server_ids = [nic.server.id for nic in Nic.objects.filter(ip=ipo[0])]
                    if not server_ids:
                        failed.append('{} {}行：IP "{}"未绑定主机。'.format(file_name, str(i + 1), ip))
                        continue

                    if not Server.objects.filter(id__in=server_ids).exists():
                        failed.append('{} {}行：IP "{}"主机已不存在。'.format(file_name, str(i + 1), ip))
                        continue

                    if cabinet:
                        if Cabinet.objects.filter(name=cabinet).exists():
                            dict_raw['cabinet'] = Cabinet.objects.get(name=cabinet)
                        else:
                            failed.append('{} {}行：该机柜 "{}"未找到。'.format(file_name, str(i + 1), cabinet))
                            continue

                    for key in ['hostname', 'login_address', 'manage_address', 'model', 'sn', 'trade_date',
                                'expired_date', 'cabinet_pos', 'supplier', 'supplier_phone', 'applicant', 'comment']:
                        if not dict_raw[key]:
                            dict_raw.pop(key)
                    # print(server_ids, dict_raw)
                    Server.objects.filter(id__in=server_ids).update(**dict_raw)
                    updated.append('{} {}行：{}'.format(file_name, str(i + 1), ip))

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

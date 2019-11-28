# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, F
from django.http import QueryDict, JsonResponse
from common.mixins import JSONResponseMixin

from cmdb.models.base import VLan, IDC, NetworkSegment, Ip
from cmdb.models.asset import Server, NetDevice
from cmdb.forms import VLanForm


class VlanView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_vlan_view'
    template_name = "cmdb/vlan.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': 'Vlan',
            'idc_list': IDC.objects.all()
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class VLanListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_vlan_view'

    def get(self, request, **kwargs):
        limit = request.GET.get('limit')
        offset = request.GET.get('offset')
        idc_id = request.GET.get("idc_id", '')
        sort_order = request.GET.get("sortOrder", '')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name
        if idc_id == '':
            obj_list = VLan.objects.get_queryset().order_by(sort_name)
        else:
            obj_list = VLan.objects.filter(idc_id=idc_id).order_by(sort_name)

        search = request.GET.get("search", '')
        if search:
            obj_list = obj_list.filter(Q(idc__idc_name=search) |
                                       Q(vlan_num__contains=search) |
                                       Q(comment__contains=search)).distinct()

        total = obj_list.count()
        if limit and offset:
            obj_list = obj_list[int(offset):int(offset + limit)].values("id", "idc_id", "idc__idc_name", "vlan_num", "comment")
        else:
            obj_list = obj_list.values("id", "idc_id", "idc__idc_name", "vlan_num", "comment")
        res = {"total": total, "rows": [o for o in obj_list]}
        return self.render_json_response(res)

    def post(self, request):
        if not request.user.has_perm('auth.perm_cmdb_vlan_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        form = VLanForm(request.POST)
        if form.is_valid():
            form.save()
            res = {'code': 0, 'result': '添加成功！'}
        else:
            res = {'code': 1, 'errmsg': form.errors}
        return self.render_json_response(res)


class VlanDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_vlan_view', 'auth.perm_cmdb_vlan_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            o = VLan.objects.get(pk=pk)
            result = {
                'id': o.id,
                'vlan_num': o.vlan_num,
                'idc': o.idc_id,
                'comment': o.comment
            }
            res = {'code': 0, 'result': result}
        except VLan.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        p = get_object_or_404(VLan, pk=pk)
        old_idc_id = p.idc_id
        form = VLanForm(QueryDict(request.body), instance=p)
        if form.is_valid():
            vlan = form.save()
            if vlan.idc_id != old_idc_id:
                # 当vlan更新了IDC，则属于该vlan下的 segmeng、ip、server都需要修改idc字段
                for seg in NetworkSegment.objects.filter(vlan_id=p.id):
                    for ipo in Ip.objects.filter(segment=seg):
                        server_ids = [nic.server.id for nic in ipo.nic_set.all()]
                        Server.objects.filter(id__in=server_ids).update(**{'idc_id': ipo.segment.vlan.idc_id})

                        NetDevice.objects.filter(ip=ipo).update(**{'idc_id': ipo.segment.vlan.idc_id})

            res = {"code": 0, "result": "更新成功"}
        else:
            res = {"code": 1, "errmsg": form.errors}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = VLan.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)

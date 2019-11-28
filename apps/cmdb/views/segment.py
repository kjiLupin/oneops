# -*- coding: utf-8 -*-
from IPy import IP
from django.shortcuts import render, get_object_or_404
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, F
from django.http import QueryDict, JsonResponse
from common.mixins import JSONResponseMixin

from cmdb.models.base import IDC, VLan, NetworkSegment, Ip
from cmdb.models.asset import Server, NetDevice
from cmdb.forms import NetworkSegmentForm


vlan_map_key = {'id': 'id', 'in': 'vlan__idc__idc_name', 'vl': 'vlan__vlan_num', 'seg': 'segment',
                'nm': 'netmask', 'cmt': 'comment'}


class SegmentView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_segment_view'
    template_name = "cmdb/segment.html"

    def get_context_data(self, **kwargs):
        idc_list = IDC.objects.all()
        context = {
            'path1': 'CMDB',
            'path2': '网段',
            'idc_list': idc_list,
            'vlan_list': [] if not idc_list else VLan.objects.filter(idc=idc_list[0])
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SegmentListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_segment_view'

    def get(self, request, **kwargs):
        limit = request.GET.get('limit')
        offset = request.GET.get('offset')

        sort_order = request.GET.get("sortOrder", 'asc')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = vlan_map_key.get(sort_name, 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        idc_id = request.GET.get("idc_id", '')
        if idc_id:
            obj_list = NetworkSegment.objects.filter(vlan__idc_id=idc_id).order_by(sort_name)
        else:
            obj_list = NetworkSegment.objects.get_queryset().order_by(sort_name)

        vlan_id = request.GET.get("vlan_id", '')
        if vlan_id:
            obj_list = obj_list.filter(vlan_id=vlan_id)

        search = request.GET.get("search", None)
        if search is not None:
            obj_list = obj_list.filter(Q(segment__contains=search) | Q(comment__contains=search)).distinct()

        res = list()
        total_count = obj_list.count()
        if limit and offset:
            obj_list = obj_list[int(offset):int(offset + limit)]

        for o in obj_list:
            try:
                ip_total = IP(o.segment).make_net(o.netmask).len() - 2
                ip_used = Ip.objects.filter(segment=o).count()
                ip_usable = int(ip_total) - int(ip_used)
                res.append({'id': o.id, 'iid': o.vlan.idc_id, 'vid': o.vlan.id, 'in': o.vlan.idc.idc_name,
                            'it': ip_total, 'used': ip_used, 'usable': ip_usable, 'vl': o.vlan.vlan_num,
                            'seg': o.segment, 'nm': o.netmask, 'cmt': o.comment})
            except Exception as e:
                print(e, o.segment, o.vlan_id)
        res = {"total": total_count, "rows": res}
        return self.render_json_response(res)

    def post(self, request):
        if not request.user.has_perm('auth.perm_cmdb_segment_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        post_data = request.POST.copy()
        idc_id = post_data.get('idc')
        vlan_id = post_data.get('vlan')
        if idc_id and vlan_id:
            form = NetworkSegmentForm(post_data)
            if form.is_valid():
                form.save()
                res = {'code': 0, 'result': '添加成功！'}
            else:
                # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
                res = {'code': 1, 'errmsg': form.errors}
        else:
            res = {'code': 1, 'errmsg': 'IDC和VLan是必选项！'}
        return self.render_json_response(res)


class SegmentDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_segment_view', 'auth.perm_cmdb_segment_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            p = NetworkSegment.objects.get(pk=pk)
            value = {'id': p.id, 'idc': p.vlan.idc_id, 'vlan': p.vlan_id,
                     'segment': p.segment, 'netmask': p.netmask, 'comment': p.comment}
            res = {'code': 0, 'result': value}
        except NetworkSegment.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        post_data = QueryDict(request.body).copy()
        vlan_id = post_data.get('vlan')
        if vlan_id:
            p = get_object_or_404(NetworkSegment, pk=pk)
            old_idc_id = p.vlan.idc_id
            form = NetworkSegmentForm(post_data, instance=p)
            if form.is_valid():
                ns = form.save()
                if ns.vlan.idc_id != old_idc_id:
                    # 当网段更换vlan后，假如旧vlan和新vlan不是同一个idc，则需更新该网段下所有服务器的idc属性
                    for ipo in Ip.objects.filter(segment=ns):
                        server_ids = [nic.server.id for nic in ipo.nic_set.all()]
                        Server.objects.filter(id__in=server_ids).update(**{'idc_id': ipo.segment.vlan.idc_id})

                        NetDevice.objects.filter(ip=ipo).update(**{'idc_id': ipo.segment.vlan.idc_id})

                res = {"code": 0, "result": "更新成功"}
            else:
                res = {"code": 1, "errmsg": form.errors}
        else:
            res = {'code': 1, 'errmsg': 'IDC和VLan是必选项！'}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = NetworkSegment.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)

# -*- coding: utf-8 -*-
from IPy import IP
from django.shortcuts import render, get_object_or_404
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, F
from django.http import QueryDict, JsonResponse
from common.mixins import JSONResponseMixin

from cmdb.models.base import IDC, VLan, NetworkSegment, Ip
from cmdb.models.asset import Server, NetDevice, Nic
from cmdb.forms import IpForm
from cmdb.api.ip import get_mac_by_ip


ip_map_key = {'id': 'id', 'in': 'segment__vlan__idc__idc_name', 'vn': 'segment__vlan__vlan_num',
              'seg': 'segment__segment', 'ip': 'ip', 'cmt': 'comment'}


def get_ips_by_server_id(sid):
    nic_list = Nic.objects.filter(server__id=sid)
    ips = [ip.ip for nic in nic_list for ip in nic.ip.all()]
    return ips


class IpView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_ip_view'
    template_name = "cmdb/ip.html"

    def get_context_data(self, **kwargs):
        idc_list = IDC.objects.all()
        vlan_list = [] if not idc_list else VLan.objects.filter(idc=idc_list[0])
        segment_list = [] if not vlan_list else NetworkSegment.objects.filter(vlan=vlan_list[0])
        context = {
            'path1': 'CMDB',
            'path2': 'IP',
            'idc_list': idc_list,
            'vlan_list': vlan_list,
            'segment_list': segment_list
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class IpListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_ip_view'

    def get(self, request, **kwargs):
        side_menu_show = request.GET.get("side_menu_show", None)
        available = request.GET.get("available", None)
        idc_id = request.GET.get("idc_id", '')
        vlan_id = request.GET.get("vlan_id", '')
        segment_id = request.GET.get("segment_id", '')
        res = list()
        if side_menu_show is not None:
            # 用于网段管理页面 侧边栏显示Ip列表
            # filter_dict = {'segment_id': segment_id, 'vlan_id': vlan_id, 'idc_id': idc_id}
            try:
                segment = NetworkSegment.objects.get(id=segment_id)
                for ip in IP(segment.segment).make_net(segment.netmask)[1:-1]:
                    ret = dict()
                    if Ip.objects.filter(segment__id=segment_id, ip=str(ip)).exists():
                        ipo = Ip.objects.get(segment__id=segment_id, ip=str(ip))
                        # ip表中能查到，说明已经分配
                        if Nic.objects.filter(ip=ipo).exists():
                            # nic_ip 表中能查到，说明已经绑定网卡
                            ret["ip"], ret["is_used"] = str(ip), "used"
                        else:
                            ret["ip"], ret["is_used"] = str(ip), "allocated"
                    else:
                        ret["ip"], ret["is_used"] = str(ip), "unused"
                    res.append(ret)
            except Exception as e:
                print(e)
            return self.render_json_response(res)

        if available is not None:
            # 申请新ip时，返回未分配，或未绑定的ip地址
            try:
                segment = NetworkSegment.objects.get(id=segment_id)
                for ip in IP(segment.segment).make_net(segment.netmask)[1:-1]:
                    ipo = Ip.objects.filter(segment=segment).filter(ip=str(ip))
                    if ipo:
                        if Nic.objects.filter(ip=ipo[0]).exists():
                            pass
                        elif NetDevice.objects.filter(ip=ipo[0]).exists():
                            pass
                        else:
                            res.append(str(ip))
                    else:
                        res.append(str(ip))
            except Exception as e:
                print(e)
            return self.render_json_response(res)

        limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset'))

        sort_order = request.GET.get("sortOrder", 'asc')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = ip_map_key.get(sort_name, 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        if segment_id == '':
            if vlan_id:
                vlan = VLan.objects.get(id=vlan_id)
                segment_list = NetworkSegment.objects.filter(vlan=vlan)
                if segment_list:
                    segment_id = segment_list[0].id
            elif idc_id:
                vlan_list = VLan.objects.filter(idc_id=idc_id)
                if vlan_list:
                    vlan = vlan_list[0]
                    segment_list = NetworkSegment.objects.filter(vlan=vlan)
                    if segment_list:
                        segment_id = segment_list[0].id
            else:
                return self.render_json_response(res)

        filter_dict = {'segment_id': segment_id}
        if filter_dict:
            obj_list = Ip.objects.filter(**filter_dict).order_by(sort_name)
        else:
            obj_list = Ip.objects.get_queryset().order_by(sort_name)
        if vlan_id:
            obj_list = obj_list.filter(segment__vlan__id=vlan_id)
        if idc_id:
            obj_list = obj_list.filter(segment__vlan__idc__id=idc_id)

        search = request.GET.get("search", '')
        if search != '':
            nic_list = Nic.objects.filter(mac_address__contains=search)
            ip_ids = [ip.id for nic in nic_list for ip in nic.ip.all()]
            obj_list = obj_list.filter(Q(id__in=ip_ids) | Q(ip__contains=search) |
                                       Q(segment__segment__contains=search) |
                                       Q(comment__contains=search)).distinct()

        for o in obj_list[offset:(offset + limit)]:
            mac = get_mac_by_ip(o)
            res.append({'id': o.id, 'iid': o.segment.vlan.idc_id, 'vid': o.segment.vlan_id, 'sid': o.segment_id,
                        'in': o.segment.vlan.idc.idc_name, 'vl': o.segment.vlan.vlan_num,
                        'seg': o.segment.segment_prefix, 'ip': o.ip, 'mac': mac, 'cmt': o.comment})
        res = {"total": obj_list.count(), "rows": res}
        return self.render_json_response(res)

    def post(self, request):
        if not request.user.has_perm('auth.perm_cmdb_ip_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        post_data = request.POST.copy()
        idc_id = post_data.pop('idc')
        vlan_id = post_data.pop('vlan')
        segment_id = post_data.get('segment')
        if idc_id and vlan_id and segment_id:
            ip = post_data.get('ip')
            segment = NetworkSegment.objects.get(id=segment_id)
            if segment.segment != str(IP(ip).make_net(segment.netmask).net()):
                res = {'code': 1, 'errmsg': '此ip不在该网段内！'}
            else:
                form = IpForm(post_data)
                if form.is_valid():
                    form.save()
                    res = {'code': 0, 'result': '添加成功！'}
                else:
                    # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
                    res = {'code': 1, 'errmsg': form.errors}
        else:
            res = {'code': 1, 'errmsg': 'IDC和VLan和网段是必选项！'}
        return self.render_json_response(res)


class IpDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_ip_view', 'auth.perm_cmdb_ip_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            p = Ip.objects.get(pk=pk)
            value = {'id': p.id, 'idc': p.segment.vlan.idc_id, 'vlan': p.segment.vlan_id,
                     'segment': p.segment_id, 'ip': p.ip, 'comment': p.comment}
            res = {'code': 0, 'result': value}
        except Ip.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        post_data = QueryDict(request.body).copy()
        print(post_data)
        idc_id = post_data.get('idc')
        vlan_id = post_data.get('vlan')
        segment_id = post_data.get('segment')
        if idc_id and vlan_id and segment_id:
            p = get_object_or_404(Ip, pk=pk)
            segment = NetworkSegment.objects.get(id=segment_id)
            if segment.segment != str(IP(p.ip).make_net(segment.netmask).net()):
                res = {'code': 1, 'errmsg': '此ip不在该网段内！'}
            else:
                old_idc_id = p.segment.vlan.idc_id
                form = IpForm(post_data, instance=p)
                if form.is_valid():
                    ipo = form.save()
                    if ipo.segment.vlan.idc_id != old_idc_id:
                        # 当IP更换网段后，假如旧网段的idc和新网段不是同一个idc，则需更新该网段下所有服务器的idc属性
                        server_ids = [nic.server.id for nic in ipo.nic_set.all()]
                        Server.objects.filter(id__in=server_ids).update(**{'idc_id': ipo.segment.vlan.idc_id})

                        NetDevice.objects.filter(ip=ipo).update(**{'idc_id': ipo.segment.vlan.idc_id})

                    res = {"code": 0, "result": "更新成功"}
                else:
                    res = {"code": 1, "errmsg": form.errors}
        else:
            res = {'code': 1, 'errmsg': '网段是必选项！'}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = Ip.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)

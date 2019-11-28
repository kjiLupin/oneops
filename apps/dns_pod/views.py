# -*- coding: utf-8 -*-
import datetime
from django.views.generic import View, ListView, TemplateView
from django.shortcuts import render
from django.http import QueryDict, JsonResponse
from django.contrib.auth.decorators import permission_required
from django.db.models import Q, F
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin

from .models import Zone, Record, DnsLog
from .forms import ZoneForm, RecordForm
from accounts.models import User


@permission_required('auth.perm_dns_zone_view', raise_exception=True)
def zone(request):
    path1, path2 = "域名", "域名列表"
    return render(request, 'dns_pod/zone.html', locals())


class ZoneListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_dns_zone_view'

    def get(self, request, **kwargs):
        dns_type = request.GET.get("dns_type", None)
        if dns_type is None or dns_type == 'all':
            obj_list = Zone.objects.get_queryset().order_by('type')
        else:
            obj_list = Zone.objects.filter(type=dns_type).order_by('type')

        search = request.GET.get("search", None)
        if search is not None:
            obj_list = obj_list.filter(
                Q(domain_name__contains=search) | Q(type__contains=search) | Q(comment__contains=search))

        obj_list = obj_list.values("id", "domain_name", "type", "create_time", "comment")
        return self.render_json_response([o for o in obj_list])

    def post(self, request):
        if not request.user.has_perm('auth.perm_dns_zone_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        form = ZoneForm(request.POST)
        if form.is_valid():
            form.save()
            # 记录到日志
            zone_info = Zone.objects.get(domain_name=form.instance.domain_name, type=form.instance.type).__str__()
            DnsLog.objects.create(user=request.user, action='add', new_zone=zone_info)
            res = {'code': 0, 'result': '添加成功！'}
        else:
            # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
            res = {'code': 1, 'errmsg': form.errors}
        return self.render_json_response(res)


class ZoneDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_dns_zone_view', 'auth.perm_dns_zone_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        p = Zone.objects.filter(pk=pk)
        if p:
            obj_list = p.values("id", "domain_name", "type", "create_time", "comment")
            res = {'code': 0, 'result': [o for o in obj_list]}
        else:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            z = Zone.objects.get(pk=pk)
            update_data = QueryDict(request.body).dict()
            if Zone.objects.exclude(pk=pk).filter(type=z.type, domain_name=update_data['domain_name']).exists():
                res = {"code": 1, "errmsg": "相同环境类型，域名不能重复！"}
            else:
                # 保存，并记录修改日志
                old_zone_info = Zone.objects.get(pk=pk).__str__()

                Zone.objects.filter(pk=pk).update(**update_data)
                new_zone_info = Zone.objects.get(pk=pk).__str__()
                DnsLog.objects.create(user=request.user, action='edit', old_zone=old_zone_info, new_zone=new_zone_info)
                res = {"code": 0, "result": "更新成功"}
        except Zone.DoesNotExist:
            res = {"code": 1, "errmsg": "该记录不存在！"}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = Zone.objects.filter(pk=pk)
            if obj:
                # 记录到日志
                zone_info = obj[0].__str__()
                obj.delete()

                DnsLog.objects.create(user=self.request.user, action='delete', old_zone=zone_info)
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)


@permission_required('auth.perm_dns_record_view', raise_exception=True)
def record(request, **kwargs):
    domain_name, env = kwargs.get('domain_name'), kwargs.get('env')
    header_title = domain_name
    path1, path2 = "域名", "记录值"
    return render(request, 'dns_pod/record.html', locals())


class RecordListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_dns_record_view'

    def get(self, request, **kwargs):
        domain_name, env = kwargs.get('domain_name'), kwargs.get('env')
        r_type = request.GET.get("record_type", None)
        if r_type is None or r_type == 'all':
            obj_list = Record.objects.using('bind_{}'.format(env)).filter(zone=domain_name)
        else:
            obj_list = Record.objects.using('bind_{}'.format(env)).filter(zone=domain_name).filter(type=r_type)

        search = request.GET.get("search", None)
        if search is not None:
            obj_list = obj_list.filter(Q(host__contains=search) |Q(data__contains=search) |
                                       Q(status__contains=search) | Q(view__contains=search)).distinct()

        obj_list = obj_list.values("id", "zone", "host", "type", "data", "status", "ttl", "mx_priority")
        return self.render_json_response([o for o in obj_list])

    def post(self, request, **kwargs):
        if not request.user.has_perm('auth.perm_dns_record_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        env = kwargs.get('env')
        form = RecordForm(request.POST)
        if form.is_valid():
            post_data = QueryDict(request.body).dict()
            if "mx_priority" in post_data:
                if post_data['mx_priority']:
                    post_data['mx_priority'] = int(post_data['mx_priority'])
                else:
                    post_data.pop('mx_priority')
            Record.objects.using('bind_{}'.format(env)).create(**post_data)
            # 记录到日志
            record_info = Record.objects.using('bind_{}'.format(env)).get(zone=form.instance.zone,
                                                                          host=form.instance.host,
                                                                          data=form.instance.data).__str__()
            DnsLog.objects.create(user=request.user, action='add', new_record=record_info)
            res = {'code': 0, 'result': '添加解析成功'}
        else:
            # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
            res = {'code': 1, 'errmsg': form.errors}
        return JsonResponse(res, safe=True)


class RecordDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_dns_record_view', 'auth.perm_dns_record_edit')

    def put(self, request, *args, **kwargs):
        try:
            pk, env = kwargs.get('pk'), kwargs.get('env')
            p = Record.objects.using('bind_{}'.format(env)).get(pk=pk)
            form = RecordForm(request.POST, instance=p)
            if form.is_valid():
                # 保存，并记录修改日志
                old_record_info = Record.objects.using('bind_{}'.format(env)).get(domain_name=form.instance.zone,
                                                                                  host=form.instance.host,
                                                                                  data=form.instance.data).__str__()

                post_data = QueryDict(request.body).dict()
                if "mx_priority" in post_data:
                    if post_data['mx_priority']:
                        post_data['mx_priority'] = int(post_data['mx_priority'])
                    else:
                        post_data.pop('mx_priority')
                Record.objects.using('bind_{}'.format(env)).filter(pk=pk).update(**post_data)
                Record.objects.using('bind_{}'.format(env)).filter(pk=pk).update(serial=F('serial') + 1)

                new_record_info = Record.objects.using('bind_{}'.format(env)).get(domain_name=form.instance.zone,
                                                                                  host=form.instance.host,
                                                                                  data=form.instance.data).__str__()
                DnsLog.objects.create(user=request.user, action='edit', old_record=old_record_info, new_record=new_record_info)

                res = {"code": 0, "result": "更新成功", 'next_url': self.next_url}
            else:
                res = {"code": 1, "errmsg": form.errors, 'next_url': self.next_url}
        except Exception as e:
            res = {"code": 1, "errmsg": str(e), 'next_url': self.next_url}
        return self.render_json_response(res)

    def delete(self, *args, **kwargs):
        pk, env = kwargs.get('pk'), kwargs.get('env')
        try:
            obj = Record.objects.using('bind_{}'.format(env)).filter(pk=pk)
            if obj:
                # 记录到日志
                record_info = obj[0].__str__()
                obj.delete()
                DnsLog.objects.create(user=self.request.user, action='delete', old_record=record_info)

                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)


class DnsLogIndex(PermissionRequiredMixin, ListView):
    permission_required = 'auth.perm_dns_log_view'
    model = DnsLog
    template_name = 'dns_pod/dns_log.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': '域名配置',
            'path2': '操作记录',
            'user_list': [u["username"] for u in User.objects.all().values("username")]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DnsLogList(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_dns_log_view'

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset'))

        date_from = request.GET.get("date_from", None)
        date_to = request.GET.get("date_to", None)
        user = request.GET.get("user", None)
        dns_type = request.GET.get("type", None)
        zone = request.GET.get("zone", None)

        if date_from and date_to:
            date_from = datetime.datetime.strptime(date_from, 'mm/dd/yyyy')
            date_to = datetime.datetime.strptime(date_to, 'mm/dd/yyyy')
            obj_list = DnsLog.objects.filter(create_time__gte=date_from).filter(create_time__lte=date_to)
        elif date_from:
            date_from = datetime.datetime.strptime(date_from, 'mm/dd/yyyy')
            obj_list = DnsLog.objects.filter(create_time__gte=date_from)
        elif date_to:
            date_to = datetime.datetime.strptime(date_to, 'mm/dd/yyyy')
            obj_list = DnsLog.objects.filter(create_time__lte=date_to)
        else:
            seven_day_ago = datetime.datetime.now() + datetime.timedelta(days=-7)
            obj_list = DnsLog.objects.filter(create_time__gte=seven_day_ago)

        if user:
            obj_list = obj_list.filter(user__username=user)
        if zone:
            zone_info = '{}: {}'.format(dns_type, zone)
            obj_list = obj_list.filter(Q(new_zone=zone_info) | Q(old_zone=zone_info)).distinct()

        search = request.GET.get("search", None)
        if search:
            obj_list = obj_list.filter(Q(old_record__contains=search) |Q(new_record__contains=search) |
                                       Q(old_zone__contains=search) | Q(new_zone__contains=search)).distinct()
        result = list()
        for obj in obj_list[offset:(offset + limit)]:
            item = {
                'user': obj.user.display,
                'action': obj.action,
                'old_info': str(obj.old_zone or '') + str(obj.old_record or ''),
                'new_info': str(obj.new_zone or '') + str(obj.new_record or ''),
                'create_time': obj.create_time
            }
            result.append(item)
        res = {"total": obj_list.count(), "rows": result}
        return self.render_json_response(res)

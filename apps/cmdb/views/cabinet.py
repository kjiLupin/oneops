# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, F
from django.http import QueryDict, JsonResponse
from common.mixins import JSONResponseMixin

from cmdb.models.base import IDC, Cabinet
from cmdb.forms import CabinetForm


class CabinetView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_cabinet_view'
    template_name = "cmdb/cabinet.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': 'Cabinet',
            'idc_list': IDC.objects.all()
        }
        print(context)
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CabinetListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_cabinet_view'

    def get(self, request, **kwargs):
        idc_id = request.GET.get("idc_id", '')
        sort_order = request.GET.get("sortOrder", 'desc')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        if idc_id == '':
            obj_list = Cabinet.objects.get_queryset().order_by(sort_name)
        else:
            obj_list = Cabinet.objects.filter(idc_id=idc_id).order_by(sort_name)

        search = request.GET.get("search")
        if search:
            obj_list = obj_list.filter(Q(name__contains=search) | Q(power__contains=search)).distinct()

        result = list()
        for o in obj_list:
            result.append({
                'id': o.id,
                'name': o.name,
                'idc': o.idc.idc_name,
                'idc_id': o.idc_id,
                'power': o.power
            })
        return self.render_json_response(result)

    def post(self, request):
        if not request.user.has_perm('auth.perm_cmdb_cabinet_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        form = CabinetForm(request.POST)
        if form.is_valid():
            form.save()
            res = {'code': 0, 'result': '添加成功！'}
        else:
            res = {'code': 1, 'errmsg': form.errors}
        return self.render_json_response(res)


class CabinetDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_cabinet_view', 'auth.perm_cmdb_cabinet_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            o = Cabinet.objects.get(pk=pk)
            result = {
                'id': o.id,
                'name': o.name,
                'idc': o.idc_id,
                'power': o.power
            }
            res = {'code': 0, 'result': result}
        except Cabinet.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        p = get_object_or_404(Cabinet, pk=pk)
        form = CabinetForm(QueryDict(request.body), instance=p)
        if form.is_valid():
            form.save()
            res = {"code": 0, "result": "更新成功"}
        else:
            res = {"code": 1, "errmsg": form.errors}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = Cabinet.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)

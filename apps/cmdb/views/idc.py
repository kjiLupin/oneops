# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404
from django.views.generic import View, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q, F
from django.http import QueryDict, JsonResponse
from common.mixins import JSONResponseMixin

from cmdb.models import IDC
from cmdb.forms import IDCForm


class IDCView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_idc_view'
    template_name = "cmdb/idc.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'CMDB',
            'path2': 'IDC'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class IDCListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_cmdb_idc_view'

    def get(self, request, **kwargs):
        sort_order = request.GET.get("sortOrder", 'desc')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name
        search = request.GET.get("search", None)
        if search is None:
            obj_list = IDC.objects.get_queryset().order_by(sort_name)
        else:
            obj_list = IDC.objects.filter(Q(idc_name__contains=search) | Q(address__contains=search) |
                                          Q(comment__contains=search)).distinct()

        obj_list = obj_list.values("id", "idc_name", "address", "phone", "email", "cabinet_num", "comment")
        return self.render_json_response([o for o in obj_list])

    def post(self, request):
        if not request.user.has_perm('auth.perm_cmdb_idc_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        form = IDCForm(request.POST)
        if form.is_valid():
            form.save()
            res = {'code': 0, 'result': '添加成功！'}
        else:
            # form.errors 会把验证不通过的信息以对象的形式传到前端，前端直接渲染即可
            res = {'code': 1, 'errmsg': form.errors}
        return self.render_json_response(res)


class IDCDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_cmdb_idc_view', 'auth.perm_cmdb_idc_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        p = IDC.objects.filter(pk=pk)
        if p:
            obj_list = p.values("id", "idc_name", "address", "phone", "email", "cabinet_num", "comment")
            res = {'code': 0, 'result': [o for o in obj_list]}
        else:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        p = get_object_or_404(IDC, pk=pk)
        form = IDCForm(QueryDict(request.body), instance=p)
        if form.is_valid():
            form.save()
            res = {"code": 0, "result": "更新成功"}
        else:
            res = {"code": 1, "errmsg": form.errors}
        return JsonResponse(res, safe=True)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = IDC.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return JsonResponse(res, safe=True)

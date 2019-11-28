# -*- coding: utf-8 -*-
import re
from django.views.generic import TemplateView
from django.shortcuts import render
from django.http import QueryDict
from django.contrib.auth.decorators import permission_required
from django.db.models import Q, F
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from common.mixins import JSONResponseMixin


@permission_required('auth.perm_accounts_perm_view', raise_exception=True)
def perm(request):
    path1, path2 = "授权管理", "权限项"
    return render(request, 'accounts/perm.html', locals())


class PermListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    """
    'perm_' 作为自定义的Permission的前缀，跟auth.Permission自带的权限区分开，方便阅读。
    """
    permission_required = 'auth.perm_accounts_perm_view'

    def get(self, request, **kwargs):
        search = request.GET.get("search", None)
        if search is not None:
            obj_list = Permission.objects.filter(codename__startswith='perm_').filter(Q(codename__contains=search) |
                                                                                      Q(name__contains=search)).distinct()
        else:
            obj_list = Permission.objects.filter(codename__startswith='perm_')
        res = list()
        for p in obj_list.order_by('codename'):
            res.append({"id": p.id, "codename": re.sub('perm_', '', p.codename), "name": p.name})
        return self.render_json_response(res)

    def post(self, request):
        try:
            update_data = QueryDict(request.body).dict()
            if not re.match(r'perm_', update_data['codename']):
                update_data['codename'] = 'perm_' + update_data['codename']
            content_type = ContentType.objects.get_for_model(Permission)
            update_data['content_type'] = content_type
            Permission.objects.create(**update_data)
            res = {'code': 0, 'result': '添加成功！'}
        except Exception as e:
            res = {'code': 1, 'errmsg': str(e)}
        return self.render_json_response(res)


class PermDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_accounts_perm_view', 'auth.perm_accounts_perm_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            p = Permission.objects.get(pk=pk)
            res = {'code': 0, 'result': {"id": p.id, "codename": re.sub('perm_', '', p.codename), "name": p.name}}
        except Permission.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            p = Permission.objects.get(pk=pk)
            update_data = QueryDict(request.body).dict()
            if Permission.objects.exclude(pk=pk).filter(codename='perm_' + update_data['codename']).exists():
                res = {"code": 1, "errmsg": "codename 不能重复！"}
            else:
                p.codename = 'perm_' + update_data['codename']
                p.name = update_data['name']
                p.save()
                res = {"code": 0, "result": "更新成功"}
        except Permission.DoesNotExist:
            res = {"code": 1, "errmsg": "该记录不存在！"}
        return self.render_json_response(res)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = Permission.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该记录！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return self.render_json_response(res)


@permission_required('auth.perm_accounts_perm_view', raise_exception=True)
def perm_group(request):
    path1, path2 = "授权管理", "权限项组"
    return render(request, 'accounts/perm_group.html', locals())


class PermGroupListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_accounts_perm_view'

    def get(self, request, **kwargs):
        search = request.GET.get("search", None)
        if search is not None:
            obj_list = Group.objects.filter(name__contains=search)
        else:
            obj_list = Group.objects.get_queryset()
        res = list()
        for o in obj_list:
            res.append({
                "id": o.id,
                "name": o.name,
                "perms": [p.name for p in o.permissions.all()]
            })
        return self.render_json_response(res)

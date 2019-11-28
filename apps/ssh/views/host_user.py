
import re
import simplejson as json
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.http import QueryDict
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin

from cmdb.models.asset import Server
from ssh.models.host_user import HostUser, HostUserAsset
from ssh.forms import HostUserForm


class HostUserOverviewView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_ssh_host_user_view'
    template_name = "ssh/host_user_overview.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'SSH',
            'path2': '系统用户总览'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class HostUserOverviewListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_ssh_host_user_view'

    def get(self, request, **kwargs):
        search = request.GET.get("search", '')
        if search:
            obj_list = HostUser.objects.filter(Q(username__contains=search) |
                                               Q(description__contains=search)).values("username").distinct()
        else:
            obj_list = HostUser.objects.get_queryset().values("username").distinct()
        host_user = list()
        for obj in obj_list:
            host_user.append({
                "username": obj["username"],
                "count": HostUser.objects.filter(username=obj['username']).count()
            })
        return self.render_json_response(host_user)


class HostUserView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_ssh_host_user_view'
    template_name = "ssh/host_user.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'SSH',
            'path2': 'Host User',
            'username': kwargs.pop('username')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class HostUserListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_ssh_host_user_view'

    def get(self, request, **kwargs):
        username = kwargs.pop('username', None)
        if username is None:
            res = list()
        else:
            search = request.GET.get("search", '')
            if search:
                obj_list = HostUser.objects.filter(username=username).filter(Q(username__contains=search) |
                                                                             Q(description__contains=search)
                                                                             ).distinct().order_by('-version')
            else:
                obj_list = HostUser.objects.filter(username=username).order_by('-version')
            res = list()
            for obj in obj_list:
                res.append({
                    "id": obj.id,
                    "username": obj.username,
                    "login_type": obj.get_login_type_display(),
                    "version": obj.version,
                    "active": obj.active,
                    "description": obj.description,
                    "creation_date": obj.creation_date,
                    "bound_asset_num": HostUserAsset.objects.filter(host_user=obj).count()
                })
        return self.render_json_response(res)


class HostUserDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_ssh_host_user_view', 'auth.perm_ssh_host_user_edit')

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            if HostUser.objects.filter(pk=pk).delete():
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return self.render_json_response(res)


class HostUserAssetDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_ssh_host_user_view', 'auth.perm_ssh_host_user_edit')

    def get(self, request, **kwargs):
        hu_id = kwargs.get('hu_id')
        try:
            hu = HostUser.objects.get(pk=hu_id)
            asset_ids = [hua.asset_id for hua in HostUserAsset.objects.filter(host_user=hu)]
            bound = Server.objects.filter(id__in=asset_ids)
            unbound = Server.objects.exclude(id__in=asset_ids)
            result = {
                'id': hu.id,
                'username': hu.username,
                'login_type': hu.get_login_type_display(),
                'description': hu.description,
                'bound': [{"id": a.id, "hn": a.hostname} for a in bound],
                'unbound': [{"id": a.id, "hn": a.hostname} for a in unbound]
            }
            res = {'code': 0, 'result': result}
        except HostUser.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        try:
            hu_id = kwargs.get('hu_id')
            hu = HostUser.objects.get(id=hu_id)
            HostUserAsset.objects.filter(host_user=hu).delete()
            put_data = QueryDict(request.body, mutable=True)
            bound_list = put_data.pop('bound') if "bound" in put_data else list()
            for server_id in bound_list:
                s = Server.objects.get(id=server_id)
                HostUserAsset.objects.create(host_user=hu, asset=s)
            res = {'code': 0, 'result': '更新成功！'}
        except Exception as e:
            res = {'code': 1, 'errmsg': '%s' % str(e)}
        return self.render_json_response(res)

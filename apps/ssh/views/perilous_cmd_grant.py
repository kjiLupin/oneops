
import re
import simplejson as json
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic import TemplateView
from django.http import QueryDict
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin

from django.contrib.auth.models import Group
from ssh.models.perilous_command import CommandGroup, UserGroupCommand


class PerilousCmdGrantView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_ssh_perilous_cmd_grant_view'
    template_name = "ssh/perilous_cmd_grant.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': '高危命令',
            'path2': '用户组授权'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class PerilousCmdGrantListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_ssh_perilous_cmd_grant_view'

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset'))

        sort_order = request.GET.get("sortOrder", '')
        sort_name = "name" if sort_order == 'desc' else "-name"

        search = request.GET.get("search", '')
        if search:
            obj_list = Group.objects.filter(name__contains=search).order_by(sort_name)
        else:
            obj_list = Group.objects.get_queryset().order_by(sort_name)
        total = obj_list.count()
        res = list()
        for o in obj_list[offset:offset + limit]:
            ugcs = UserGroupCommand.objects.filter(user_group=o)
            command_group = [cg.name for ugc in ugcs for cg in ugc.command_group.all()]
            res.append({
                "ug_id": o.id,
                "user_group_name": o.name,
                "command_group": " ".join(command_group),
                "comment": ugcs[0].comment if ugcs else ""
            })
        res = {"total": total, "rows": res}
        return self.render_json_response(res)


class PerilousCmdGrantDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_ssh_perilous_cmd_grant_view', 'auth.perm_ssh_perilous_cmd_grant_edit')

    def get(self, request, **kwargs):
        ug_id = kwargs.get('ug_id')
        try:
            user_group = Group.objects.get(id=ug_id)
            ugcs = UserGroupCommand.objects.filter(user_group=user_group)

            white_cmd_group, black_cmd_group = list(), list()
            for ugc in ugcs:
                for cg in ugc.command_group.all():
                    if cg.group_type == "white":
                        white_cmd_group.append({"id": cg.id, "name": cg.name, "comment": cg.comment})
                    else:
                        black_cmd_group.append({"id": cg.id, "name": cg.name, "comment": cg.comment})

            not_white_cmd_group, not_black_cmd_group = list(), list()
            for cg in CommandGroup.objects.exclude(id__in=[cg["id"] for cg in (white_cmd_group + black_cmd_group)]):
                if cg.group_type == "white":
                    not_white_cmd_group.append({"id": cg.id, "name": cg.name, "comment": cg.comment})
                else:
                    not_black_cmd_group.append({"id": cg.id, "name": cg.name, "comment": cg.comment})
            group_type = "white"
            for ugc in ugcs:
                for cg in ugc.command_group.all():
                    group_type = cg.group_type
                    break
            result = {
                'ug_id': ug_id,
                'name': user_group.name,
                'white_cmd_group': white_cmd_group,
                'black_cmd_group': black_cmd_group,
                'not_white_cmd_group': not_white_cmd_group,
                'not_black_cmd_group': not_black_cmd_group,
                'comment': ugcs[0].comment if ugcs else "",
                'group_type': group_type
            }
            res = {'code': 0, 'result': result}
        except Exception as e:
            res = {'code': 1, 'errmsg': str(e)}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        try:
            ug_id = kwargs.get('ug_id')
            ugc = UserGroupCommand.objects.get_or_create(user_group=Group.objects.get(id=ug_id))[0]
            put_data = QueryDict(request.body, mutable=True)
            white_cmd_groups = put_data.pop('white_cmd_group') if "white_cmd_group" in put_data else list()
            black_cmd_groups = put_data.pop('black_cmd_group') if "black_cmd_group" in put_data else list()
            if put_data["group_type"] == "white":
                ugc.command_group.set(CommandGroup.objects.filter(id__in=white_cmd_groups))
            elif put_data["group_type"] == "black":
                ugc.command_group.set(CommandGroup.objects.filter(id__in=black_cmd_groups))
            else:
                res = {'code': 1, 'result': '非法调用！'}
                return self.render_json_response(res)
            res = {'code': 0, 'result': "更新成功"}
        except Exception as e:
            res = {'code': 1, 'errmsg': '%s' % str(e)}
        return self.render_json_response(res)

    def delete(self, *args, **kwargs):
        ug_id = kwargs.get('ug_id')
        try:
            user_group = Group.objects.get(id=ug_id)
            obj = UserGroupCommand.objects.filter(user_group=user_group).delete()
            if obj:
                res = {"code": 0, "result": "清空完毕！"}
            else:
                res = {"code": 1, "errmsg": "未找到！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "错误！%s" % str(e)}
        return self.render_json_response(res)

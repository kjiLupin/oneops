
import re
import simplejson as json
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404
from django.views.generic import TemplateView
from django.http import QueryDict
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin

from ssh.models.perilous_command import PerilousCommand, CommandDetail, CommandGroup
from ssh.forms import CommandGroupForm


class PerilousCmdGroupView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_ssh_perilous_cmd_group_view'
    template_name = "ssh/perilous_cmd_group.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': '高危命令',
            'path2': '高危命令组'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class PerilousCmdGroupListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_ssh_perilous_cmd_group_view'

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit', 0))
        offset = int(request.GET.get('offset', 0))

        sort_order = request.GET.get("sortOrder", '')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        cmd_group_type = request.GET.get("group_type", '')
        if cmd_group_type == '':
            obj_list = CommandGroup.objects.get_queryset().order_by(sort_name)
        else:
            obj_list = CommandGroup.objects.filter(group_type=cmd_group_type).order_by(sort_name)

        search = request.GET.get("search", '')
        if search:
            obj_list = obj_list.filter(Q(name__contains=search) | Q(comment__contains=search)).distinct()

        total = obj_list.count()
        if limit != 0:
            obj_list = obj_list[offset:offset + limit].values("id", "name", "group_type", "comment", "creation_date")
        else:
            obj_list = obj_list.values("id", "name", "group_type", "comment", "creation_date")
        res = {"total": total, "rows": [o for o in obj_list]}
        return self.render_json_response(res)

    def post(self, request):
        if not request.user.has_perm('auth.perm_ssh_perilous_cmd_group_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        try:
            name = request.POST.get('name')
            comment = request.POST.get('comment')
            group_type = request.POST.get('group_type')
            if group_type == "white":
                white_cmds = request.POST.getlist('white_cmd')
                cd_ids = list()
                for pc_id in white_cmds:
                    pc = PerilousCommand.objects.get(id=pc_id)
                    cd = CommandDetail.objects.get_or_create(perilous_command=pc, cmd_type="white")
                    cd_ids.append(cd[0].id)
                cg = CommandGroup.objects.create(name=name, comment=comment, group_type=group_type)
                cg.command_detail.set(CommandDetail.objects.filter(id__in=cd_ids))
            elif group_type == "black":
                cd_ids = list()
                perilous_cmds = request.POST.getlist('perilous_cmd')
                for pc_id in perilous_cmds:
                    pc = PerilousCommand.objects.get(id=pc_id)
                    cd = CommandDetail.objects.get_or_create(perilous_command=pc, cmd_type="perilous")
                    cd_ids.append(cd[0].id)
                sensitive_cmds = request.POST.getlist('sensitive_cmd')
                for pc_id in sensitive_cmds:
                    pc = PerilousCommand.objects.get(id=pc_id)
                    cd = CommandDetail.objects.get_or_create(perilous_command=pc, cmd_type="sensitive")
                    cd_ids.append(cd[0].id)
                cg = CommandGroup.objects.create(name=name, comment=comment, group_type=group_type)
                cg.command_detail.set(CommandDetail.objects.filter(id__in=cd_ids))
            else:
                res = {'code': 1, 'result': '非法调用！'}
                return self.render_json_response(res)
            res = {'code': 0, 'result': '添加成功！'}
        except re.error as e:
            res = {'code': 1, 'errmsg': '正则语法错误！%s' % str(e)}
        return self.render_json_response(res)


class PerilousCmdGroupDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_ssh_perilous_cmd_group_view', 'auth.perm_ssh_perilous_cmd_group_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            o = CommandGroup.objects.get(pk=pk)
            white_cmd, perilous_cmd, sensitive_cmd = list(), list(), list()
            white_cmd_available, black_cmd_available = list(), list()
            if o.group_type == "white":
                for cd in o.command_detail.all():
                    white_cmd.append({
                        "id": cd.perilous_command.id,
                        "cmd_regex": cd.perilous_command.cmd_regex,
                        "comment": cd.perilous_command.comment
                    })
            for pc in PerilousCommand.objects.exclude(id__in=[wc["id"] for wc in white_cmd]).filter(cmd_type="white"):
                white_cmd_available.append({
                    "id": pc.id,
                    "cmd_regex": pc.cmd_regex,
                    "comment": pc.comment
                })
            if o.group_type == "black":
                for cd in o.command_detail.all():
                    if cd.cmd_type == "perilous":
                        perilous_cmd.append({
                            "id": cd.perilous_command.id,
                            "cmd_regex": cd.perilous_command.cmd_regex,
                            "comment": cd.perilous_command.comment
                        })
                    elif cd.cmd_type == "sensitive":
                        sensitive_cmd.append({
                            "id": cd.perilous_command.id,
                            "cmd_regex": cd.perilous_command.cmd_regex,
                            "comment": cd.perilous_command.comment
                        })
            un_available_cmd_ids = [i["id"] for i in (perilous_cmd + sensitive_cmd)]
            for pc in PerilousCommand.objects.exclude(id__in=un_available_cmd_ids).filter(cmd_type="black"):
                black_cmd_available.append({
                    "id": pc.id,
                    "cmd_regex": pc.cmd_regex,
                    "comment": pc.comment
                })
            result = {
                'id': o.id,
                'name': o.name,
                'group_type': o.group_type,
                'comment': o.comment,
                'wca': white_cmd_available,
                'white_cmd': white_cmd,
                'bca': black_cmd_available,
                'perilous_cmd': perilous_cmd,
                'sensitive_cmd': sensitive_cmd
            }
            res = {'code': 0, 'result': result}
        except CommandGroup.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        try:
            pk = kwargs.get('pk')
            put_data = QueryDict(request.body, mutable=True)
            white_cmds = put_data.pop('white_cmd') if "white_cmd" in put_data else list()
            perilous_cmds = put_data.pop('perilous_cmd') if "perilous_cmd" in put_data else list()
            sensitive_cmds = put_data.pop('sensitive_cmd') if "sensitive_cmd" in put_data else list()
            if put_data["group_type"] == "white":
                cd_ids = list()
                for pc_id in white_cmds:
                    pc = PerilousCommand.objects.get(id=pc_id)
                    cd = CommandDetail.objects.get_or_create(perilous_command=pc, cmd_type="white")
                    cd_ids.append(cd[0].id)
                CommandGroup.objects.filter(pk=pk).update(**put_data.dict())
                CommandGroup.objects.get(pk=pk).command_detail.set(CommandDetail.objects.filter(id__in=cd_ids))
            elif put_data["group_type"] == "black":
                cd_ids = list()
                for pc_id in perilous_cmds:
                    pc = PerilousCommand.objects.get(id=pc_id)
                    cd = CommandDetail.objects.get_or_create(perilous_command=pc, cmd_type="perilous")
                    cd_ids.append(cd[0].id)

                for pc_id in sensitive_cmds:
                    pc = PerilousCommand.objects.get(id=pc_id)
                    cd = CommandDetail.objects.get_or_create(perilous_command=pc, cmd_type="sensitive")
                    cd_ids.append(cd[0].id)
                CommandGroup.objects.filter(pk=pk).update(**put_data.dict())
                CommandGroup.objects.get(pk=pk).command_detail.set(CommandDetail.objects.filter(id__in=cd_ids))
            else:
                res = {'code': 1, 'result': '非法调用！'}
                return self.render_json_response(res)
            res = {'code': 0, 'result': '更新成功！'}
        except Exception as e:
            res = {'code': 1, 'errmsg': '%s' % str(e)}
        return self.render_json_response(res)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = CommandGroup.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return self.render_json_response(res)


import re
import simplejson as json
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.http import QueryDict
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin

from ssh.models.perilous_command import PerilousCommand
from ssh.forms import PerilousCommandForm


class PerilousCmdView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_ssh_perilous_cmd_view'
    template_name = "ssh/perilous_cmd.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': '高危命令',
            'path2': '高危命令'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class PerilousCmdListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_ssh_perilous_cmd_view'

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit', 0))
        offset = int(request.GET.get('offset', 0))

        sort_order = request.GET.get("sortOrder", '')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        cmd_type = request.GET.get("cmd_type", '')
        if cmd_type == '':
            obj_list = PerilousCommand.objects.get_queryset().order_by(sort_name)
        else:
            obj_list = PerilousCommand.objects.filter(cmd_type=cmd_type).order_by(sort_name)

        search = request.GET.get("search", '')
        if search:
            obj_list = obj_list.filter(Q(cmd_regex__contains=search) | Q(comment__contains=search)).distinct()

        total = obj_list.count()
        if limit != 0:
            obj_list = obj_list[offset:offset + limit].values("id", "cmd_regex", "cmd_type", "comment")
        else:
            obj_list = obj_list.values("id", "cmd_regex", "cmd_type", "comment")
        res = {"total": total, "rows": [o for o in obj_list]}
        return self.render_json_response(res)

    def post(self, request):
        if not request.user.has_perm('auth.perm_ssh_perilous_cmd_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        try:
            cmd_regex = request.POST.get('cmd_regex')
            re.compile(cmd_regex)
            form = PerilousCommandForm(request.POST)
            if form.is_valid():
                form.save()
                res = {'code': 0, 'result': '添加成功！'}
            else:
                res = {'code': 1, 'errmsg': form.errors}
        except re.error as e:
            res = {'code': 1, 'errmsg': '正则语法错误！%s' % str(e)}
        return self.render_json_response(res)


class PerilousCmdDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_ssh_perilous_cmd_view', 'auth.perm_ssh_perilous_cmd_edit')

    def get(self, request, **kwargs):
        pk = kwargs.get('pk')
        try:
            o = PerilousCommand.objects.get(pk=pk)
            result = {
                'id': o.id,
                'cmd_regex': o.cmd_regex,
                'cmd_type': o.cmd_type,
                'comment': o.comment
            }
            res = {'code': 0, 'result': result}
        except PerilousCommand.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        try:
            pk = kwargs.get('pk')
            dict_data = QueryDict(request.body)
            re.compile(dict_data['cmd_regex'])
            p = get_object_or_404(PerilousCommand, pk=pk)
            form = PerilousCommandForm(dict_data, instance=p)
            if form.is_valid():
                form.save()
                res = {"code": 0, "result": "更新成功"}
            else:
                res = {"code": 1, "errmsg": form.errors}
        except re.error as e:
            res = {'code': 1, 'errmsg': '正则语法错误！%s' % str(e)}
        except Exception as e:
            res = {'code': 1, 'errmsg': '%s' % str(e)}
        return self.render_json_response(res)

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = PerilousCommand.objects.filter(pk=pk).delete()
            if obj:
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return self.render_json_response(res)

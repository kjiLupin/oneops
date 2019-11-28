# -*- coding: utf-8 -*-
import re
import os
import uuid
import datetime
from django.http import QueryDict
from django.db.models import Q
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin
from accounts.models import User
from ssh.models.host_user import HostUser
from job.models.job import Tag, Job, Task, TaskLog, JobConfig

from .cmd_execute import exec_job


class JobAddView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_job_job_edit'
    template_name = 'job/job_add.html'

    def get(self, request, **kwargs):
        context = {
            'path1': 'Job',
            'path2': '新建作业',
            'uuid': str(uuid.uuid4()),
            'tag_list': [{'id': tag.id, 'name': tag.name} for tag in Tag.objects.all()],
            'host_users': [{"id": h.id, "name": h.username, "desc": h.description} for h in HostUser.objects.all()]
        }
        try:
            job_id = request.GET.get("id")
            if job_id:
                job = Job.objects.get(id=job_id)
                context.update({
                    "host_user": job.host_user.id,
                    "exec_type": job.exec_type,
                    "task_type": job.task_type,
                    "cmd": job.cmd,
                    "host": job.host,
                    "inventory": job.inventory,
                    "module_name": job.module_name,
                    "module_args": job.module_args,
                    "playbook": job.playbook,
                    "extra_vars": job.extra_vars,
                    "public": job.public,
                    "active": job.active
                })
        except:
            pass
        context.update(**kwargs)
        return self.render_to_response(context)


class JobExecuteView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_job_view'
    template_name = 'job/job_execute.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': '作业执行'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request, **kwargs):
        # 作业执行
        job_id = request.POST.get('id', None)
        if job_id is None:
            res = {'code': 1, 'errmsg': '请选择作业！'}
        else:
            try:
                job = Job.objects.get(id=job_id)
                res = exec_job(job, request.user)
            except Job.DoesNotExist:
                res = {'code': 1, 'errmsg': '该作业不存在！'}
        return self.render_json_response(res)


class JobView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_job_job_view'
    template_name = 'job/job.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': '作业列表',
            'tag_list': [{'id': tag.id, 'name': tag.name} for tag in Tag.objects.all()],
            'host_users': [{"id": h.id, "name": h.username, "desc": h.description} for h in HostUser.objects.all()]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class JobListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_job_view'

    def get(self, request, **kwargs):
        exec_type = request.GET.get("exec_type")
        task_type = request.GET.get("task_type")
        public = request.GET.get("public")
        active = request.GET.get("active")
        tags = request.GET.getlist('tags[]', [])
        if request.user.is_superuser:
            obj_list = Job.objects.get_queryset()
        else:
            obj_list = Job.objects.filter(public=True).filter(created_by=request.user)
        search = request.GET.get("search", "")
        if search:
            obj_list = obj_list.filter(Q(name__contains=search) |Q(source_file__contains=search) |
                                       Q(destination_file__contains=search) |
                                       Q(description__contains=search)).distinct()
        if exec_type:
            obj_list = obj_list.filter(exec_type=exec_type)
        if task_type:
            obj_list = obj_list.filter(task_type=task_type)
        if public:
            public = True if public == "true" else False
            obj_list = obj_list.filter(public=public)
        if active:
            active = True if active == "true" else False
            obj_list = obj_list.filter(active=active)
        if tags:
            obj_list = obj_list.filter(tags__in=Tag.objects.filter(id__in=tags)).distinct()
        inventory_path = JobConfig.objects.get(item='inventory_path').value
        playbook_path = JobConfig.objects.get(item='playbook_path').value
        res = list()
        for obj in obj_list:
            res.append({
                'id': obj.id,
                'name': obj.name,
                'hu': obj.host_user.username,
                'et': obj.get_exec_type_display(),
                'tt': obj.get_task_type_display(),
                'sf': obj.source_file,
                'df': obj.destination_file,
                'cmd': obj.cmd,
                'host': obj.host,
                'hf': re.sub(inventory_path, "", obj.inventory) if obj.inventory else "",
                'mn': obj.module_name,
                'ma': obj.module_args,
                'pb': re.sub(playbook_path, "", obj.playbook) if obj.playbook else "",
                'ea': obj.extra_vars,
                'cb': obj.created_by.display,
                'tags': " ".join([t.name for t in obj.tags.all()]),
                'pub': obj.public,
                'act': obj.active,
                'cd': obj.creation_date,
                'desc': obj.description
            })
        return self.render_json_response(res)

    def post(self, request, **kwargs):
        if not request.user.has_perm('auth.perm_job_job_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        task_name = request.POST.get('task_name')
        host_user = request.POST.get('host_user')
        program = request.POST.get('program')
        execute = request.POST.get('execute')
        inventory = request.POST.get('inventory')
        public = request.POST.get('public') == "true"
        active = request.POST.get('active') == "true"
        tags = request.POST.getlist('tags', [])
        description = request.POST.get('description')
        try:
            if program == "ansible":
                host = request.POST.get('host')
                if execute == "ad-hoc":
                    module_name = request.POST.get('module')
                    module_args = request.POST.get('args')
                    if module_name == "command":
                        module_name, module_args = "raw", request.POST.get('command')
                    elif module_name == "shell":
                        module_args = request.POST.get('shell')
                    elif module_name == "custom":
                        module_name = request.POST.get('custom_module')
                        module_args = request.POST.get('custom_args')
                        if module_name == "fetch":
                            # 批量下载文件，改变参数dest的值
                            dest = re.findall(r"dest=(.+)", module_args)[0]
                            file_name = dest.split('/')[-1]
                            module_args = module_args.replace(dest, file_name)
                    job = Job.objects.create(name=task_name,
                                             host_user=HostUser.objects.get(id=host_user),
                                             exec_type=execute,
                                             host=host,
                                             inventory=inventory,
                                             module_name=module_name,
                                             module_args=module_args,
                                             created_by=request.user,
                                             public=public,
                                             active=active,
                                             description=description
                                             )
                elif execute == "playbook":
                    playbook = request.POST.get('playbook')
                    extra_vars = request.POST.get('extra_vars')
                    job = Job.objects.create(name=task_name,
                                             host_user=HostUser.objects.get(id=host_user),
                                             exec_type=execute,
                                             host=host,
                                             inventory=inventory,
                                             playbook=playbook,
                                             extra_vars=extra_vars,
                                             created_by=request.user,
                                             public=public,
                                             active=active,
                                             description=description
                                             )
            else:
                # paramiko
                host = request.POST.get('host')
                cmd = request.POST.get('cmd')
                job = Job.objects.create(name=task_name,
                                         host_user=HostUser.objects.get(id=host_user),
                                         exec_type=program,
                                         host=host,
                                         cmd=cmd,
                                         created_by=request.user,
                                         public=public,
                                         active=active,
                                         description=description
                                         )
            job.tags.set(Tag.objects.filter(id__in=tags))
            job.save()
            res = {'code': 0, 'result': '作业添加成功'}
        except Exception as e:
            res = {'code': 1, 'errmsg': str(e)}
        return self.render_json_response(res)


class JobDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_job_job_view', 'auth.perm_job_job_edit')

    def get(self, request, **kwargs):
        try:
            pk = kwargs.get('pk')
            p = Job.objects.get(pk=pk)
            job = {
                "id": p.id,
                "name": p.name,
                "host_user": p.host_user.id,
                "exec_type": p.exec_type,
                "source_file": p.source_file,
                "destination_file": p.destination_file,
                "cmd": p.cmd,
                "host": p.host,
                "inventory": p.inventory,
                "module_name": p.module_name,
                "module_args": p.module_args,
                "playbook": p.playbook,
                "extra_vars": p.extra_vars,
                "tags": [t.id for t in p.tags.all()],
                "public": p.public,
                "active": p.active,
                "description": p.description
            }
            res = {'code': 0, 'result': job}
        except Job.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            update_data = QueryDict(request.body).dict()
            job = Job.objects.filter(pk=pk)
            if update_data['execute'] == "playbook":
                job.update(**{
                    'name': update_data['task_name'],
                    'host_user': HostUser.objects.get(id=update_data['host_user']),
                    'exec_type': update_data['execute'],
                    'task_type': 'command',
                    'source_file': '',
                    'destination_file': '',
                    'cmd': '',
                    'host': update_data['host'],
                    'inventory': update_data['inventory'],
                    'playbook': update_data['playbook'],
                    'extra_vars': update_data['extra_vars'],
                    'module_name': '',
                    'module_args': '',
                    'public': update_data['public'] == "true",
                    'active': update_data['active'] == "true",
                    'description': update_data['description']
                })
            else:
                # ad-hoc
                if update_data['module'] == "command":
                    module_name = "raw"
                    module_args = update_data['command']
                elif update_data['module'] == "custom":
                    module_name = update_data['custom_module']
                    module_args = update_data['custom_args']
                elif update_data['module'] == "shell":
                    module_name = update_data['module']
                    module_args = update_data['shell']
                else:
                    module_name = update_data['module']
                    module_args = update_data['module_args']
                job.update(**{
                    'name': update_data['task_name'],
                    'host_user': HostUser.objects.get(id=update_data['host_user']),
                    'exec_type': update_data['execute'],
                    'task_type': 'command',
                    'source_file': '',
                    'destination_file': '',
                    'cmd': '',
                    'host': update_data['host'],
                    'inventory': update_data['inventory'],
                    'playbook': '',
                    'extra_vars': '',
                    'module_name': module_name,
                    'module_args': module_args,
                    'public': update_data['public'] == "true",
                    'active': update_data['active'] == "true",
                    'description': update_data['description']
                })
            tags_id_list = update_data['tags'].split(',') if 'tags' in update_data else list()
            job[0].tags.set(Tag.objects.filter(id__in=tags_id_list))
            res = {"code": 0, "result": "更新成功"}
        except Job.DoesNotExist:
            res = {"code": 1, "errmsg": "该记录不存在！"}
        return self.render_json_response(res)

    def delete(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = Job.objects.filter(pk=pk)
            if obj:
                obj.delete()
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return self.render_json_response(res)


class JobLogView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_job_log'
    template_name = 'job/job_log.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': '作业日志',
            'user_list': [{"id": u.id, "display": u.display} for u in User.objects.get_queryset()]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class JobLogListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_job_log'

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset'))

        date_from = request.GET.get("date_from", None)
        date_to = request.GET.get("date_to", None)
        try:
            if request.user.is_superuser:
                # 超级用户才可以查看所有用户的执行日志
                if date_from and date_to:
                    date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
                    date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__gte=date_from, creation_date__lte=date_to, job__isnull=False)
                elif date_from:
                    date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__gte=date_from, job__isnull=False)
                elif date_to:
                    date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__lte=date_to, job__isnull=False)
                else:
                    seven_day_ago = datetime.datetime.now() + datetime.timedelta(days=-7)
                    obj_list = Task.objects.filter(creation_date__gte=seven_day_ago, job__isnull=False)
            else:
                # 普通用户，只能查看自己的执行日志
                if date_from and date_to:
                    date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
                    date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__gte=date_from, creation_date__lte=date_to, user=request.user, job__isnull=False)
                elif date_from:
                    date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__gte=date_from, user=request.user, job__isnull=False)
                elif date_to:
                    date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__lte=date_to, user=request.user, job__isnull=False)
                else:
                    seven_day_ago = datetime.datetime.now() + datetime.timedelta(days=-7)
                    obj_list = Task.objects.filter(creation_date__gte=seven_day_ago, user=request.user, job__isnull=False)

            user_id = request.GET.get("user_id", None)
            if user_id:
                obj_list = obj_list.filter(user__id=user_id)
            task_type = request.GET.get("task_type")
            if task_type:
                obj_list = obj_list.filter(task_type=task_type)
            search = request.GET.get("search", None)
            if search:
                obj_list = obj_list.filter(Q(name__contains=search) | Q(source_file__contains=search) |
                                           Q(destination_file__contains=search) |
                                           Q(error_msg__contains=search)).distinct()
            result = list()
            for obj in obj_list[offset:(offset + limit)]:
                total_tasks_num = obj.task_nums
                if total_tasks_num:
                    success_num = TaskLog.objects.filter(task=obj).filter(status='success').count()
                    failed_num = TaskLog.objects.filter(task=obj).filter(status='failed').count()
                    not_start_num = total_tasks_num - success_num - failed_num
                else:
                    success_num, failed_num, not_start_num = None, None, None
                item = {
                    'id': obj.id,
                    'name': obj.job.name,
                    'user': obj.user.display,
                    'et': obj.get_exec_type_display(),
                    'tt': obj.get_task_type_display(),
                    'tt2': obj.task_type,
                    'sf': obj.source_file,
                    'df': obj.destination_file,
                    'cd': obj.creation_date,
                    'tn': total_tasks_num,
                    'sn': success_num,
                    'fn': failed_num,
                    'nsn': not_start_num,
                    'executed': obj.executed,
                    'error': obj.error_msg
                }
                result.append(item)
            res = {"total": obj_list.count(), "rows": result}
        except Exception as e:
            print(str(e))
            res = {"total": 0, "rows": list()}
        return self.render_json_response(res)

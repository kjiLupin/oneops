# -*- coding: utf-8 -*-
import datetime
from django.db.models import Q
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin

from accounts.models import User
from job.models.job import Task, TaskLog


class TaskView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_cmd_execute'
    template_name = 'job/task.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': '任务日志',
            'user_list': [{"id": u.id, "display": u.display} for u in User.objects.get_queryset()]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_job_view'

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
                    obj_list = Task.objects.filter(creation_date__gte=date_from, creation_date__lte=date_to, job__isnull=True)
                elif date_from:
                    date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__gte=date_from, job__isnull=True)
                elif date_to:
                    date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__lte=date_to, job__isnull=True)
                else:
                    seven_day_ago = datetime.datetime.now() + datetime.timedelta(days=-7)
                    obj_list = Task.objects.filter(creation_date__gte=seven_day_ago, job__isnull=True)
            else:
                # 普通用户，只能查看自己的执行日志
                if date_from and date_to:
                    date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
                    date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__gte=date_from, creation_date__lte=date_to, user=request.user, job__isnull=True)
                elif date_from:
                    date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__gte=date_from, user=request.user, job__isnull=True)
                elif date_to:
                    date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S')
                    obj_list = Task.objects.filter(creation_date__lte=date_to, user=request.user, job__isnull=True)
                else:
                    seven_day_ago = datetime.datetime.now() + datetime.timedelta(days=-7)
                    obj_list = Task.objects.filter(creation_date__gte=seven_day_ago, user=request.user, job__isnull=True)

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
                    'name': obj.name.split('-')[-1],
                    'user': obj.user.display,
                    'et': obj.get_exec_type_display(),
                    'tt': obj.get_task_type_display(),
                    'tt2': obj.task_type,
                    'sf': obj.source_file,
                    'df': obj.destination_file,
                    'host': obj.host,
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


class TaskLogView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    """
    任务详情：展示每台机器执行结果
    """
    permission_required = 'auth.perm_job_task_log'
    template_name = 'job/task_detail.html'

    def get_context_data(self, **kwargs):
        task_id = kwargs.get('id')
        task = Task.objects.get(id=int(task_id))
        context = {
            'path1': 'Job',
            'path2': '任务详细',
            'task_id': task_id,
            'exec_type': task.exec_type
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskLogListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_task_log'

    def get(self, request, **kwargs):
        task_id = kwargs.get('id')
        limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset'))
        try:
            task = Task.objects.get(id=int(task_id))
            obj_list = TaskLog.objects.filter(task=task)
            search = request.GET.get("search", None)
            if search:
                obj_list = obj_list.filter(Q(host__contains=search) | Q(host_user__contains=search) |
                                           Q(cmd__contains=search) | Q(module_name__contains=search) |
                                           Q(module_args__contains=search) | Q(playbook_name__contains=search) |
                                           Q(extra_vars__contains=search) | Q(result__contains=search)).distinct()
            res = list()
            if task.exec_type == "ad-hoc":
                for obj in obj_list[offset:(offset + limit)]:
                    res.append({
                        'h': obj.host,
                        'hu': obj.host_user,
                        'mn': obj.module_name,
                        'ma': obj.module_args,
                        'status': obj.get_status_display(),
                        'res': obj.result,
                        'st': obj.start_time,
                        'et': obj.end_time
                    })
            elif task.exec_type == "playbook":
                for obj in obj_list[offset:(offset + limit)]:
                    res.append({
                        'h': obj.host,
                        'hu': obj.host_user,
                        'pn': obj.playbook_name,
                        'p': obj.playbook,
                        'ea': obj.extra_vars,
                        'status': obj.get_status_display(),
                        'res': obj.result,
                        'st': obj.start_time,
                        'et': obj.end_time
                    })
            else:
                # paramiko
                for obj in obj_list[offset:(offset + limit)]:
                    res.append({
                        'h': obj.host,
                        'hu': obj.host_user,
                        'cmd': obj.cmd,
                        'status': obj.get_status_display(),
                        'res': obj.result,
                        'st': obj.start_time,
                        'et': obj.end_time
                    })
            return self.render_json_response({"total": len(obj_list), "rows": res})
        except Task.DoesNotExist:
            print("Task id not found.")
        except Exception as e:
            print(str(e))
        return self.render_json_response({"total": 0, "rows": list()})

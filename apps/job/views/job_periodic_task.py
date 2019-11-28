# -*- coding: utf-8 -*-
import datetime
import subprocess
from django.http import QueryDict
from django.db.models import Q
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin
from job.models.job import Job
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask


class PeriodicTaskView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_job_job_view'
    template_name = 'job/periodic_task.html'

    def get(self, request, **kwargs):
        cs_list = list()
        for cs in CrontabSchedule.objects.all():
            cs_list.append({
                "id": cs.id,
                "value": "{} {} {} {} {}".format(cs.minute, cs.hour, cs.day_of_week, cs.day_of_month, cs.month_of_year)
            })
        is_list = list()
        for _is in IntervalSchedule.objects.all():
            is_list.append({
                "id": _is.id,
                "value": "*/{} {}".format(_is.every, _is.period)
            })
        job_list = list()
        if request.user.is_superuser:
            for j in Job.objects.all():
                job_list.append({"id": j.id, "name": j.name, "description": j.description})
        else:
            for j in Job.objects.filter(created_by=request.user):
                job_list.append({"id": j.id, "name": j.name, "description": j.description})
        context = {
            'path1': 'Job',
            'path2': '定时作业',
            'cs_list': cs_list,
            'is_list': is_list,
            'job_list': job_list
        }
        context.update(**kwargs)
        return self.render_to_response(context)


class PeriodicTaskListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_job_view'

    def get(self, request, **kwargs):
        periodic_type = request.GET.get("periodic_type", "")
        if periodic_type == "":
            obj_list = PeriodicTask.objects.get_queryset()
        elif periodic_type == "crontab":
            obj_list = PeriodicTask.objects.exclude(crontab=None)
        elif periodic_type == "interval":
            obj_list = PeriodicTask.objects.exclude(interval=None)

        search = request.GET.get("search", "")
        if search:
            obj_list = obj_list.filter(Q(name__contains=search) | Q(task__contains=search) |
                                       Q(description__contains=search)).distinct()
        res = list()
        for obj in obj_list:
            crontab = "{} {} {} {} {}".format(obj.crontab.minute, obj.crontab.hour, obj.crontab.day_of_week,
                                              obj.crontab.day_of_month, obj.crontab.month_of_year) if obj.crontab else ''
            interval = "*/{} {}".format(obj.interval.every, obj.interval.period) if obj.interval else ''
            res.append({
                'id': obj.id,
                'name': obj.name.split('#')[-1],
                'task': obj.task,
                'interval': interval,
                'crontab': crontab,
                'args': obj.args,
                'kwargs': obj.kwargs,
                'queue': obj.queue,
                'exchange': obj.exchange,
                'routing_key': obj.routing_key,
                # 'priority': obj.priority,
                'expires': obj.expires,
                # 'one_off': obj.one_off,
                # 'start_time': obj.start_time,
                'enabled': obj.enabled,
                'last_run_at': obj.last_run_at,
                'total_run_count': obj.total_run_count,
                'date_changed': obj.date_changed,
                'description': obj.description,
                'no_changes': obj.no_changes
            })
        return self.render_json_response(res)

    def post(self, request, **kwargs):
        if not request.user.has_perm('auth.perm_job_job_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        try:
            job = request.POST.get('job', None)
            description = request.POST.get('description', '')
            schedule = request.POST.get('schedule', None)
            noexpires = request.POST.get('noexpires', None)
            enabled = request.POST.get('enabled', "true")
            if noexpires is None:
                expires = datetime.datetime.strptime(request.POST.get('expires'), "%Y-%m-%d %H:%M")
            else:
                expires = None
            if job is None:
                res = {'code': 1, 'errmsg': "未选择任何作业！"}
                return self.render_json_response(res)
            job = Job.objects.get(id=job)
            now_time = datetime.datetime.now().strftime("%Y%m%d%H%M")
            if schedule == "crontab":
                crontab = request.POST.get('crontab', 0)
                cs = CrontabSchedule.objects.get(id=crontab)
                PeriodicTask.objects.create(name="{}#{}-{}".format(job.id, job.name, now_time),
                                            task='job.tasks.task.periodic_job',
                                            args=[job.id, request.user.id], interval=None, crontab=cs,
                                            enabled=True if enabled == "true" else False,
                                            expires=expires, description=description)
            elif schedule == "interval":
                interval = request.POST.get('interval', 0)
                _is = IntervalSchedule.objects.get(id=interval)
                PeriodicTask.objects.create(name="{}#{}-{}".format(job.id, job.name, now_time),
                                            task='job.tasks.task.periodic_job',
                                            args=[job.id, request.user.id], interval=_is, crontab=None,
                                            enabled=True if enabled == "true" else False,
                                            expires=expires, description=description)
            else:
                res = {'code': 1, 'errmsg': "非法调用！未选择任何定时周期！"}
                return self.render_json_response(res)
            res = {'code': 0, 'result': '作业添加成功'}
        except Exception as e:
            res = {'code': 1, 'errmsg': str(e)}
        return self.render_json_response(res)


class PeriodicTaskDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_job_job_view', 'auth.perm_job_job_edit')

    def get(self, request, **kwargs):
        try:
            pk = kwargs.get('pk')
            p = PeriodicTask.objects.get(pk=pk)
            res = {
                "id": p.id,
                "job_id": p.name.split('#')[0],
                "description": p.description,
                "expires": p.expires.strftime("%Y-%m-%d %H:%M") if p.expires else "",
                "enabled": p.enabled,
                "crontab": p.crontab.id if p.crontab else "",
                "interval": p.interval.id if p.interval else ""
            }
            res = {'code': 0, 'result': res}
        except Job.DoesNotExist:
            res = {'code': 1, 'errmsg': '未找到！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            update_data = QueryDict(request.body).dict()
            p = PeriodicTask.objects.get(pk=pk)
            job_id = update_data["job"]
            job = Job.objects.get(id=job_id)
            if p.name.split("#")[0] != job_id:
                now_time = datetime.datetime.now().strftime("%Y%m%d%H%M")
                p.name = "{}#{}-{}".format(job.id, job.name, now_time)
            p.description = update_data["description"]
            p.enabled = True if update_data["enabled"] == "true" else False
            p.args = [job.id, request.user.id]
            if 'noexpires' in update_data:
                p.expires = None
            else:
                p.expires = datetime.datetime.strptime(update_data['expires'], "%Y-%m-%d %H:%M")
            if update_data['schedule'] == "crontab":
                p.crontab_id = update_data["crontab"]
                p.interval = None
            else:
                p.crontab = None
                p.interval_id = update_data["interval"]
            p.save()
            subprocess.Popen(["systemctl", "restart", "celery_beat.service"])
            res = {"code": 0, "result": "更新成功"}
        except Job.DoesNotExist:
            res = {"code": 1, "errmsg": "该记录不存在！"}
        return self.render_json_response(res)

    def delete(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            obj = PeriodicTask.objects.filter(pk=pk)
            if obj:
                obj.delete()
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "未找到该解析！"}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除错误！%s" % str(e)}
        return self.render_json_response(res)

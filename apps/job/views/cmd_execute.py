# -*- coding: utf-8 -*-
import datetime
import uuid
import traceback
import simplejson as json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from wdoneops.celery import celery_app
from common.mixins import JSONResponseMixin

from common.utils.base import send_msg_to_admin
from job.models.job import HostUser, Task, TaskLog
from job.tasks.ansible_api import AnsibleAPI
from ssh.views.perilous_cmd_check import get_perilous_cmd, perilous_cmd_check


# https://zhuanlan.zhihu.com/p/40820809 Celery学习总结
@celery_app.task
def async_func(task_id, t_uuid, host=None, **kwargs):
    _task = Task.objects.get(id=task_id)
    try:
        if _task.exec_type == "ad-hoc":
            # 高危命令校验
            white_cmd, perilous_cmd, sensitive_cmd = get_perilous_cmd(_task.user)
            if white_cmd or perilous_cmd or sensitive_cmd:
                if kwargs.get("module_name") in ["command", "raw"]:
                    if perilous_cmd_check(kwargs.get('module_args'), white_cmd, perilous_cmd, sensitive_cmd) is False:
                        _task.error_msg = "您的命令已被黑白名单拦截！请联系管理员添加权限"
                        _task.executed = True
                        _task.save(update_fields=['executed', 'error_msg'])
                        return
                else:
                    _task.error_msg = "您被设置了命令黑白名单，只能执行command、raw模块！"
                    _task.executed = True
                    _task.save(update_fields=['executed', 'error_msg'])
                    return
            ansible_api = AnsibleAPI(_task.id, t_uuid, **kwargs)
            ansible_api.run_ad_hoc(host, kwargs.get('module_name'), kwargs.get('module_args'))
        elif _task.exec_type == "playbook":
            ansible_api = AnsibleAPI(_task.id, t_uuid, **kwargs)
            ansible_api.run_playbook([kwargs.get('playbook')], json.loads(kwargs.get('extra_vars')))
        else:
            _task.error_msg = "调用错误！"
            _task.save(update_fields=['error_msg'])
            return
        ansible_api.save_result()
    except Exception as e:
        send_msg_to_admin(traceback.print_exc())
        _task.error_msg = str(e)
    _task.task_nums = TaskLog.objects.filter(task_id=_task.id).count()
    _task.executed = True
    _task.save(update_fields=['task_nums', 'executed', 'error_msg'])


def exec_job(job, user):
    date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    _task = Task.objects.create(
        uuid=str(uuid.uuid4()),
        job=job,
        name=date_now + "-" + job.name,
        user=user,
        exec_type=job.exec_type,
        host=job.host
    )
    data = {
        "host_user": job.host_user.id,
        "resource": list(),
        "hosts_file": [job.inventory]
    }
    if job.exec_type == "ad-hoc":
        if job.module_name in ['copy', 'fetch']:
            data.update({
                "module_name": job.module_name,
                "module_args": job.module_args,
                "module_args_real": job.module_args
            })
        else:
            data.update({
                "module_name": job.module_name,
                "module_args": job.module_args
            })
        async_func.delay(_task.id, _task.uuid, host=job.host, **data)
    elif job.exec_type == "playbook":
        data.update({
            "playbook_name": job.playbook.split('/')[-1],
            "playbook": job.playbook,
            "extra_vars": job.extra_vars
        })
        async_func.delay(_task.id, _task.uuid, host=job.host, **data)
    else:
        # paramiko
        return {'code': 1, 'errmsg': '暂不支持paramiko任务'}
    return {'code': 0, 'result': '该作业已提交后台运行中......'}


class CmdExecute(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_cmd_execute'
    template_name = 'job/cmd_execute.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': '快速命令执行',
            'host_users': [{"id": h.id, "name": h.username, "desc": h.description} for h in HostUser.objects.all()]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request):
        # 提交命令并执行
        try:
            date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            # uuid作为redis key，把命令执行过程放入redis中。
            uuid = str(uuid.uuid4())
            task_name = request.POST.get('task_name')
            host_user = request.POST.get('host_user')
            program = request.POST.get('program')
            execute = request.POST.get('execute')
            _task = Task.objects.create(
                uuid=uuid,
                name=date_now + "-" + task_name,
                user=request.user,
                exec_type=execute
            )
            data = {
                "host_user": host_user,
                "resource": list(),
                "hosts_file": [request.POST.get('inventory')]
            }
            if program == "ansible":
                host = request.POST.get('host')
                _task.host = host
                _task.save(update_fields=['host'])
                if execute == "ad-hoc":
                    ansible_module = request.POST.get('module')
                    module_args = request.POST.get('args')
                    if ansible_module == "raw":
                        command = request.POST.get('command')
                        data.update({
                            "module_name": ansible_module,
                            "module_args": command
                        })
                        async_func(_task.id, uuid, host=host, **data)
                    elif ansible_module == "shell":
                        shell = request.POST.get('shell')
                        data.update({
                            "module_name": ansible_module,
                            "module_args": shell
                        })
                        async_func(_task.id, uuid, host=host, **data)
                    elif ansible_module == "custom":
                        custom_module = request.POST.get('custom_module')
                        custom_args = request.POST.get('custom_args')
                        data.update({
                            "module_name": custom_module,
                            "module_args": custom_args
                        })
                        async_func(_task.id, uuid, host=host, **data)
                    else:
                        data.update({
                            "module_name": ansible_module,
                            "module_args": module_args
                        })
                        async_func(_task.id, uuid, host=host, **data)
                elif execute == "playbook":
                    playbook = request.POST.get('playbook')
                    extra_vars = request.POST.get('extra_vars')
                    data.update({
                        "playbook_name": playbook.split('/')[-1],
                        "playbook": playbook,
                        "extra_vars": extra_vars
                    })
                    async_func(_task.id, uuid, host=host, **data)
            else:
                # paramiko
                _task = Task.objects.create(
                    name=date_now + "-" + task_name,
                    user=request.user,
                    exec_type=program
                )
        except Exception as e:
            print('error', traceback.print_exc())
            return self.render_json_response({'code': 1, 'errmsg': str(traceback.print_exc())})
        return self.render_json_response({'code': 0, 'result': '任务提交成功！请到"任务日志"查看执行结果！'})

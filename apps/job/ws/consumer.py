# -*- coding: utf-8 -*-
import os
import uuid
import json
import datetime
import traceback
from channels.generic.websocket import WebsocketConsumer
from common.utils.base import send_msg_to_admin, make_directory, FILE_DOWNLOAD_TMP_DIR
from cmdb.models.business import App
from job.models.job import Task, TaskLog, Job
from job.tasks.gen_resource import GenResource
from job.tasks.ansible_api import AnsibleAPI


class AdHocConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super(AdHocConsumer, self).__init__(*args, **kwargs)
        self.user = self.scope["user"]
        self.ans_info = None

    def connect(self):
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        self.ans_info = json.loads(text_data)
        self.run()

    def disconnect(self, code):
        pass

    def run(self):
        date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        # uuid作为redis key，把命令执行过程放入redis中。
        _uuid = str(uuid.uuid4())
        task_name = self.ans_info.get('task_name')
        host_user = self.ans_info.get('host_user')
        execute = self.ans_info.get('execute')
        _task = Task.objects.create(
            uuid=_uuid,
            name=date_now + "-" + task_name,
            user=self.user,
            exec_type=execute
        )
        try:
            data = {
                "host_user": host_user,
                "resource": list(),
                "hosts_file": [self.ans_info.get('inventory')]
            }
            host = self.ans_info.get('host')
            ansible_module = self.ans_info.get('module')
            module_args = self.ans_info.get('args')
            if ansible_module == "raw":
                module_args = self.ans_info.get('command')
            elif ansible_module == "shell":
                module_args = self.ans_info.get('shell')
            elif ansible_module == "custom":
                ansible_module = self.ans_info.get('custom_module')
                module_args = self.ans_info.get('custom_args')
            elif ansible_module == "fetch":
                _task.task_type = "download"
                _task.source_file = self.ans_info.get('src_file')
                _task.destination_file = self.ans_info.get('dest_file')
                tmp_dir = os.path.join(FILE_DOWNLOAD_TMP_DIR, self.user.username, str(_task.id))
                make_directory(tmp_dir)
                module_args = "src={} dest={}-{{{{inventory_hostname}}}} flat=yes".format(
                    self.ans_info.get('src_file'), os.path.join(tmp_dir, self.ans_info.get('dest_file')))
            ans = AnsibleAPI(_task.id, _uuid, sock=self, **data)
            ans.run_ad_hoc(host=host, module_name=ansible_module, module_args=module_args)
            ans.save_result()
            _task.host = host
        except Exception as e:
            _task.error_msg = str(e)
            self.send('<code style="color: #FF0000">\nansible执行模块出错：{}\n</code>'.format(str(e)))
        finally:
            self.close()
        _task.task_nums = TaskLog.objects.filter(task_id=_task.id).count()
        _task.executed = True
        _task.save()


class PlaybookConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super(PlaybookConsumer, self).__init__(*args, **kwargs)
        self.ans_info = None

    def connect(self):
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        self.ans_info = json.loads(text_data)
        self.run()

    def disconnect(self, code):
        pass

    def run(self):
        date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        # uuid作为redis key，把命令执行过程放入redis中。
        _uuid = str(uuid.uuid4())
        task_name = self.ans_info.get('task_name')
        host_user = self.ans_info.get('host_user')
        execute = self.ans_info.get('execute')
        _task = Task.objects.create(
            uuid=_uuid,
            name=date_now + "-" + task_name,
            user=self.user,
            exec_type=execute
        )
        try:
            host = self.ans_info.get('host')
            playbook = self.ans_info.get('playbook')
            extra_vars = self.ans_info.get('extra_vars')
            data = {
                "host_user": host_user,
                "resource": list(),
                "hosts_file": [self.ans_info.get('inventory')],
                "playbook_name": playbook.split('/')[-1]
            }
            ans = AnsibleAPI(_task.id, _uuid, **data)
            ans.run_playbook([playbook], json.loads(extra_vars))
            ans.save_result()
            _task.host = host
        except Exception as e:
            _task.error_msg = str(e)
            self.send('<code style="color: #FF0000">\nansible执行模块出错：{}\n</code>'.format(str(e)))
        finally:
            self.close()
        _task.task_nums = TaskLog.objects.filter(task_id=_task.id).count()
        _task.executed = True
        _task.save()


class JobConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super(JobConsumer, self).__init__(*args, **kwargs)
        self.user = self.scope["user"]
        self.ans_info = None

    def connect(self):
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        self.ans_info = json.loads(text_data)
        self.run()

    def disconnect(self, code):
        pass

    def run(self):
        job_id = self.ans_info.get('job_id')
        job = Job.objects.get(id=job_id)
        date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        _task = Task.objects.create(
            uuid=str(uuid.uuid4()),
            job=job,
            name=date_now + "-" + job.name,
            user=self.user,
            exec_type=job.exec_type,
            host=job.host
        )
        try:
            data = {
                "host_user": job.host_user.id,
                "resource": list(),
                "hosts_file": [job.inventory]
            }
            if _task.exec_type == "ad-hoc":
                ans = AnsibleAPI(_task.id, _task.uuid, sock=self, **data)
                ans.run_ad_hoc(host=job.host, module_name=job.module_name, module_args=job.module_args)
            elif _task.exec_type == "playbook":
                data.update({
                    "playbook_name": job.playbook.split('/')[-1]
                })
                ans = AnsibleAPI(_task.id, _task.uuid, sock=self, **data)
                ans.run_playbook([job.playbook], json.loads(job.extra_vars))
            else:
                raise Exception("暂不支持其他执行方式！")
            ans.save_result()
        except Exception as e:
            _task.error_msg = str(e)
            self.send('<code style="color: #FF0000">\nansible执行模块出错：{}\n</code>'.format(str(e)))
        finally:
            self.close()
        _task.task_nums = TaskLog.objects.filter(task_id=_task.id).count()
        _task.executed = True
        _task.save()


class AppConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super(AppConsumer, self).__init__(*args, **kwargs)
        self.ans_info = None

    def connect(self):
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        self.ans_info = json.loads(text_data)
        self.run()

    def disconnect(self, code):
        pass

    def run(self):
        try:
            app = App.objects.get(id=self.ans_info.get('app_id'))
            if self.ans_info.get('action') == "backup_code":
                resource = GenResource().gen_host_dict_by_app_id(self.ans_info.get('app_id'))
                ans = AnsibleAPI(0, str(uuid.uuid4()), sock=self, resource=resource, hosts_file=None)
                playbook = ["/data/ansible/playbook/admin/app_offline.yml"]
                extra_vars = {"apphost": app.app_code, "app_code": app.app_code,
                              "tomcat_port": app.tomcat_port, "app_type": app.app_type}
                ans.run_playbook(playbook=playbook, extra_vars=extra_vars)
        except Exception as e:
            self.send('<code style="color: #FF0000">\nansible执行playbook出错：{}\n</code>'.format(traceback.print_exc()))
        finally:
            self.close()

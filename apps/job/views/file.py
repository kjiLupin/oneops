# -*- coding: utf-8 -*-
import re
import os
import traceback
import uuid
import datetime
import zipfile
import simplejson as json
from io import BytesIO
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin
from common.utils.base import send_msg_to_admin, make_directory, FILE_UPLOAD_TMP_DIR, FILE_DOWNLOAD_TMP_DIR
from .cmd_execute import async_func

from job.models.job import HostUser, Task, TaskLog


class FileUploadView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_file_upload'
    template_name = 'job/file_upload.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': '快速文件分发',
            'host_users': [{"id": h.id, "name": h.username, "desc": h.description} for h in HostUser.objects.all()]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request):
        try:
            date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            redis_key = str(uuid.uuid4())
            task_name = request.POST.get('task_name')
            host_user = request.POST.get('host_user')
            program = request.POST.get('program')
            execute = request.POST.get('execute')
            task = Task.objects.create(
                name=date_now + "-" + task_name,
                user=request.user,
                exec_type=execute,
                task_type="upload"
            )
            data = {
                "host_user": host_user,
                "resource": list(),
                "hosts_file": [request.POST.get('inventory')]
            }
            if program == "ansible":
                host = request.POST.get('host')
                ansible_module = request.POST.get('module')
                # 获取上传的文件，并拷贝到目标主机
                upload_args = request.POST.get('upload_args')
                upload_files = request.FILES.getlist('upload_file', [])
                if len(upload_files) == 0:
                    task.error_msg = '文件未上传成功！'
                    task.save(update_fields=['task_type', 'error_msg'])
                    return self.render_json_response({'code': 1, 'errmsg': '文件未上传成功！'})
                task.source_file = '|'.join([u_file.name for u_file in upload_files])
                task.save(update_fields=['source_file'])
                if re.match(r'dest=\S+', upload_args):
                    task.destination_file = re.match(r'(?:dest=)\S+', upload_args).group().replace('dest=', '')
                    task.save(update_fields=['destination_file'])
                else:
                    task.error_msg = '缺少参数"dest=/path/to/"'
                    task.save(update_fields=['error_msg'])
                    return self.render_json_response({'code': 1, 'errmsg': '缺少参数"dest=/path/to/"'})
                tmp_dir = os.path.join(FILE_UPLOAD_TMP_DIR, request.user.username, str(task.id))
                make_directory(tmp_dir)
                for u_file in upload_files:
                    file_path = os.path.join(tmp_dir, u_file.name)
                    with open(file_path, 'wb') as f:
                        for chunk in u_file.chunks():
                            f.write(chunk)
                    data.update({
                        "module_name": ansible_module,
                        "module_args": "src={} {}".format(file_path, upload_args)
                    })
                    async_func.delay(task.id, redis_key, host=host, **data)
            else:
                # paramiko
                task = Task.objects.create(
                    name=date_now + "-" + task_name,
                    user=request.user,
                    exec_type=program
                )
        except Exception as e:
            send_msg_to_admin(traceback.print_exc())
            return self.render_json_response({'code': 1, 'errmsg': str(e)})
        return self.render_json_response({'code': 0, 'result': '命令已提交！'})


class FileDownloadView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_file_download'
    template_name = 'job/file_download.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': '快速文件下载',
            'host_users': [{"id": h.id, "name": h.username, "desc": h.description} for h in HostUser.objects.all()]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request):
        try:
            date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            redis_key = str(uuid.uuid4())
            task_name = request.POST.get('task_name')
            host_user = request.POST.get('host_user')
            program = request.POST.get('program')
            execute = request.POST.get('execute')
            task = Task.objects.create(
                name=date_now + "-" + task_name,
                user=request.user,
                exec_type=execute,
                task_type="download"
            )
            data = {
                "host_user": host_user,
                "resource": list(),
                "hosts_file": [request.POST.get('inventory')]
            }
            if program == "ansible":
                host = request.POST.get('host')
                ansible_module = request.POST.get('module')

                # 获取远程主机上的文件，并下载到本机
                src_file = request.POST.get('src_file')
                dest_file = request.POST.get('dest_file')
                task.source_file = src_file
                task.destination_file = dest_file
                task.save(update_fields=['source_file', 'destination_file'])

                tmp_dir = os.path.join(FILE_DOWNLOAD_TMP_DIR, request.user.username, str(task.id))
                make_directory(tmp_dir)
                data.update({
                    "module_name": ansible_module,
                    "module_args": "src={} dest={}-{{{{inventory_hostname}}}} flat=yes".format(
                        src_file, os.path.join(tmp_dir, dest_file))
                })
                async_func.delay(task.id, redis_key, host=host, **data)
            else:
                # paramiko
                task = Task.objects.create(
                    name=date_now + "-" + task_name,
                    user=request.user,
                    exec_type=program
                )
        except Exception as e:
            send_msg_to_admin(traceback.print_exc())
            return self.render_json_response({'code': 1, 'errmsg': str(e)})
        return self.render_json_response({'code': 0, 'result': '命令已提交！'})


class FileDownloadExportView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_file_download'

    def get(self, request, **kwargs):
        try:
            task_id = kwargs.get('id')
            task_name = Task.objects.get(id=task_id).name
            # Open StringIO to grab in-memory ZIP contents
            s = BytesIO()

            # The zip compressor
            archive = zipfile.ZipFile(s, "w")
            path = os.path.join(FILE_DOWNLOAD_TMP_DIR, request.user.username, task_id)
            for file_name in os.listdir(path):
                archive.write(os.path.join(path, file_name), file_name)
            archive.close()
            response = HttpResponse(s.getvalue(), content_type="application/x-zip-compressed")
            response['Content-Disposition'] = 'attachment; filename=%s.zip' % task_name.split('-')[-1]
            return response
        except Exception as e:
            return HttpResponse(str(e))

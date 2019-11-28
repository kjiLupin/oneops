import os
import shutil
import re
import time
from django.views.generic import TemplateView

from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin
from django.http import QueryDict, JsonResponse

from job.models.job import JobConfig


def file_path_auditor(user, file_path):
    root_path = JobConfig.objects.get(item='playbook_path').value
    if not re.match(root_path, file_path):
        return False, 'Playbook根目录设置有误！'
    if not user.is_superuser:
        re_path = os.path.join(root_path, user.username)
        if not re.match(re_path, file_path):
            return False, '只允许查看自己的文件！'
    return True, ""


class PlaybookView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_job_playbook_view'
    template_name = 'job/playbook.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': 'Playbook'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class PlaybookListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_playbook_view'

    def get(self, request, **kwargs):
        result = list()
        try:
            playbook = JobConfig.objects.get(item='playbook_path')
            if os.path.exists(playbook.value):
                if request.user.is_superuser:
                    playbook_path = playbook.value
                    if not os.path.exists(os.path.join(playbook_path, request.user.username)):
                        os.mkdir(os.path.join(playbook_path, request.user.username))
                    if not os.path.exists(os.path.join(playbook_path, "public")):
                        os.mkdir(os.path.join(playbook_path, "public"))
                else:
                    playbook_path = os.path.join(playbook.value, request.user.username)
                if not os.path.exists(playbook_path):
                    os.mkdir(playbook_path)
                generator = os.walk(playbook_path)
                for parent, dir_names, _ in sorted(generator, key=lambda key: key[0]):
                    for name in sorted(dir_names):
                        result.append({'id': os.path.join(parent, name), 'name': name + "/", 'parent_id': parent})
            else:
                return JsonResponse({"code": 1, "errmsg": "Playbook目录异常：%s" % playbook.value}, safe=True)
        except JobConfig.DoesNotExist:
            pass
        except Exception as e:
            print(e)
        return self.render_json_response(result)

    def post(self, request):
        # 新增子目录
        if not request.user.has_perm('auth.perm_job_playbook_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        parent_dir = request.POST.get('parent_id')
        dir_name = request.POST.get('dir_name')
        try:
            if not re.match(JobConfig.objects.get(item='playbook_path').value, parent_dir):
                return self.render_json_response({'code': 1, 'errmsg': '未设置Playbook根目录！'})
            new_path = os.path.join(parent_dir, dir_name)
            os.mkdir(new_path)
            res = {'code': 0, 'result': '添加成功！'}
        except Exception as e:
            res = {'code': 1, 'errmsg': str(e)}
        return self.render_json_response(res)


class PlaybookDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_job_playbook_view', 'perm_job_playbook_edit')

    def put(self, request, *args, **kwargs):
        # 重命名目录
        try:
            data = QueryDict(request.body).copy()
            old_path = data['old_path']
            new_path = os.path.join(os.path.dirname(old_path), data['new_name'])
            if not re.match(JobConfig.objects.get(item='playbook_path').value, new_path):
                return self.render_json_response({'code': 1, 'errmsg': 'Playbook根目录设置有误！'})
            shutil.move(old_path, new_path)
            res = {"code": 0, "result": "更新成功"}
        except Exception as e:
            res = {"code": 1, "errmsg": "目录重命名出错：%s" % str(e)}
        return JsonResponse(res, safe=True)

    def delete(self, request, *args, **kwargs):
        # 删除子目录
        if not request.user.has_perm('auth.perm_job_playbook_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增！'})
        data = QueryDict(request.body).copy()
        stat, output = file_path_auditor(request.user, data['dir_name'])
        if stat is False:
            return self.render_json_response({'code': 1, 'errmsg': output})
        try:
            if os.path.exists(data['dir_name']):
                shutil.rmtree(data['dir_name'])
                res = {"code": 0, "result": "删除成功"}
            else:
                res = {"code": 1, "errmsg": "目录不存在：%s" % data['dir_name']}
        except Exception as e:
            res = {"code": 1, "errmsg": "删除出错：%s" % str(e)}
        return JsonResponse(res, safe=True)


class PlaybookFileListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_playbook_view'

    def get(self, request, **kwargs):
        # 列出家目录下的playbook文件
        result = list()
        try:
            path = request.GET.get('path')
            if path is None or not os.path.exists(path):
                self.render_json_response(result)
            stat, output = file_path_auditor(request.user, path)
            if stat is False:
                return self.render_json_response({'code': 1, 'errmsg': output})

            search = request.GET.get('search', '')
            for f in os.listdir(path):
                if search not in f:
                    continue
                if not re.search(r'.*\.yml$|.*\.yaml$', f, re.I):
                    continue
                file_path = os.path.join(path, f)
                state = os.stat(file_path)
                mtime = time.strftime("%Y-%m-%d %X", time.localtime(state.st_mtime))
                if os.path.isfile(file_path):
                    size = round(state.st_size / float(1024), 2)
                    result.append({"type": "file", "size": size, "mtime": mtime, "name": f, "path": file_path})
                else:
                    result.append({"type": "dir", "size": "-", "mtime": mtime, "name": f, "path": file_path})

        except JobConfig.DoesNotExist:
            pass
        except Exception as e:
            print(e)
        return self.render_json_response(result)

    def post(self, request, *args, **kwargs):
        # 上传playbook文件
        if not request.user.has_perm('auth.perm_job_playbook_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法上传！'})
        import_files = request.FILES.getlist('files', None)
        if len(import_files) == 0:
            return self.render_json_response({'code': 1, 'errmsg': '上传错误！'})

        parent_dir = request.POST.get('parent_id')
        created, failed = [], []
        for im_file in import_files:
            file_path = os.path.join(parent_dir, im_file.name)
            with open(file_path, 'wb') as f:
                for chunk in im_file.chunks():
                    f.write(chunk)
            if not os.path.isfile(file_path):
                failed.append('{}：文件为空，或上传错误！'.format(im_file.name))
                continue
            created.append('{}：上传成功！'.format(im_file.name))

        data = {
            'code': 0,
            'created': created,
            'created_info': 'Created {}'.format(len(created)),
            'failed': failed,
            'failed_info': 'Failed {}'.format(len(failed)),
            'msg': 'Created: {}, Error: {}'.format(len(created), len(failed))
        }
        return self.render_json_response(data)


class PlaybookFileView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_playbook_view'

    def get(self, request, *args, **kwargs):
        file_path = "/" + kwargs.get('file')
        stat, output = file_path_auditor(request.user, file_path)
        if stat is False:
            return self.render_json_response({'code': 1, 'errmsg': output})
        if os.path.isfile(file_path):
            with open(file_path, 'r') as content_file:
                file_content = content_file.read()
        return self.render_json_response({'code': 0, 'result': file_content})

    def post(self, request, *args, **kwargs):
        # 保存playbook文件
        if not request.user.has_perm('auth.perm_job_playbook_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法保存！'})
        file_content = request.POST.get('cont')
        file_path = "/" + kwargs.get('file')
        try:
            stat, output = file_path_auditor(request.user, file_path)
            if stat is False:
                return self.render_json_response({'code': 1, 'errmsg': output})
            with open(file_path, 'w') as content_file:
                content_file.write(file_content)
            res = {"code": 0, "result": "更新成功"}
        except Exception as e:
            res = {"code": 1, "errmsg": "保存Playbook文件出错：%s" % str(e)}
        return JsonResponse(res, safe=True)

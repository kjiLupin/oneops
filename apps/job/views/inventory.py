import os
import shutil
import re
import time
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin
from django.http import QueryDict, JsonResponse

from job.models.job import JobConfig


def file_path_auditor(user, file_path):
    root_path = JobConfig.objects.get(item='inventory_path').value
    if not re.match(root_path, file_path):
        return False, 'Inventory根目录设置有误！'
    if not user.is_superuser:
        re_path = os.path.join(root_path, user.username)
        if not re.match(re_path, file_path):
            return False, '只允许查看自己的文件！'
    return True, ""


class InventoryView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_job_inventory_view'
    template_name = 'job/inventory.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': 'Inventory'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class InventoryListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_inventory_view'

    def get(self, request, **kwargs):
        result = list()
        try:
            inventory = JobConfig.objects.get(item='inventory_path')
            if os.path.exists(inventory.value):
                if request.user.is_superuser:
                    inventory_path = inventory.value
                    if not os.path.exists(os.path.join(inventory_path, request.user.username)):
                        os.mkdir(os.path.join(inventory_path, request.user.username))
                    if not os.path.exists(os.path.join(inventory_path, "public")):
                        os.mkdir(os.path.join(inventory_path, "public"))
                else:
                    inventory_path = os.path.join(inventory.value, request.user.username)
                if not os.path.exists(inventory_path):
                    os.mkdir(inventory_path)
                generator = os.walk(inventory_path)
                for parent, dir_names, _ in sorted(generator, key=lambda key: key[0]):
                    for name in sorted(dir_names):
                        result.append({'id': os.path.join(parent, name), 'name': name + "/", 'parent_id': parent})
            else:
                return JsonResponse({"code": 1, "errmsg": "Inventory目录异常：%s" % inventory.value}, safe=True)
        except JobConfig.DoesNotExist:
            pass
        except Exception as e:
            print(e)
        return self.render_json_response(result)

    def post(self, request):
        # 添加子目录
        if not request.user.has_perm('auth.perm_job_inventory_edit'):
            return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法新增目录！'})
        parent_dir = request.POST.get('parent_id')
        dir_name = request.POST.get('dir_name')
        try:
            if not re.match(JobConfig.objects.get(item='inventory_path').value, parent_dir):
                return self.render_json_response({'code': 1, 'errmsg': '未设置Inventory根目录！'})
            new_path = os.path.join(parent_dir, dir_name)
            os.mkdir(new_path)
            res = {'code': 0, 'result': '添加成功！'}
        except Exception as e:
            res = {'code': 1, 'errmsg': str(e)}
        return self.render_json_response(res)


class InventoryDetailView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = ('auth.perm_job_inventory_view', 'auth.perm_job_inventory_edit')

    def put(self, request, *args, **kwargs):
        # 重命名目录
        try:
            data = QueryDict(request.body).copy()
            old_path = data['old_path']
            new_path = os.path.join(os.path.dirname(old_path), data['new_name'])
            if not re.match(JobConfig.objects.get(item='inventory_path').value, new_path):
                return self.render_json_response({'code': 1, 'errmsg': 'Inventory根目录设置有误！'})
            shutil.move(old_path, new_path)
            res = {"code": 0, "result": "更新成功"}
        except Exception as e:
            res = {"code": 1, "errmsg": "目录重命名出错：%s" % str(e)}
        return JsonResponse(res, safe=True)

    def delete(self, request, *args, **kwargs):
        # 删除目录
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


class InventoryHostsFileListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_inventory_view'

    def get(self, request, **kwargs):
        # 列出家目录下的Inventory文件
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
        # 上传inventory文件
        if not request.user.has_perm('auth.perm_job_inventory_edit'):
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


class InventoryHostsFileView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_inventory_view'

    def get(self, request, *args, **kwargs):
        # 获取inventory文件内容
        file_path = "/" + kwargs.get('file')
        stat, output = file_path_auditor(request.user, file_path)
        if stat is False:
            return self.render_json_response({'code': 1, 'errmsg': output})
        if os.path.isfile(file_path):
            with open(file_path, 'r') as content_file:
                file_content = content_file.read()
        else:
            return self.render_json_response({'code': 1, 'errmsg': "文件不存在！"})
        return self.render_json_response({'code': 0, 'result': file_content})

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        # 编辑inventory文件并保存
        if not request.user.has_perm('auth.perm_job_inventory_edit'):
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
            res = {"code": 1, "errmsg": "保存Inventory文件出错：%s" % str(e)}
        return JsonResponse(res, safe=True)

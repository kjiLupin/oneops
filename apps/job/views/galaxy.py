import os
import re
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin
from django.http import JsonResponse

from job.models.job import JobConfig


def file_path_auditor(user, file_path):
    root_path = JobConfig.objects.get(item='roles_path').value
    if not re.match(root_path, file_path):
        return False, 'Inventory根目录设置有误！'
    if not user.is_superuser:
        re_path = os.path.join(root_path, user.username)
        if not re.match(re_path, file_path):
            return False, '只允许查看自己的文件！'
    return True, ""


class GalaxyView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_job_galaxy_view'
    template_name = 'job/galaxy.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': 'Roles集合'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class GalaxyRolesListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_galaxy_view'

    def get(self, request, **kwargs):
        result = list()
        try:
            roles = JobConfig.objects.get(item='roles_path')
            if os.path.exists(roles.value):
                if request.user.is_superuser:
                    roles_path = roles.value
                    if not os.path.exists(os.path.join(roles_path, request.user.username)):
                        os.mkdir(os.path.join(roles_path, request.user.username))
                    if not os.path.exists(os.path.join(roles_path, "public")):
                        os.mkdir(os.path.join(roles_path, "public"))
                else:
                    roles_path = os.path.join(roles.value, request.user.username)
                if not os.path.exists(roles_path):
                    os.mkdir(roles_path)
                generator = os.walk(roles_path)
                for parent, dir_names, file_names in sorted(generator, key=lambda key: key[0]):
                    for name in sorted(dir_names):
                        result.append({'id': os.path.join(parent, name), 'name': name + "/", 'parent_id': parent})
                    for name in sorted(file_names):
                        result.append({'id': os.path.join(parent, name), 'name': name, 'parent_id': parent})
            else:
                return self.render_json_response({"code": 1, "errmsg": "Roles目录异常：%s" % roles.value})
        except JobConfig.DoesNotExist:
            pass
        except Exception as e:
            print(e)
        return self.render_json_response(result)


class GalaxyRolesFileView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_galaxy_view'

    def get(self, request, *args, **kwargs):
        # 获取roles文件内容
        file_path = "/" + kwargs.get('file')
        stat, output = file_path_auditor(request.user, file_path)
        if stat is False:
            return self.render_json_response({'code': 1, 'errmsg': output})
        if os.path.isfile(file_path):
            with open(file_path, 'r') as content_file:
                file_content = content_file.read()
        return self.render_json_response({'code': 0, 'result': file_content})

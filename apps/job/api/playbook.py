import os
import shutil
import re
import time
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.versioning import URLPathVersioning
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin
from django.http import QueryDict, JsonResponse

from job.models.job import JobConfig, Job


class PlaybookListAPIView(JSONResponseMixin, APIView):
    versioning_class = URLPathVersioning

    def dispatch(self, request, *args, **kwargs):
        """
        请求到来之后，都要执行dispatch方法，dispatch方法根据请求方式不同触发 get/post/put等方法
        注意：APIView中的dispatch方法有好多好多的功能。
        """
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **kwargs):
        # 获取该用户可用的Playbook文件，即public目录及家目录下所有文件
        result = list()
        try:
            root_path = JobConfig.objects.get(item='playbook_path').value
            for item in ['public', request.user.username]:
                path = os.path.join(root_path, item)
                if not os.path.exists(path):
                    continue
                generator = os.walk(path)
                for parent, dir_names, file_names in sorted(generator, key=lambda key: key[0]):
                    for name in sorted(file_names):
                        if not re.search(r'.*\.yml$|.*\.yaml$', name, re.I):
                            continue
                        result.append({
                            'path': os.path.join(parent, name),
                            'name': os.path.join(parent[len(root_path):], name)
                        })
        except JobConfig.DoesNotExist:
            return self.render_json_response({'error': 'JobConfig.DoesNotExist'})
        except Exception as e:
            return self.render_json_response({'error': str(e)})
        return self.render_json_response(result)


class PlaybookConflictAPIView(JSONResponseMixin, APIView):

    def get(self, request, **kwargs):
        # 修改playbook时，先判断是否有作业、定时任务依赖它
        file_path = request.GET.get('file_path')
        if Job.objects.filter(playbook=file_path).exists():
            jobs = ','.join([j.name for j in Job.objects.filter(playbook=file_path)])
            return self.render_json_response({'code': 0, 'result': jobs})
        else:
            return self.render_json_response({'code': 1})

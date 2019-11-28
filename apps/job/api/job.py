
from rest_framework.views import APIView
from rest_framework.versioning import URLPathVersioning
from common.mixins import JSONResponseMixin

from job.models.job import JobConfig, Job


class JobListAPIView(JSONResponseMixin, APIView):
    versioning_class = URLPathVersioning

    def dispatch(self, request, *args, **kwargs):
        """
        请求到来之后，都要执行dispatch方法，dispatch方法根据请求方式不同触发 get/post/put等方法
        注意：APIView中的dispatch方法有好多好多的功能。
        """
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, **kwargs):
        # 获取该用户可用的作业
        result = list()
        try:
            if request.user.is_superuser:
                obj_list = Job.objects.filter(active=True)
            else:
                obj_list = Job.objects.filter(active=True).filter(public=True).filter(created_by=request.user)
            for o in obj_list:
                result.append({
                    'id': o.id,
                    'name': o.name,
                    'desc': o.description
                })
        except Exception as e:
            print(e)
            return self.render_json_response(result)
        return self.render_json_response(result)


class JobDetailAPIView(JSONResponseMixin, APIView):

    def get(self, request, **kwargs):
        # 作业执行页面，查看作业详细接口
        pk = kwargs.get('pk')
        p = Job.objects.get(pk=pk)
        inventory_path = JobConfig.objects.get(item='inventory_path').value
        playbook_path = JobConfig.objects.get(item='playbook_path').value
        if p.task_type == "command":
            if p.exec_type == "paramiko":
                job = """作业名：{}\n作业类型：{}\n执行用户：{}\n执行方式：{}\n命令：{}\n目标机器：{}\n描述：{}\n创建人：{}\n创建时间：{}""".format(
                    p.name, p.get_task_type_display(), p.host_user.username,
                    p.exec_type, p.cmd, p.host, p.description, p.created_by.display, p.creation_date)
            elif p.exec_type == "ad-hoc":
                job = """作业名：{}\n作业类型：{}\n执行用户：{}\n执行方式：{}\n目标机器：{}\nhosts文件：{}\nAnsible模块：{}\nAnsible参数：{}\n描述：{}\n创建人：{}\n创建时间：{}""".format(
                    p.name, p.get_task_type_display(), p.host_user.username,
                    p.exec_type, p.host, p.inventory.replace(inventory_path, ""), p.module_name, p.module_args,
                    p.description, p.created_by.display, p.creation_date)
            else:
                # playbook
                job = """作业名：{}\n作业类型：{}\n执行用户：{}\n执行方式：{}\n目标机器：{}\nhosts文件：{}\nPlaybook：{}\nPlaybook参数：{}\n描述：{}\n创建人：{}\n创建时间：{}""".format(
                    p.name, p.get_task_type_display(), p.host_user.username,
                    p.exec_type, p.host, p.inventory.replace(inventory_path, ""), p.playbook.replace(playbook_path, ""),
                    p.extra_vars, p.description, p.created_by.display, p.creation_date)
        elif p.task_type == "download":
            job = """作业名：{}\n作业类型：{}\n执行用户：{}\n执行方式：{}\n目标机器：{}\n下载文件名：{}\n描述：{}\n创建人：{}\n创建时间：{}""".format(
                p.name, p.get_task_type_display(), p.host_user.username,
                p.exec_type, p.host, p.destination_file, p.description,
                p.created_by.display, p.creation_date)
        else:
            job = "不支持上传文件的作业！"
        return self.render_json_response({'code': 0, 'result': job})

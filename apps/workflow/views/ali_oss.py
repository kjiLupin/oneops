# -*- coding: utf-8 -*-
import os
import time
from django.db.models import Q, F
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from common.utils.base import BASE_DIR, get_random_string
from common.mixins import JSONResponseMixin

from workflow.models import Workflow, CommonFlow, FlowStep
from workflow.utils.aliyun_oss import upload_apk_to_ali_oss, AliOSSManager
from cmdb.models.base import OSS


def get_random_file_name(file_name):
    pos = file_name.index('.')
    return get_random_string() + file_name[pos:]


class AliOSSView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/ali_oss.html"

    def get_context_data(self, **kwargs):
        wf = Workflow.objects.get(code='ali_oss')
        context = {
            "path1": "Workflow",
            "path2": "Aliyun OSS",
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name,
            "oss_list": OSS.objects.filter(supplier='aliyun')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        # 上传文件到 阿里云 oss
        wf = Workflow.objects.get(code='ali_oss')
        if not FlowStep.objects.filter(workflow=wf).exists():
            return self.render_json_response({"code": -1, "errmsg": "该流程未配置工单步骤！"})
        oss_id = request.POST.get('oss', '')
        path = request.POST.get('path')
        file_name = request.POST.get('file_name', 'local_name')
        upload_files = request.FILES.getlist('upload_file[]')
        if not oss_id or not OSS.objects.filter(id=oss_id).exists():
            return self.render_json_response({"code": -1, "errmsg": "未找到该OSS！"})
        oss = OSS.objects.get(id=oss_id)
        try:
            today = time.strftime("%Y-%m-%d", time.localtime())
            oss_temp_dir = os.path.join(BASE_DIR, "logs", today)
            if not os.path.exists(oss_temp_dir):
                os.mkdir(oss_temp_dir)
            om = AliOSSManager(oss)
            result = list()
            for f in upload_files:
                file_path = os.path.join(oss_temp_dir, f.name)
                with open(file_path, 'wb+') as info:
                    for chunk in f.chunks():
                        info.write(chunk)
                if file_name == 'local_name':
                    uri = os.path.join(path, f.name)
                else:
                    uri = os.path.join(path, get_random_file_name(f.name))
                ret = om.put_file(uri, file_path)
                if ret == 200:
                    result.append("%s Succeeded：https://oss.yadoom.com/%s" % (f.name, uri))
                else:
                    result.append("%s Failed." % f.name)
        except Exception as e:
            return self.render_json_response({"code": -1, "errmsg": str(e)})
        wf.counts = F('counts') + 1
        wf.save()
        content = "、".join([f.name for f in upload_files])
        cf = CommonFlow.objects.create(workflow=wf, applicant=request.user, status='end', content=content,
                                       result="\n".join(result))
        return self.render_json_response({"code": 0, "result": {"id": cf.id}})


class AliOSSDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/ali_oss_detail.html"

    def get_context_data(self, **kwargs):
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)
        context = {
            "path1": "Workflow",
            "path2": "Aliyun OSS",
            "wf_type": cf.workflow.get_wf_type_display(),
            "wf_name": cf.workflow.name,
            "status": cf.status,
            "applicant": cf.applicant.username,
            "reason": cf.reason,
            "content": "申请人：{}\n申请理由：{}\n任务内容：\n{}".format(cf.applicant.username, cf.reason, cf.content),
            "result": cf.result,
            "update_time": cf.update_time
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AliOSSAPKView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/ali_oss_apk.html"

    def get_context_data(self, **kwargs):
        wf = Workflow.objects.get(code='ali_oss_apk')
        context = {
            "path1": "Workflow",
            "path2": "APK 文件上传",
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name,
            "oss_list": OSS.objects.filter(supplier='aliyun')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        # 上传文件到 阿里云 oss
        wf = Workflow.objects.get(code='ali_oss_apk')
        if not FlowStep.objects.filter(workflow=wf).exists():
            return self.render_json_response({"code": -1, "errmsg": "该流程未配置工单步骤！"})
        oss_id = request.POST.get('oss', '')
        upload_files = request.FILES.getlist('upload_file[]')
        if not oss_id or not OSS.objects.filter(id=oss_id).exists():
            return self.render_json_response({"code": -1, "errmsg": "未找到该OSS！"})
        oss = OSS.objects.get(id=oss_id)
        try:
            result = upload_apk_to_ali_oss(oss, upload_files)
        except Exception as e:
            return self.render_json_response({"code": -1, "errmsg": str(e)})
        wf.counts = F('counts') + 1
        wf.save()
        content = "、".join([f.name for f in upload_files])
        cf = CommonFlow.objects.create(workflow=wf, applicant=request.user, status='end',
                                       content=content, result="\n".join(result))
        return self.render_json_response({"code": 0, "result": {"id": cf.id}})


class AliOSSAPKDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/ali_oss_apk_detail.html"

    def get_context_data(self, **kwargs):
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)
        context = {
            "path1": "Workflow",
            "path2": "APK 文件上传",
            "wf_type": cf.workflow.get_wf_type_display(),
            "wf_name": cf.workflow.name,
            "status": cf.status,
            "applicant": cf.applicant.username,
            "reason": cf.reason,
            "content": "申请人：{}\n申请理由：{}\n任务内容：\n{}".format(cf.applicant.username, cf.reason, cf.content),
            "result": cf.result,
            "update_time": cf.update_time
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

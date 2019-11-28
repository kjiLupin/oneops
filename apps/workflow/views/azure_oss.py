# -*- coding: utf-8 -*-
import traceback
from django.db.models import Q, F
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from common.mixins import JSONResponseMixin

from workflow.models import Workflow, CommonFlow, FlowStep
from workflow.utils.azure_oss import upload_apk_to_azure_oss
from cmdb.models.base import OSS


class AzureOSSAPKView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/azure_oss_apk.html"

    def get_context_data(self, **kwargs):
        wf = Workflow.objects.get(code='azure_oss_apk')
        context = {
            "path1": "Workflow",
            "path2": "APK 文件上传",
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name,
            "oss_list": OSS.objects.filter(supplier='azure')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        # 上传文件到 微软云 oss
        wf = Workflow.objects.get(code='azure_oss_apk')
        if not FlowStep.objects.filter(workflow=wf).exists():
            return self.render_json_response({"code": -1, "errmsg": "该流程未配置工单步骤！"})
        oss_id = request.POST.get('oss', '')
        upload_files = request.FILES.getlist('upload_file[]')
        if not oss_id or not OSS.objects.filter(id=oss_id).exists():
            return self.render_json_response({"code": -1, "errmsg": "未找到该OSS！"})
        oss = OSS.objects.get(id=oss_id)
        try:
            result = upload_apk_to_azure_oss(oss, upload_files)
        except Exception as e:
            traceback.print_exc()
            return self.render_json_response({"code": -1, "errmsg": str(e)})
        wf.counts = F('counts') + 1
        wf.save()
        content = "、".join([f.name for f in upload_files])
        cf = CommonFlow.objects.create(workflow=wf, applicant=request.user, status='end',
                                       content=content, result="\n".join(result))
        return self.render_json_response({"code": 0, "result": {"id": cf.id}})


class AzureOSSAPKDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/azure_oss_apk_detail.html"

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

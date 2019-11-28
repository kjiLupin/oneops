# -*- coding: utf-8 -*-
import re
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from common.mixins import JSONResponseMixin

from workflow.models import Workflow, CommonFlow, FlowStep
from workflow.utils.aliyun_cdn import AliCDNManager
from cmdb.models.base import CDN


class AliCDNView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/ali_cdn.html"

    def get_context_data(self, **kwargs):
        wf = Workflow.objects.get(code='ali_cdn')
        context = {
            "path1": "Workflow",
            "path2": "Aliyun CDN",
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name,
            "cdn_list": CDN.objects.filter(supplier='aliyun')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    @csrf_exempt
    def post(self, request, **kwargs):
        wf = Workflow.objects.get(code='ali_cdn')
        if not FlowStep.objects.filter(workflow=wf).exists():
            return self.render_json_response({"code": -1, "errmsg": "该流程未配置工单步骤！"})
        cdn_id = request.POST.get('cdn', '')
        url_path = request.POST.get('url_path', '').strip()
        src_type = request.POST.get('src_type', '')
        if src_type == "Directory":
            if not all(re.search(r'/$', uri) for uri in url_path.split('\r\n')):
                return self.render_json_response({"code": -1, "errmsg": "CDN不存在！"})
        if not cdn_id or not CDN.objects.filter(id=cdn_id).exists():
            return self.render_json_response({"code": -1, "errmsg": "CDN不存在！"})
        cdn = CDN.objects.get(id=cdn_id)
        if not url_path or not src_type:
            return self.render_json_response({"code": -1, "errmsg": "请检查URL地址！"})
        wf_content = 'CDN：{0}（{1}）\n类型：{2}\n路径：{3}'.format(cdn.get_supplier_display(), cdn.comment, src_type, url_path)
        cm = AliCDNManager(cdn)
        ret = [cm.flush(uri, src_type) for uri in url_path.split("\r\n")]
        cf = CommonFlow.objects.create(workflow=wf, applicant=request.user, status='end',
                                       content=wf_content, result='\n'.join(ret))
        return self.render_json_response({"code": 0, "id": cf.id})


class AliCDNDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/ali_cdn_detail.html"

    def get_context_data(self, **kwargs):
        flow_id = kwargs.get('flow_id')
        cf = CommonFlow.objects.get(id=flow_id)
        context = {
            "path1": "Workflow",
            "path2": "Aliyun CDN",
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

# -*- coding: utf-8 -*-
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View
from django.db.models import Q
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from common.mixins import JSONResponseMixin

from workflow.models import Workflow, CommonFlow, CommonFlowArg, FlowStep, FlowStepLog

flow_detail_uri = {
    'ali_cdn': reverse_lazy('workflow:flow-ali-cdn-detail', kwargs={'flow_id': 0}),
    'ali_oss': reverse_lazy('workflow:flow-ali-oss-detail', kwargs={'flow_id': 0}),
    'ali_oss_apk': reverse_lazy('workflow:flow-ali-oss-apk-detail', kwargs={'flow_id': 0}),
    'azure_oss_apk': reverse_lazy('workflow:flow-azure-oss-apk-detail', kwargs={'flow_id': 0}),
    'app_apply': reverse_lazy('workflow:flow-app-apply-detail', kwargs={'flow_id': 0}),
    'app_offline': reverse_lazy('workflow:flow-app-offline-detail', kwargs={'flow_id': 0}),
    'tomcat_dump': reverse_lazy('workflow:flow-tomcat-dump-detail', kwargs={'flow_id': 0}),
    'tomcat_jstack': reverse_lazy('workflow:flow-tomcat-jstack-detail', kwargs={'flow_id': 0}),
    'cross_segment_access': reverse_lazy('workflow:flow-cross-segment-access-detail', kwargs={'flow_id': 0}),
}


class FlowTotalView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/flow_total.html"

    def get_context_data(self, **kwargs):
        context = {
            "path1": "Workflow",
            "path2": "所有流程",
            "workflow_list": [{"id": wf.id, "name": wf.name} for wf in Workflow.objects.filter(is_active=True)]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class FlowTotalListView(LoginRequiredMixin, JSONResponseMixin, TemplateView):

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit'))
        offset = int(request.GET.get('offset'))
        sort_order = request.GET.get("sortOrder", '')
        sort_name = request.GET.get("sortName", 'id')
        if sort_name == 'wf_name' or sort_name == 'wf_type':
            sort_name = 'workflow__{}'.format(sort_name)
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        user = request.user

        if user.is_superuser:
            obj_list = CommonFlow.objects.get_queryset()
        else:
            # 获取我申请的、以及我工单的流程
            cf_id_list = [fal.cf.id for fal in FlowStepLog.objects.filter(operator=user)]
            obj_list = CommonFlow.objects.filter(Q(id__in=cf_id_list) | Q(applicant=user))

        wf_type = request.GET.get("wf_type", '')
        if wf_type:
            obj_list = obj_list.filter(workflow__wf_type=wf_type)
        wf_id = request.GET.get("wf_id", '')
        if wf_id:
            obj_list = obj_list.filter(workflow_id=wf_id)
        status = request.GET.get("status", '')
        if status:
            obj_list = obj_list.filter(status=status)
        search = request.GET.get("search", None)
        if search:
            obj_list = obj_list.filter(Q(applicant__display=search) |
                                       Q(reason__contains=search) |
                                       Q(content__contains=search) |
                                       Q(result__contains=search)).distinct()

        obj_list = obj_list.order_by(sort_name)
        result = list()
        for o in obj_list[offset:(offset + limit)]:
            extra_args = ""
            for cma in CommonFlowArg.objects.filter(cf=o):
                extra_args += '{}: {}\n'.format(cma.arg, cma.value)
            result.append({
                'id': o.id,
                'wf_name': o.workflow.name,
                'wf_type': o.workflow.get_wf_type_display(),
                'detail_uri': flow_detail_uri[o.workflow.code][:-1] + str(o.id),
                'applicant': o.applicant.display,
                'status': o.status,
                'status_display': o.get_status_display(),
                'reason': o.reason,
                'content': o.content,
                'extra_args': extra_args,
                'result': o.result,
                'create_time': o.create_time,
                'update_time': o.update_time})
        res = {"total": obj_list.count(), "rows": result}
        return self.render_json_response(res)


class FlowPendingView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/flow_pending.html"

    def get_context_data(self, **kwargs):
        context = {
            "path1": "Workflow",
            "path2": "待处理流程",
            "workflow_list": [{"id": wf.id, "name": wf.name} for wf in Workflow.objects.filter(is_active=True)]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class FlowPendingListView(LoginRequiredMixin, JSONResponseMixin, TemplateView):

    def get(self, request, **kwargs):
        """
        待处理流程：用户所在用户组包含，该待处理工单的组
        :param request:
        :param kwargs:
        :return:
        """
        sort_order = request.GET.get("sortOrder", '')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        user = request.user

        wf_type = request.GET.get("wf_type", '')
        if wf_type:
            obj_list = CommonFlow.objects.filter(workflow__wf_type=wf_type, status='pending')
        else:
            obj_list = CommonFlow.objects.filter(status='pending')
        wf_id = request.GET.get("wf_id", '')
        if wf_id:
            obj_list = obj_list.filter(workflow_id=wf_id)
        search = request.GET.get("search", None)
        if search:
            obj_list = obj_list.filter(Q(reason__contains=search) |
                                       Q(content__contains=search) |
                                       Q(result__contains=search)).distinct()

        obj_list = obj_list.order_by(sort_name)
        result = list()
        for cf in obj_list:
            # 获取该流程的工单步骤
            fas = FlowStep.objects.filter(workflow=cf.workflow, step=1)
            if user.is_superuser or cf.applicant == user or fas.group in user.groups.all():
                extra_args = ""
                for cma in CommonFlowArg.objects.filter(cf=cf):
                    extra_args += '{}: {}\n'.format(cma.arg, cma.value)
                result.append({
                    'id': cf.id,
                    'wf_name': cf.workflow.name,
                    'wf_type': cf.workflow.get_wf_type_display(),
                    'detail_uri': flow_detail_uri[cf.workflow.code][:-1] + str(cf.id),
                    'applicant': cf.applicant.display,
                    'reason': cf.reason,
                    'content': cf.content,
                    'extra_args': extra_args,
                    'result': cf.result,
                    'create_time': cf.create_time,
                    'update_time': cf.update_time})
        return self.render_json_response(result)


class FlowOngoingView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/flow_ongoing.html"

    def get_context_data(self, **kwargs):
        context = {
            "path1": "Workflow",
            "path2": "未完成的流程",
            "workflow_list": [{"id": wf.id, "name": wf.name} for wf in Workflow.objects.filter(is_active=True)]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class FlowOngoingListView(LoginRequiredMixin, JSONResponseMixin, TemplateView):

    def get(self, request, **kwargs):
        sort_order = request.GET.get("sortOrder", '')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        user = request.user

        wf_type = request.GET.get("wf_type", '')
        if wf_type:
            obj_list = CommonFlow.objects.filter(workflow__wf_type=wf_type, status='ongoing')
        else:
            obj_list = CommonFlow.objects.filter(status='ongoing')
        wf_id = request.GET.get("wf_id", '')
        if wf_id:
            obj_list = obj_list.filter(workflow_id=wf_id)
        search = request.GET.get("search", None)
        if search:
            obj_list = obj_list.filter(Q(reason__contains=search) |
                                       Q(content__contains=search) |
                                       Q(result__contains=search)).distinct()

        obj_list = obj_list.order_by(sort_name)
        result = list()
        for cf in obj_list:
            # 获取该流程的当前的步骤
            next_step = 1
            if FlowStepLog.objects.filter(cf=cf).exists():
                last_fas = FlowStepLog.objects.filter(cf=cf).order_by('-id')
                next_step = last_fas[0].flow_step.step + 1
            fas = FlowStep.objects.get(workflow=cf.workflow, step=next_step)
            if user.is_superuser or cf.applicant == user or fas.group in user.groups.all():
                extra_args = ""
                for cma in CommonFlowArg.objects.filter(cf=cf):
                    extra_args += '{}: {}\n'.format(cma.arg, cma.value)
                result.append({
                    'id': cf.id,
                    'wf_name': cf.workflow.name,
                    'wf_type': cf.workflow.get_wf_type_display(),
                    'detail_uri': flow_detail_uri[cf.workflow.code][:-1] + str(cf.id),
                    'applicant': cf.applicant.display,
                    'status': cf.get_status_display(),
                    'reason': cf.reason,
                    'content': cf.content,
                    'extra_args': extra_args,
                    'result': cf.result,
                    'create_time': cf.create_time,
                    'update_time': cf.update_time})
        return self.render_json_response(result)


class FlowEndView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/flow_end.html"

    def get_context_data(self, **kwargs):
        context = {
            "path1": "Workflow",
            "path2": "已归档的流程",
            "workflow_list": [{"id": wf.id, "name": wf.name} for wf in Workflow.objects.filter(is_active=True)]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class FlowEndListView(LoginRequiredMixin, JSONResponseMixin, TemplateView):

    def get(self, request, **kwargs):
        limit = int(request.GET.get('limit', 14))
        offset = int(request.GET.get('offset', 0))
        sort_order = request.GET.get("sortOrder", '')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        user = request.user

        wf_type = request.GET.get("wf_type", '')
        if wf_type:
            if user.is_superuser:
                obj_list = CommonFlow.objects.filter(applicant=user, workflow__wf_type=wf_type,
                                                     status__in=['cancel', 'rejected', 'end'])
            else:
                obj_list = CommonFlow.objects.filter(workflow__wf_type=wf_type,
                                                     status__in=['cancel', 'rejected', 'end'])
        else:
            if user.is_superuser:
                obj_list = CommonFlow.objects.filter(status__in=['cancel', 'rejected', 'end'])
            else:
                obj_list = CommonFlow.objects.filter(applicant=user, status__in=['cancel', 'rejected', 'end'])
        wf_id = request.GET.get("wf_id", '')
        if wf_id:
            obj_list = obj_list.filter(workflow_id=wf_id)
        search = request.GET.get("search", '')
        if search:
            obj_list = obj_list.filter(Q(reason__contains=search) |
                                       Q(content__contains=search) |
                                       Q(result__contains=search)).distinct()

        obj_list = obj_list.order_by(sort_name)
        result = list()
        for cf in obj_list[offset:(offset + limit)]:
            extra_args = ""
            for cma in CommonFlowArg.objects.filter(cf=cf):
                extra_args += '{}: {}\n'.format(cma.arg, cma.value)
            result.append({
                'id': cf.id,
                'wf_name': cf.workflow.name,
                'wf_type': cf.workflow.get_wf_type_display(),
                'detail_uri': flow_detail_uri[cf.workflow.code][:-1] + str(cf.id),
                'applicant': cf.applicant.display,
                'status': cf.status,
                'status_display': cf.get_status_display(),
                'reason': cf.reason,
                'content': cf.content,
                'extra_args': extra_args,
                'result': cf.result,
                'create_time': cf.create_time,
                'update_time': cf.update_time})
        res = {"total": obj_list.count(), "rows": result}
        return self.render_json_response(res)

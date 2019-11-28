# -*- coding: utf-8 -*-
from django.views.generic import TemplateView, View
from django.db.models import Q, F
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from common.mixins import JSONResponseMixin

from django.contrib.auth.models import Group
from workflow.models import Workflow, FlowStep


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/dashboard.html"

    def get_context_data(self, **kwargs):
        context = {
            "most_used_list": [
                {"name": wf.name, "uri": wf.uri, "comment": wf.comment}
                for wf in Workflow.objects.filter(is_active=True).order_by('-counts')[:8]
            ]
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class WorkflowView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/workflow.html"

    def get_context_data(self, **kwargs):
        context = {
            "path1": "Workflow",
            "path2": "工作流列表"
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class WorkflowListView(LoginRequiredMixin, JSONResponseMixin, TemplateView):

    def get(self, request, **kwargs):
        sort_order = request.GET.get("sortOrder", '')
        sort_name = request.GET.get("sortName", 'id')
        sort_name = sort_name if sort_order == 'asc' else '-' + sort_name

        wf_type = request.GET.get("wf_type", '')
        if wf_type:
            obj_list = Workflow.objects.filter(is_active=True).filter(wf_type=wf_type)
        else:
            obj_list = Workflow.objects.filter(is_active=True)

        search = request.GET.get("search", None)
        if search:
            obj_list = obj_list.filter(Q(title__contains=search) | Q(comment__contains=search)).distinct()

        obj_list = obj_list.order_by(sort_name)
        result = [{
            'id': o.id,
            'name': o.name,
            'counts': o.counts,
            'uri': o.uri,
            'wf_type': o.get_wf_type_display(),
            'comment': o.comment,
            'update_time': o.update_time,
            'flow_steps': FlowStep.objects.filter(workflow=o).count()} for o in obj_list]
        return self.render_json_response(result)


class WorkflowStepsListView(LoginRequiredMixin, JSONResponseMixin, TemplateView):

    def get(self, request, **kwargs):
        wf_id = request.GET.get("wf_id", '')
        if wf_id:
            workflow = Workflow.objects.get(id=wf_id)
            obj_list = FlowStep.objects.filter(workflow=workflow)
        else:
            obj_list = FlowStep.objects.get_queryset()

        result = [{
            'id': o.id,
            'workflow': o.workflow,
            'step': o.step,
            'group': o.group,
            'update_time': o.update_time} for o in obj_list]
        return self.render_json_response(result)


class WorkflowStepsDetailView(LoginRequiredMixin, JSONResponseMixin, TemplateView):
    template_name = "workflow/steps.html"

    def get_context_data(self, **kwargs):
        wf_id = kwargs.get('wf_id')
        wf = Workflow.objects.get(id=wf_id)
        fas_list = FlowStep.objects.filter(workflow=wf).exclude(group=None)
        context = {
            "path1": "Workflow",
            "path2": "流程步骤",
            "id": wf.id,
            "wf_type": wf.get_wf_type_display(),
            "wf_name": wf.name,
            "fas_list": fas_list,
            "group_available": Group.objects.all()
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request, **kwargs):
        try:
            wf_id = kwargs.get('wf_id')
            wf = Workflow.objects.get(id=wf_id)
        except Workflow.DoesNotExist:
            return self.render_json_response({"code": 1, "errmsg": "非法调用！"})
        group1 = request.POST.get("group1", -1)
        group2 = request.POST.get("group2", -1)
        group3 = request.POST.get("group3", -1)
        group4 = request.POST.get("group4", -1)
        group5 = request.POST.get("group5", -1)

        group = Group.objects.filter(id=group1)
        FlowStep.objects.update_or_create(workflow=wf, step=1, defaults={"group": group[0] if group else None})

        group = Group.objects.filter(id=group2)
        FlowStep.objects.update_or_create(workflow=wf, step=2, defaults={"group": group[0] if group else None})

        group = Group.objects.filter(id=group3)
        FlowStep.objects.update_or_create(workflow=wf, step=3, defaults={"group": group[0] if group else None})

        group = Group.objects.filter(id=group4)
        FlowStep.objects.update_or_create(workflow=wf, step=4, defaults={"group": group[0] if group else None})

        group = Group.objects.filter(id=group5)
        FlowStep.objects.update_or_create(workflow=wf, step=5, defaults={"group": group[0] if group else None})

        return self.render_json_response({"code": 0, "result": "更新成功！"})

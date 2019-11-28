from django.contrib import admin
# Register your models here.
from workflow.models import Workflow, FlowStep, FlowStepLog, CommonFlow, CommonFlowArg


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'counts', 'uri', 'wf_type', 'comment', 'is_active', 'update_time')
    search_fields = ['name', 'comment']


@admin.register(FlowStep)
class FlowStepAdmin(admin.ModelAdmin):
    list_display = ('id', 'workflow', 'step', 'group', 'update_time')
    search_fields = ['workflow', 'group']


@admin.register(CommonFlow)
class CommonFlowAdmin(admin.ModelAdmin):
    list_display = ('id', 'workflow', 'applicant', 'status', 'reason', 'content', 'result', 'update_time')
    search_fields = ['workflow', 'applicant', 'content']


@admin.register(CommonFlowArg)
class CommonFlowArgAdmin(admin.ModelAdmin):
    list_display = ('id', 'cf', 'arg', 'value')


@admin.register(FlowStepLog)
class FlowStepLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'cf', 'flow_step', 'operator', 'is_passed', 'reply', 'create_time')

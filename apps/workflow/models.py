from django.db import models
from accounts.models import User
from django.contrib.auth.models import Group


class Workflow(models.Model):
    code = models.CharField('工作流代码', max_length=50)
    name = models.CharField(max_length=50)
    counts = models.IntegerField(default=0)
    uri = models.CharField(max_length=50)
    wf_type = models.CharField(max_length=5, choices=(('prod', '正式环境变更流程'), ('test', '测试环境变更流程'),
                                                      ('apply', '资源申请流程'), ('ops', '运维专用流程')))
    comment = models.CharField(max_length=50, default='')
    is_active = models.BooleanField('是否可用', default=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflow_workflow'
        verbose_name = u'工作流表'
        verbose_name_plural = u'工作流表'


class FlowStep(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    step = models.SmallIntegerField(default=1)
    group = models.ForeignKey(Group, null=True, on_delete=models.SET_NULL)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflow_flow_step'
        unique_together = (('workflow', 'step'),)
        verbose_name = u'工作流步骤表'
        verbose_name_plural = u'工作流步骤表'


class CommonFlow(models.Model):
    flow_status = (('pending', '待处理'), ('ongoing', '处理中'), ('cancel', '主动取消'), ('rejected', '已被拒绝'),
                   ('end', '已结束'))
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    applicant = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=10, choices=flow_status)
    current_step = models.SmallIntegerField(default=1)
    reason = models.CharField('申请理由', max_length=256, default='')
    content = models.TextField('任务内容', blank=True, null=True)
    result = models.TextField(blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflow_common_flow'
        verbose_name = u'工作流通用模板表'
        verbose_name_plural = u'工作流通用模板表'


class CommonFlowArg(models.Model):
    cf = models.ForeignKey(CommonFlow, on_delete=models.CASCADE)
    arg = models.CharField(max_length=50)
    value = models.CharField(max_length=256)

    class Meta:
        db_table = 'workflow_common_flow_arg'
        unique_together = (('cf', 'arg'),)
        verbose_name = u'工作流额外参数表'
        verbose_name_plural = u'工作流额外参数表'


class FlowStepLog(models.Model):
    cf = models.ForeignKey(CommonFlow, on_delete=models.CASCADE)
    flow_step = models.ForeignKey(FlowStep, null=True, on_delete=models.SET_NULL)
    operator = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    is_passed = models.BooleanField()
    reply = models.TextField('操作人回复', default='')
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workflow_flow_step_log'
        verbose_name = u'工作流步骤记录表'
        verbose_name_plural = u'工作流步骤记录表'

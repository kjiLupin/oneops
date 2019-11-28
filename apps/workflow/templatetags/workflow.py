import datetime
from django import template
from workflow.models import Workflow, FlowStep, CommonFlow, FlowStepLog

register = template.Library()


@register.filter(name='flow_count')
def flow_count(user, status):
    count = 0
    if status == "pending":
        if user.is_superuser:
            count = CommonFlow.objects.filter(status=status).count()
        else:
            for cf in CommonFlow.objects.filter(status=status):
                fas = FlowStep.objects.get(workflow=cf.workflow, step=1)
                if cf.applicant == user or fas.group in user.groups.all():
                    count += 1
    elif status == "ongoing":
        if user.is_superuser:
            count = CommonFlow.objects.filter(status=status).count()
        else:
            for cf in CommonFlow.objects.filter(status=status):
                if cf.applicant == user:
                    count += 1
                else:
                    next_step = 1
                    if FlowStepLog.objects.filter(cf=cf).exists():
                        last_fas = FlowStepLog.objects.filter(cf=cf).order_by('-id')
                        next_step = last_fas[0].flow_step.step + 1
                    fas = FlowStep.objects.get(workflow=cf.workflow, step=next_step)
                    if fas.group in user.groups.all():
                        count += 1
    elif status == "end":
        if user.is_superuser:
            count = CommonFlow.objects.filter(status=status).count()
        else:
            count = CommonFlow.objects.filter(applicant=user, status=status).count()
    elif status == "end7":
        seven_days_ago = datetime.datetime.now() + datetime.timedelta(days=-7)
        if user.is_superuser:
            count = CommonFlow.objects.filter(status='end', update_time__gte=seven_days_ago).count()
        else:
            count = CommonFlow.objects.filter(applicant=user, status='end', update_time__gte=seven_days_ago).count()
    return count


@register.filter(name='chk_flow_perm')
def chk_flow_perm(user, code_step):
    if user.is_superuser:
        return True
    try:
        (flow_code, step) = code_step.split(":")
        wf = Workflow.objects.get(code=flow_code)
        fs = FlowStep.objects.get(workflow=wf, step=step)
        if fs.group and fs.group not in user.groups.all():
            return False
    except Exception as e:
        print(e)
        return False
    return True

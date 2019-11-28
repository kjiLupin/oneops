# -*- coding: utf-8 -*-
from django.views.generic import View
from common.mixins import JSONResponseMixin
from workflow.models import CommonFlow


class WorkflowInfoAPIView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            result = {
                "pending": CommonFlow.objects.filter(status='pending').count(),
                "ongoing": CommonFlow.objects.filter(applicant=request.user, status='ongoing').count(),
                "end": CommonFlow.objects.filter(applicant=request.user, status='end').count()
            }
            res = {'code': 0, 'result': result}
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)

# -*- coding: utf-8 -*-
import simplejson as json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from common.mixins import JSONResponseMixin

from job.models.job import JobConfig


class JobSettingsView(PermissionRequiredMixin, TemplateView):
    permission_required = 'auth.perm_job_settings'
    template_name = 'job/config.html'

    def get_context_data(self, **kwargs):
        context = {
            'path1': 'Job',
            'path2': '系统配置'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class JobConfigListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_job_settings'

    def get(self, request, **kwargs):
        all_config = JobConfig.objects.all().values('item', 'value')
        sys_config = {}
        for items in all_config:
            sys_config[items['item']] = items['value']
        return self.render_json_response(sys_config)

    def post(self, request):
        configs = request.POST.get('configs', None)
        try:
            if configs is None or len(json.loads(configs)) == 0:
                return self.render_json_response({'code': 1, 'errmsg': '提交内容为空！'})
            with transaction.atomic():
                JobConfig.objects.all().delete()
                JobConfig.objects.bulk_create(
                    [JobConfig(item=items['key'], value=items['value']) for items in json.loads(configs)])
        except Exception as e:
            return self.render_json_response({'code': 1, 'errmsg': str(e)})
        return self.render_json_response({'status': 0, 'result': '保存成功！'})

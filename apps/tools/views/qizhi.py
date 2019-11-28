
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class QiZhiCreateHostView(LoginRequiredMixin, TemplateView):
    template_name = "tools/qizhi_create_host.html"

    def get(self, request, **kwargs):
        context = {
            'path1': '小工具',
            'path2': '堡垒机录入'
        }
        context.update(**kwargs)
        return self.render_to_response(context)


from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class EncryptionView(LoginRequiredMixin, TemplateView):
    template_name = "tools/encryption.html"

    def get(self, request, **kwargs):
        context = {
            'path1': '小工具',
            'path2': '维密天使'
        }
        context.update(**kwargs)
        return self.render_to_response(context)

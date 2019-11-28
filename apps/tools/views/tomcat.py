
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from cmdb.models.asset import Server


class TomcatView(LoginRequiredMixin, TemplateView):
    template_name = "tools/tomcat.html"

    def get(self, request, **kwargs):
        test_host_list = Server.objects.filter(app_env='test').order_by('hostname')
        host_id = request.GET.get('select_id', 0)
        if host_id == 0:
            tomcat_list = list()
        else:
            tomcat_list = Server.objects.get(id=host_id).app.all()
        context = {
            'path1': '小工具',
            'path2': 'Tomcat',
            'test_host_list': test_host_list,
            'select_id': int(host_id),
            'tomcat_list': tomcat_list
        }
        context.update(**kwargs)
        return self.render_to_response(context)

# -*- coding: utf-8 -*-
from django.views.generic import TemplateView, View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.contrib.auth.decorators import permission_required
from django.db.models import Q, F
from django.contrib.auth.mixins import PermissionRequiredMixin
from common.mixins import JSONResponseMixin
from common.utils.magicbox_api import get_user_list_from_mb

from accounts.models import User


@permission_required('auth.perm_accounts_user_view', raise_exception=True)
def user(request):
    path1, path2 = "用户管理", "用户"
    return render(request, 'accounts/user.html', locals())


class UserListView(PermissionRequiredMixin, JSONResponseMixin, TemplateView):
    permission_required = 'auth.perm_accounts_user_view'

    def get(self, request, **kwargs):
        search = request.GET.get("search", None)
        if search is not None:
            obj_list = User.objects.filter(
                Q(username__contains=search) | Q(email__contains=search) | Q(display__contains=search))
        else:
            obj_list = User.objects.get_queryset()
        obj_list = obj_list.values("id", "username", "email", "is_active", "display", "is_superuser", "date_joined", "last_login")
        return self.render_json_response([o for o in obj_list])


@method_decorator(csrf_exempt, name='dispatch')
class OaUserListAPIView(JSONResponseMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            result = [{
                "k": p['email'],
                "v": "{}({},{})".format(p['name'], p['workNo'], p['email'])
            } for p in get_user_list_from_mb()]
            # result = [{
            #     "k": u.email,
            #     "v": "{}({},{})".format(u.display, u.username, u.email)
            # } for u in User.objects.all()]
            res = {'code': 0, 'result': result}
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)

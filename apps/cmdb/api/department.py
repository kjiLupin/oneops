# -*- coding: utf-8 -*-
import traceback
from django.http import QueryDict
from rest_framework.views import APIView
from rest_framework.versioning import URLPathVersioning
from common.mixins import JSONResponseMixin
from cmdb.models import BizMgtDept


class BizMgtDeptAPIView(JSONResponseMixin, APIView):
    versioning_class = URLPathVersioning

    def dispatch(self, request, *args, **kwargs):
        """
        请求到来之后，都要执行dispatch方法，dispatch方法根据请求方式不同触发 get/post/put等方法
        注意：APIView中的dispatch方法有好多好多的功能。
        """
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # 获取版本
        print(request.version)
        # 反向生成URL
        reverse_url = request.versioning_scheme.reverse('api-biz-dept', request=request)
        print(reverse_url)
        try:
            bgd_id = request.GET.get('id')
            o = BizMgtDept.objects.get(id=bgd_id)
            res = {"id": o.id, "dept_name": o.dept_name, "parent_id": o.parent_id, "comment": o.comment}
            return self.render_json_response({'code': 0, 'result': res})
        except BizMgtDept.DoesNotExist:
            return self.render_json_response({'code': 1, 'errmsg': '未找到该记录！'})

    def post(self, request, *args, **kwargs):
        parent_id = request.POST.get('parent_id')
        node_ids = request.POST.getlist('nodes[]', [])
        BizMgtDept.objects.filter(id__in=node_ids).update(parent_id=parent_id)
        res = {'code': 0, 'result': '操作成功！'}
        return self.render_json_response(res)

    def put(self, request, *args, **kwargs):
        try:
            ver = kwargs.get('version')
            bgd_id = request.GET.get('id')
            post_data = QueryDict(request.body).dict()
            print(ver, post_data)
            BizMgtDept.objects.filter(id=bgd_id).update(**post_data)
        except KeyError:
            print(traceback.print_exc())
            return self.render_json_response({'code': 1, 'errmsg': '未找到该记录！'})
        except BizMgtDept.DoesNotExist:
            return self.render_json_response({'code': 1, 'errmsg': '未找到该记录！'})
        return self.render_json_response({'code': 0, 'result': '操作成功！'})


# -*- coding: utf-8 -*-
import traceback
from django.http import QueryDict
from django.db.models import F
from rest_framework.views import APIView
from rest_framework.versioning import URLPathVersioning
from common.mixins import JSONResponseMixin
from dns_pod.models import Record, DnsLog


class RecordAPIView(JSONResponseMixin, APIView):
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
        # 获取版本管理的类
        print(request.versioning_scheme)

        # 反向生成URL
        reverse_url = request.versioning_scheme.reverse('api-record', request=request)
        print(reverse_url)
        env = kwargs.get('env')
        record_id = request.GET.get("id", None)
        if id is None:
            return self.render_json_response({'code': 1, 'errmsg': '请指定记录！'})
        obj_list = Record.objects.using('bind_{}'.format(env)).filter(id=record_id)
        obj_list = obj_list.values("zone", "host", "type", "data", "status", "ttl", "mx_priority", "view")
        res = {"total": len(obj_list), "rows": [o for o in obj_list]}
        return self.render_json_response({'code': 0, 'result': res})

    def post(self, request, *args, **kwargs):
        return self.render_json_response({'code': 1, 'errmsg': '未找到该记录！'})

    def put(self, request, *args, **kwargs):
        try:
            if not request.user.has_perm('auth.perm_dns_record_edit'):
                return self.render_json_response({'code': 1, 'errmsg': '权限不足，无法修改！'})
            ver, env = kwargs.get('version'), kwargs.get('env')
            post_data = QueryDict(request.body).dict()
            print(ver, post_data)
            record_id = post_data.pop('id')
            if "mx_priority" in post_data:
                if post_data['mx_priority']:
                    post_data['mx_priority'] = int(post_data['mx_priority'])
                else:
                    post_data.pop('mx_priority')
            # 保存，并记录修改日志
            old_record_info = Record.objects.using('bind_{}'.format(env)).get(id=record_id).__str__()

            Record.objects.using('bind_{}'.format(env)).filter(id=record_id).update(**post_data)
            Record.objects.using('bind_{}'.format(env)).filter(id=record_id).update(serial=F('serial') + 1)

            new_record_info = Record.objects.using('bind_{}'.format(env)).get(id=record_id).__str__()
            DnsLog.objects.create(user=request.user, action='edit', old_record=old_record_info,
                                  new_record=new_record_info)

        except KeyError:
            print(traceback.print_exc())
            return self.render_json_response({'code': 1, 'errmsg': '未找到该记录！'})
        except Record.DoesNotExist:
            return self.render_json_response({'code': 1, 'errmsg': '未找到该记录！'})
        return self.render_json_response({'code': 0, 'result': '操作成功！'})

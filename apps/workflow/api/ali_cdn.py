# -*- coding: utf-8 -*-
import traceback
from django.views.generic import View
from common.mixins import JSONResponseMixin
from ssh.utils.executor import Executor

static_file_host = '172.20.1.48'


class SyncCSFileAPIView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            src_path = request.GET.get('src_path', '')
            src_env = request.GET.get('src_env', '')
            if not src_path or not src_env:
                return self.render_json_response({'code': 1, 'errmsg': '请输入文件名或目录名！'})
            executor = Executor(static_file_host, 22, "root")
            if executor.host_user is None:
                return self.render_json_response({'code': 1, 'errmsg': '%s 获取系统登陆用户失败！' % static_file_host})
            status, output = executor.get_connect()
            if status is False:
                return self.render_json_response({'code': 1, 'errmsg': output})
            ret = list()
            for src in src_path.split('\r\n'):
                cmd = 'ansible {0} -m copy -a "src=/data/pic/{1} dest=/usr/share/nginx/static/{1}"'.format(src_env, src)
                ret.append(executor.exec_command(cmd))
            res = {'code': 0, 'result': "<br/>".join(ret)}
        except Exception as e:
            traceback.print_exc()
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)

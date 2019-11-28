import os
import subprocess
from django.views.generic import View
from django.http import HttpResponse


class EncryptionAPIView(View):

    def get(self, request, *args, **kwargs):
        try:
            password = request.GET.get('password', None)
            env = request.GET.get('env', None)
            if password and env:
                base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
                exe_file_dir = os.path.join(base_dir, 'scripts')
                if env == "dev":
                    output = subprocess.getoutput("cd {};java dbpasswordhelper -e {}".format(exe_file_dir, password))
                    res = "dev公司环境 明文为：{} {}".format(password, output.strip().split('\n')[1])
                elif env == "wdai":
                    output = subprocess.getoutput("cd {};java dbpasswordhelper -e {} -k".format(exe_file_dir, password))
                    res = "wdai下沙环境 明文为：{} {}".format(password, output.strip().split('\n')[1])
                else:
                    res = '非法调用！'
            else:
                res = '非法调用！'
        except Exception as e:
            res = str(e)
        return HttpResponse(res)

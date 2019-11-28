
import datetime
import traceback
import simplejson as json
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View, TemplateView
from common.utils.config import SysConfig
from common.utils.ding_api import get_ding_user_id
from common.utils.base import cfg
from common.utils.cryptor import cryptor
from common.utils.http_api import HttpRequests
from accounts.models import User


login_failure_counter = {}  # 登录失败锁定计数器，给login_authenticate用。


@csrf_exempt
def login_authenticate(username, password):
    """登录认证，包含一个登录失败计数器，5分钟内连续失败5次的账号，会被锁定5分钟"""
    sys_config = SysConfig().sys_config
    if sys_config.get('lock_cnt_threshold'):
        lock_cnt_threshold = int(sys_config.get('lock_cnt_threshold'))
    else:
        lock_cnt_threshold = 5
    if sys_config.get('lock_time_threshold'):
        lock_time_threshold = int(sys_config.get('lock_time_threshold'))
    else:
        lock_time_threshold = 300

    # 服务端二次验证参数
    if username == "" or password == "" or username is None or password is None:
        result = {'status': 2, 'errmsg': '用户名或密码为空，请重新输入!'}
    elif username in login_failure_counter and login_failure_counter[username]["cnt"] >= lock_cnt_threshold and (
            datetime.datetime.now() - login_failure_counter[username]["last_failure_time"]).seconds \
            <= lock_time_threshold:
        result = {'status': 3, 'errmsg': '登录失败超过5次，该账号已被锁定5分钟!'}
    else:
        if username == 'admin':
            # 调用 django 认证系统
            user = authenticate(username=username, password=password)
        else:
            # 调用 Bim 统一身份认证系统
            # {"token":{"tokenId":"......"},"roles":[],"attributes":[{"values":["WD44134"],"name":"uid"}]}
            # {"exception":{"message":"密码无效","name":"com.bamboocloud.bam.idsvcs.InvalidPassword"}}
            # {"exception":{"message":"验证失败","name":"com.bamboocloud.bam.idsvcs.InvalidCredentials"}}
            url = 'http://bam.yadoom.com:8080/bam/identity/json/authenticateapi'
            data = {
                'uid': username,
                'usercredential': password,
                'app_id': 'oa',
                'app_key': 'password',
                'attributenames': 'uid',
                'uri': 'realm=/',
                'module': 'LDAP'
            }
            _, ret = HttpRequests().post(url, data)
            ret = json.loads(ret)
            print(ret)
            if 'exception' not in ret:
                # 认证成功
                url = 'http://bam.yadoom.com:8080/bam/identity/json/attributesapi'
                data = {
                    'tokenid': ret['token']['tokenId'],
                    'app_id': 'oa',
                    'app_key': 'password'
                }
                _, ret = HttpRequests().post(url, data)
                ret = json.loads(ret)
                display = ''
                if 'exception' not in ret:
                    for item in ret['attributes']:
                        if item['name'] == 'sn':
                            display = item['values'][0]
                if not User.objects.filter(username=username).exists():
                    user = User()
                    user.username = username
                    user.display = display
                    user.password = make_password(password)
                    user.password2 = cryptor.encrypt(password)
                    user.save()

                    try:
                        # 添加到默认组，默认组设置最小权限
                        group = Group.objects.get(id=1)
                        user.groups.add(group)
                    except Exception:
                        print('无id=1的权限组，无法默认添加')
                else:
                    user = User.objects.get(username=username)
                    if user.password != make_password(password):
                        user.password = make_password(password)
                        user.password2 = cryptor.encrypt(password)
                        user.save(update_fields=['password'])
                    if display and user.display != display:
                        user.display = display
                        user.save(update_fields=['display'])
                user = User.objects.get(username=username)
            else:
                user = None
        if user:
            # 登录成功
            # 获取该用户的钉钉 userid，用于给他发钉钉消息
            if sys_config.get("ding_to_person") == 'true' and username != 'admin':
                get_ding_user_id(username)

            # 如果登录失败计数器中存在该用户名，则清除之
            if username in login_failure_counter:
                login_failure_counter.pop(username)

            result = {'status': 0, 'result': 'Successful'}
        else:
            # 登录失败
            if username not in login_failure_counter:
                # 第一次登录失败，登录失败计数器中不存在该用户，则创建一个该用户的计数器
                login_failure_counter[username] = {"cnt": 1, "last_failure_time": datetime.datetime.now()}
            else:
                if (datetime.datetime.now() - login_failure_counter[username]["last_failure_time"]).seconds <= lock_time_threshold:
                    login_failure_counter[username]["cnt"] += 1
                else:
                    # 上一次登录失败时间早于5分钟前，则重新计数。以达到超过5分钟自动解锁的目的。
                    login_failure_counter[username]["cnt"] = 1
                login_failure_counter[username]["last_failure_time"] = datetime.datetime.now()
            result = {'status': 1, 'errmsg': '用户名或密码错误，请重新输入！'}
    return result


class LoginView(TemplateView):
    template_name = "login.html"

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")
        result = login_authenticate(username, password)
        if result['status'] == 0:
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
            else:
                user = User()

            # 开启LDAP的认证通过后更新用户密码
            if settings.ENABLE_LDAP:
                if user.password != make_password(password):
                    user.password = make_password(password)
            user.password2 = cryptor.encrypt(password)
            user.save()
            try:
                # 添加到默认组，默认组设置最小权限
                user = User.objects.get(username=username)
                group = Group.objects.get(id=1)
                user.groups.add(group)
            except Exception:
                print('无id=1的权限组，无法默认添加')

            # 调用了django内置登录方法，防止管理后台二次登录
            login(request, user)
        else:
            pass
        return JsonResponse(result)


class OAuthRedirectView(View):
    oauth_api = cfg.get('oauth', 'oauth_api')
    client_id = cfg.get('oauth', 'client_id')
    redirect_uri = cfg.get('oauth', 'redirect_uri')

    def get(self, request, *args, **kwargs):
        next_url = '{0}/authorize?client_id={1}&scope=read_user+openid+api&redirect_uri={2}&response_type=code'.format(
            self.oauth_api, self.client_id, self.redirect_uri)
        return HttpResponseRedirect(next_url)


class OAuthAuthView(View):
    oauth_api = cfg.get('oauth', 'oauth_api')
    client_id = cfg.get('oauth', 'client_id')
    client_secret = cfg.get('oauth', 'client_secret')
    redirect_uri = cfg.get('oauth', 'redirect_uri')

    def get(self, request, *args, **kwargs):
        sso_code = request.GET.get('code')
        url = '{0}/accessToken?client_id={1}&client_secret={2}&redirect_uri={3}&code={4}&grant_type=authorization_code'.format(
            self.oauth_api, self.client_id, self.client_secret, self.redirect_uri, sso_code
        )
        _, token = HttpRequests().get(url)
        try:
            access_token = json.loads(token)['access_token']
            _, user = HttpRequests().get('%s/profile?access_token=%s' % (self.oauth_api, access_token))
            user_info = json.loads(user)
            user_id = user_info['id']
            user_job_number = user_info['empid']
            user_email = user_info['email']
            user_name = user_info['name']
            user_display = user_info['username']

            import random
            password = "".join(random.sample('abcdefghijklmnopqrstuvwxyzAbcDfGijKnMnopqrStuvvxYZ0123456789', 8))

            if not User.objects.filter(username=user_job_number).exists():
                user = User()
                user.username = user_job_number
                user.password = make_password(password)
                user.password2 = cryptor.encrypt(password)
                user.display = user_display
                user.email = user_email
                user.save()

                try:
                    # 添加到默认组，默认组设置最小权限
                    group = Group.objects.get(id=1)
                    user.groups.add(group)
                except Exception:
                    print('无id=1的权限组，无法默认添加')
            user = User.objects.get(username=user_job_number)
            # 调用django内置登录方法，防止管理后台二次登录
            login(request, user)
            next_url = request.GET.get("next") if request.GET.get("next", None) else reverse("accounts:profile")
            return HttpResponseRedirect(next_url)

        except:
            print(traceback.print_exc())
        return render(request, 'login.html')


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponseRedirect(reverse("accounts:login"))


class Profile(LoginRequiredMixin, TemplateView):
    template_name = "accounts/user_profile.html"

    def get_context_data(self, **kwargs):
        context = {
            'path1': '用户管理',
            'path2': '个人中心',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

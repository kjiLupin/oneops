
import smtplib
import traceback
import simplejson as json
from django.shortcuts import render
from django.http import JsonResponse
from django.db import transaction
from common.models import Config
from common.utils.email_api import MailSender
from common.utils.config import SysConfig


def settings(request):
    if request.method == "GET":
        context = {
            'path1': '全局设置',
            'path2': '编辑',
            'config': SysConfig().sys_config
        }
        return render(request, 'common/settings.html', context)
    else:
        if not request.user.has_perm('auth.perm_common_settings_edit'):
            return JsonResponse({'code': 1, 'errmsg': '权限不足，无法修改！'})
        configs = request.POST.get('configs', None)
        try:
            if configs is None or len(json.loads(configs)) == 0:
                return JsonResponse({'code': 1, 'errmsg': '提交内容为空！'})
            with transaction.atomic():
                Config.objects.all().delete()
                Config.objects.bulk_create(
                    [Config(item=items['key'], value=items['value']) for items in json.loads(configs)])
        except Exception as e:
            return JsonResponse({'code': 1, 'errmsg': str(e)})
        return JsonResponse({'code': 0, 'result': '保存成功！'})


def email_check(request):
    mail_sender = MailSender()
    try:
        if mail_sender.MAIL_SSL:
            server = smtplib.SMTP_SSL(mail_sender.MAIL_REVIEW_SMTP_SERVER,
                                      mail_sender.MAIL_REVIEW_SMTP_PORT)  # SMTP协议默认SSL端口是465
        else:
            server = smtplib.SMTP(mail_sender.MAIL_REVIEW_SMTP_SERVER,
                                  mail_sender.MAIL_REVIEW_SMTP_PORT)  # SMTP协议默认端口是25
        # 如果提供的密码为空，则不需要登录SMTP server
        if mail_sender.MAIL_REVIEW_FROM_PASSWORD != '':
            server.login(mail_sender.MAIL_REVIEW_FROM_ADDR, mail_sender.MAIL_REVIEW_FROM_PASSWORD)
        result = {'status': 0, 'msg': '连接成功！'}
    except Exception as e:
        print(traceback.format_exc())
        result = {'status': 1, 'msg': '邮件服务配置不正确,\n{}'.format(str(e))}
    # 返回结果
    return JsonResponse(result)

# -*- coding: UTF-8 -*-
import os
import datetime
import hashlib
import configparser
import threading
from common.utils.config import sys_config
from common.utils.email_api import MailSender
from common.utils.ding_api import DingSender

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

cfg = configparser.ConfigParser()
cfg.read(os.path.join(BASE_DIR, 'wdoneops.conf'))
ROOT_URL = cfg.get('base', 'root_url')

FILE_UPLOAD_TMP_DIR = os.path.join(BASE_DIR, 'logs/upload/')
FILE_DOWNLOAD_TMP_DIR = os.path.join(BASE_DIR, 'logs/download/')

admin_mail = sys_config.get('admin_mail')


def get_random_string(length=32):
    s = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    return hashlib.md5(s.encode(encoding='UTF-8')).hexdigest()[:length]


def dict_list_duplicate_delete(li):
    _list = list(set([str(i) for i in li]))
    return [eval(i) for i in _list]


def get_ip_by_request(request):
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        return request.META['HTTP_X_FORWARDED_FOR'].split(',')[0]
    else:
        return request.META['REMOTE_ADDR'].split(',')[0]


def make_directory(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


def async_deco(func):
    def wrapper(*args, **kwargs):
        thr = threading.Thread(target=func, args=args, kwargs=kwargs)
        thr.start()
    return wrapper


def send_msg_to_admin(content, mail_to=admin_mail):
    if sys_config.get('ding_to_group') == 'true':
        web_hook_url = sys_config.get('ding_web_hook')
        DingSender().ding_to_group(web_hook_url, content)
    elif sys_config.get('mail') == 'true':
        MailSender().send_email('运维告警邮件-OneOPS系统', content, mail_to.split(','))
    else:
        print(content)

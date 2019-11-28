#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import json
import redis
import traceback
from common.utils.http_api import HttpRequests
from common.utils.config import SysConfig
from common.models import Config
from accounts.models import User

http_request = HttpRequests()


def get_access_token():
    sys_conf = SysConfig().sys_config
    token = sys_conf.get('ding_access_token', '')
    expire_time = sys_conf.get('ding_expires_time', 0)
    now_time = int(time.time())
    if expire_time and (int(expire_time) - now_time) > 60:
        # 还没到超时时间
        return token
    else:
        # token 已过期
        corp_id = sys_conf.get('ding_corp_id')
        corp_secret = sys_conf.get('ding_corp_secret')
        url = "https://oapi.dingtalk.com/gettoken?corpid={0}&corpsecret={1}".format(corp_id, corp_secret)
        status, ret = http_request.get(url)
        if status is True:
            # 钉钉推荐加锁更新token，这里暂时未实现
            # from django.db import transaction
            s = json.loads(ret)

            updated_values = {"item": "ding_access_token", "value": s["access_token"]}
            Config.objects.update_or_create(item="ding_access_token", defaults=updated_values)

            updated_values = {"item": "ding_expires_time", "value": str(int(now_time + s["expires_in"]))}
            Config.objects.update_or_create(item="ding_expires_time", defaults=updated_values)

            return s["access_token"]
        else:
            print(ret)
            return


def get_ding_user_id(username):
    try:
        rs = redis.StrictRedis(host="127.0.0.1", port=6379, db=1)
        ding_user_id = rs.execute_command('GET {}'.format(username.upper()))
        if ding_user_id is not None:
            user = User.objects.get(username=username)
            if user.ding_user_id != str(ding_user_id, encoding="utf8"):
                user.ding_user_id = str(ding_user_id, encoding="utf8")
                user.save(update_fields=['ding_user_id'])
    except Exception as e:
        traceback.print_exc()


class DingSender(object):
    def __init__(self):
        self.headers = {'Content-Type': 'application/json'}
        self.request = HttpRequests()
        self.app_id = SysConfig().sys_config.get('ding_agent_id', None)

    def ding_to_person(self, ding_user_id, content):
        if self.app_id is None:
            return "No app id."
        data = {
            "touser": ding_user_id,
            "agentid": self.app_id,
            "msgtype": "text",
            "text": {
                "content": "{}".format(content)
            },
        }
        url = 'https://oapi.dingtalk.com/message/send?access_token=' + get_access_token()
        # print(url, data)
        status, ret = self.request.post(url, data, self.headers)
        return status, ret

    def ding_to_group(self, url, content):
        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": "{}".format(content)
                },
            }
            status, ret = self.request.post(url, json.dumps(data), self.headers)
            print('ding_to_group', status, ret)
            return status, ret
        except Exception as e:
            print(traceback.format_exc())
            return False, str(e)

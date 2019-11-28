#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 定时同步员工的钉钉ID 到本地redis

import os
import sys
import json
import time
import traceback
import requests
import redis
import django

base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(base_dir)
os.environ['DJANGO_SETTINGS_MODULE'] = 'wdoneops.settings'
django.setup()

from common.utils.config import sys_config
from common.utils.base import send_msg_to_admin

rs = redis.StrictRedis(host="127.0.0.1", port=6379, db=1)


def get_access_token(corp_id, corp_secret):
    now_time = int(time.time())
    expire_time = rs.execute_command('TTL token')
    if expire_time and (int(expire_time) - now_time) > 60:
        # 还没到超时时间
        return rs.execute_command('GET token').decode()
    else:
        # token 已过期
        url = "https://oapi.dingtalk.com/gettoken?corpid={0}&corpsecret={1}".format(corp_id, corp_secret)
        resp = requests.get(url, timeout=3)

        ret = str(resp.content, encoding="utf8")
        s = json.loads(ret)
        rs.execute_command('SETEX token {} {}'.format(s["expires_in"], s["access_token"]))
        return s["access_token"]


class Ding(object):
    def __init__(self):
        self.corp_id = sys_config.get('ding_corp_id')
        self.corp_secret = sys_config.get('ding_corp_secret')
        self.root_dept_id = sys_config.get('ding_root_dept_id')
        self.key = sys_config.get('ding_oneops_username')
        self.token = get_access_token(self.corp_id, self.corp_secret)

    def get_dept_list_id_fetch_child(self, parent_dept_id):
        ids = [int(parent_dept_id)]
        url = 'https://oapi.dingtalk.com/department/list_ids?id={0}&access_token={1}'.format(parent_dept_id, self.token)
        resp = requests.get(url, timeout=3)
        ret = str(resp.content, encoding="utf8")
        s = json.loads(ret)
        if s["errcode"] == 0:
            for dept_id in s["sub_dept_id_list"]:
                ids.extend(self.get_dept_list_id_fetch_child(dept_id))
        return ids

    def sync_ding_user_id(self):
        """
        本公司使用工号（username）登陆oneops，并且工号对应钉钉系统中字段 "jobnumber"。
        所以可根据钉钉中 jobnumber 查到该用户的 ding_user_id。
        """
        try:
            for dept_id in self.root_dept_id.split(','):
                dept_id_list = self.get_dept_list_id_fetch_child(dept_id)
                for di in dept_id_list:
                    url = 'https://oapi.dingtalk.com/user/list?access_token={0}&department_id={1}'.format(self.token, di)
                    try:
                        resp = requests.get(url, timeout=3)
                        ret = str(resp.content, encoding="utf8")
                        # print('user_list_by_dept_id:', ret)
                        s = json.loads(ret)
                        if s["errcode"] == 0:
                            for u in s["userlist"]:
                                try:
                                    cmd = """SETEX {} 86400 {}""".format(u[self.key], u["userid"])
                                    rs.execute_command(cmd)
                                except:
                                    send_msg_to_admin(traceback.print_exc())
                        else:
                            print(ret)
                    except:
                        send_msg_to_admin(traceback.print_exc())
                    time.sleep(1)
        except Exception:
            send_msg_to_admin(traceback.print_exc())

if __name__ == "__main__":
    Ding().sync_ding_user_id()

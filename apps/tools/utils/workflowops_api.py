#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import traceback
from common.utils.http_api import HttpRequests

http_request = HttpRequests()
workflowops_host_api = "http://workflowops.yadoom.com/api"


def get_workflowops_token(username, password):
    data = {'username': username,  'password': password}
    url = "http://workflowops.yadoom.com/api/api-token-auth/"
    status, ret = http_request.post(url, data)
    if status is True:
        s = json.loads(ret)
        # updated_values = {"item": "workflowops_token", "value": s["token"]}
        # Config.objects.update_or_create(item="workflowops_token", defaults=updated_values)
        return s["token"]
    else:
        print(ret)
        raise Exception("调用WorkflowOps系统失败，请联系管理员！")


def get_online_surfing_user(username, password):
    try:
        token = get_workflowops_token(username, password)
        headers = {'Authorization': 'JWT ' + token}
        url = "http://workflowops.yadoom.com/api/science-surfing/online-user/?username={}".format(username)
        status, ret = http_request.get(url, headers)
        if status is True:
            s = json.loads(ret)
            if s["count"] > 0:
                return s['results'][0]
            else:
                return
        else:
            print(ret)
            return
    except Exception as e:
        traceback.print_exc()
        return


def net_surfing_apply(username, password, ip):
    token = get_workflowops_token(username, password)
    headers = {'Authorization': 'JWT ' + token}
    url = "http://workflowops.yadoom.com/api/science-surfing/apply/"
    status, ret = http_request.post(url, {'ip': ip}, headers)
    if status is True:
        return json.loads(ret)
    else:
        print(ret)
        return


def get_surfing_logs(username, password, page, page_size):
    try:
        token = get_workflowops_token(username, password)
        headers = {'Authorization': 'JWT ' + token}
        url = "http://workflowops.yadoom.com/api/science-surfing/logs/?username={}&page={}&page_size={}".\
            format(username, page, page_size)
        status, ret = http_request.get(url, headers)
        if status is True:
            return json.loads(ret)
        else:
            print(ret)
            return
    except Exception as e:
        traceback.print_exc()
        return

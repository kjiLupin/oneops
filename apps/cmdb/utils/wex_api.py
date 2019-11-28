#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from common.utils.http_api import HttpRequests
from common.utils.base import send_msg_to_admin

http_request = HttpRequests()


def application_update(data):
    url = "http://wex.yadoom.com/api/wex/api/application/update"
    # data = {
    #     "app_code": data["app_code"],
    #     "app_name": data["app_name"],
    #     "app_type": data["app_type"],
    #     "tomcat_port": data["tomcat_port"],
    #     "scm_url": data["scm_url"],
    #     "importance": data["importance"],
    #     "domain_name": data["domain_name"],
    #     "primary": data["primary"],
    #     "secondary": data["secondary"],
    #     "comment": data["comment"]
    # }
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    status, ret = http_request.post(url=url, params=json.dumps(data), headers=headers)
    if status is False:
        send_msg_to_admin("wex更新应用接口调用出错：\n" + ret)
    print(ret)

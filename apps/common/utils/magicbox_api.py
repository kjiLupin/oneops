#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
from common.utils.http_api import HttpRequests


user_list_url = "http://magicbox.nw.yadoom.com/user/getResearchCenterSimpleUser"
email_url = "http://magicbox.nw.yadoom.com/user/getUserByEmail?email="
work_no_url = "http://magicbox.nw.yadoom.com/user/getUserByWorkNo?workNo="

external_user = [
    {'name': '金少凌', 'email': 'JinShaoLing_1056745@yadoom.com', 'workNo': 1056745},
    {'name': '潘云鹏', 'email': 'PanYunPeng_1056746@yadoom.com', 'workNo': 1056746},
    {'name': '刘天宇', 'email': 'LiuTianYu_1056744@yadoom.com', 'workNo': 1056744},
    {'name': '白鹏成', 'email': 'BaiPengCheng_1056743@yadoom.com', 'workNo': 1056743}
]


def get_user_list_from_mb():
    http_request = HttpRequests()
    status, ret = http_request.get(user_list_url)
    if status is True:
        s = json.loads(ret)
        if s["code"] == 0:
            res = external_user
            for p in s["data"]:
                if "name" in p and "email" in p and "workNo" in p:
                    res.append({
                        "name": p["name"],
                        "email": p["email"],
                        "workNo": p["workNo"]
                    })
            return res
        else:
            print(ret)
            return list()
    else:
        print(ret)
        return list()


def get_user_detail_from_mb(no_or_email):
    external_user_email = [u['email'] for u in external_user]
    external_user_workno = [u['workNo'] for u in external_user]
    if no_or_email in external_user_email or no_or_email in external_user_workno:
        return {}
    if re.match(r'^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,4}$', no_or_email, re.I):
        url = email_url + no_or_email
    else:
        url = work_no_url + no_or_email
    http_request = HttpRequests()
    status, ret = http_request.get(url)
    if status is True:
        s = json.loads(ret)
        if s["code"] == 0:
            return {
                "name": s["data"]["name"],
                "user_id": s["data"]["userId"],
                "ding_user_id": s["data"]["dingDingId"],
                "avatar": s["data"]["avatar"],
                "email": s["data"]["email"],
                "work_no": s["data"]["workNo"],
                "dept_id": s["data"]["deptId"],
                "phone": s["data"]["phone"]
            }
        else:
            return None
    else:
        print(ret)
        return None

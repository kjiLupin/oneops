#!/usr/bin/env python
# coding:utf-8
# 定时检查堡垒机中的用户，是否已经离职。若已离职，则禁用 堡垒机及oneops 账户。
# pip install suds or pip3 install suds-py3
import re
import os
import sys
import requests
import suds.client
import django
import logging

base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(base_dir)
os.environ['DJANGO_SETTINGS_MODULE'] = 'wdoneops.settings'
django.setup()

from accounts.models import User, RetiredEmployeeRecord
from common.utils.base import send_msg_to_admin

logging.getLogger('suds.client').setLevel(logging.DEBUG)

blj_query = 'https://172.20.1.163:8081/api/identity/query/'
blj_update = 'https://172.20.1.163:8081/api/identity/update/bylogin/{}/'
headers = {
    'identity': '1',
    'token': 'xxxxx',
}

ret = requests.get(blj_query, headers=headers, verify=False)
bb = ret.json()

for i in range(len(bb['data'])):
    work_no = str(bb['data'][i]['login'])
    # WD开头账号，活跃状态账号
    if re.match(r'10\d\d\d\d\d', work_no) and bb['data'][i]['status'] == 1:
        # print(bb['data'][i]['id'], bb['data'][i]['name'], bb['data'][i]['status'], bb['data'][i]['login'])
        try:
            c = suds.client.Client("http://192.168.21.54:8080/bim-server/api/webservice/ExtApiIngtAuthService?WSDL")
            token = c.service.login('OA', 'password', False, None)
            c = suds.client.Client("http://192.168.21.54:8080/bim-server/api/webservice/ExtApiIngtTargetAccountService?WSDL")
            ret = c.service.getByUsername(token, work_no)
            fullname, department_id, is_disabled = '', None, False
            for item in dict(ret)['entry']:
                if item["key"] == "organizationId":
                    department_id = item["value"]
                if item["key"] == "isDisabled":
                    is_disabled = item["value"]
                if item["key"] == "fullname":
                    fullname = item["value"]

            cont = list()
            if is_disabled is True:
                # 员工已离职，统一身份系统返回状态为"禁用"，此处也禁用堡垒机账户
                r = requests.post(blj_update.format(work_no), data={'status': 0}, headers=headers, verify=False)
                print("disable ", work_no, r.text)
                User.objects.filter(username=work_no).update(is_active=False)
                cont.append('{}({}) 已离职，已禁用其堡垒机账户。'.format(work_no, fullname))
                RetiredEmployeeRecord.objects.create(
                    work_no=work_no, display=fullname, comment=cont
                )
                send_msg_to_admin('\n'.join(cont), "yuanxuekun@yadoom.com,yukai_44134@yadoom.com")
            elif department_id is not None:
                if User.objects.filter(username=work_no).exists():
                    user = User.objects.get(username=work_no)
                    if user.ding_dept_id:
                        if user.ding_dept_id != department_id:
                            # 用户更换了部门，发告警信息给管理员
                            cont.append('{}({}) 更换了部门，请询问是否还需要使用堡垒机！'.format(work_no, user.display))

                            # RetiredEmployeeRecord.objects.create(
                            #     work_no=work_no, display=fullname, comment=cont
                            # )
                            # send_msg_to_admin('\n'.join(cont), "yuanxuekun@yadoom.com,yukai_44134@yadoom.com")

                    # 更新oneops 员工部门id
                    user.ding_dept_id = department_id
                    user.save(update_fields=['ding_dept_id'])

        except suds.WebFault as ex:
            print(ex.fault, ex.document)
            send_msg_to_admin(str(ex.fault) + "\n" + str(ex.document))

# 同步某个时间点之后更新的记录，searchFilterMap 对象构造不成功
# https://docs.inductiveautomation.com/display/DOC79/SUDS+-+Library+Overview
# c = suds.client.Client("http://192.168.21.53:8080/bim-server/api/webservice/ExtApiIngtTargetAccountService?WSDL")
# sa = c.factory.create('SerachAble')

# # cacheable, converted, page, searchFilterMap, sort
# # searchFilterMap key='' value={}
# search_obj = {
# False, False, None,
# [("",{"updateAt": "2019-03-15 20:17:15.000"},False,"gte",{"updateAt": "2019-03-10 20:17:15.000"})],
# None
# }
# ret = c.service.findBy(token, "isDisabled", search_obj)

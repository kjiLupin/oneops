# -*- coding: utf-8 -*-
# 阿里云python SDK开发CDN刷新页面
# pip install aliyun-python-sdk-cdn
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkcdn.request.v20180510.RefreshObjectCachesRequest import RefreshObjectCachesRequest


class AliCDNManager(object):

    def __init__(self, cdn):
        self.access_id = cdn.account
        self.access_secret = cdn.secret
        self.end_point = cdn.end_point
        self.client = AcsClient(self.access_id, self.access_secret, self.end_point)

    def flush(self, obj_uri, obj_type):
        request = RefreshObjectCachesRequest()
        request.set_accept_format('json')

        # 其值可以为File或Directory
        # print(11111, obj_uri, obj_type)
        request.set_ObjectType(obj_type)
        request.set_ObjectPath(obj_uri.strip())

        response = self.client.do_action_with_exception(request)
        return str(response, encoding='utf-8')

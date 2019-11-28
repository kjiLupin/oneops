#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests


blj_url = 'https://172.20.1.163:8081'
headers = {'identity': '1', 'token': 'xxxxx'}
default_pass = 'xxxxx'


def create_user(post_data):
    # post_data['login'] = login
    # post_data['name'] = name
    # post_data['email'] = email
    # post_data['passwd1'] = passwd1
    # post_data['status'] = '1'
    # post_data['auth_method'] = '5'
    # post_data['passwd'] = '0'
    # post_data['domain'] = groupid
    url = blj_url + '/api/identity/create/'
    r = requests.post(url, data=post_data, headers=headers, verify=False)
    return r.json()


def add_groups(groups, users):
    post_data = {
        'op': '1',
        'sets': users
    }
    url = '{}/api/identity_zone/update/{}/'.format(blj_url, groups)
    r = requests.post(url, data=post_data, headers=headers, verify=False)
    return r.json()


def query_id(user):
    post_data = {'login': user}
    url = blj_url + '/api/identity/query/'
    r = requests.get(url, params=post_data, headers=headers, verify=False)
    return '[%s]' % r.json()['data'][0]['id']


def create_host(group_ids, hostname, ip):
    url = blj_url + '/api/server/create/'
    post_data = {
        "name": hostname,
        "ipaddr": ip,
        "domain": "1",
        "systype": "General Linux",
        "server_zone_list": "[1,%s]" % ','.join(group_ids)
    }
    r = requests.post(url, data=post_data, headers=headers, verify=False)
    result = r.json()
    if result['code'] == 2000:
        host_id = result['data']
        url = '%s/api/server/password/update/%d/' % (blj_url, host_id)
        post_data = {
            "sets": '[[3,"{0}"],[9,"{0}"]]'.format(default_pass),
            "op": 1
        }
        r = requests.post(url, data=post_data, headers=headers, verify=False)
        result = r.json()
        if result['code'] == 2000:
            return '创建成功 %s' % result['msg']
        else:
            return '设置登陆用户异常 %s' % result['msg']
    else:
        return '创建异常 %s' % result['msg']

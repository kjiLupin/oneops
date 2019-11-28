#!/usr/bin/env python
# -*- coding: utf-8 -*-
# https://www.zabbix.com/documentation/3.4/zh/manual/api
# https://www.iyunv.com/thread-665618-1-1.html

import json
import requests

zabbix_user, zabbix_password = "yukai", "redhat"
zabbix_url = "http://zabbix.yadoom.com/zabbix/api_jsonrpc.php"


def get_access_token():
    data = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "user": zabbix_user,
            "password": zabbix_password
        },
        "id": 1,
        "auth": None
    }
    headers = {'Content-Type': 'application/json-rpc'}
    resp = requests.post(url=zabbix_url, json=data, headers=headers)
    print(resp.status_code, resp.content)
    if resp.status_code == 200:
        return json.loads(resp.content)["result"]
    return


def get_host_ids(token, ip_list):
    data = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid"],
            "filter": {
                "ip": ip_list
            }
        },
        "auth": token,
        "id": 2
    }
    headers = {'Content-Type': 'application/json-rpc'}
    resp = requests.post(url=zabbix_url, json=data, headers=headers)
    print(resp.status_code, resp.content)
    if resp.status_code == 200:
        s = json.loads(resp.content)
        # [{'hostid': '11103'}, {'hostid': '10639'}]
        return [r["hostid"] for r in s["result"]]
    return list()


def get_monitor_item_ids(token, host_id_list, key_list):
    # https://www.zabbix.com/documentation/3.4/zh/manual/api/reference/item/get
    # ['system.cpu.util[,user,avg1]', 'vm.memory.size[pavailable]']
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_id_list,
            "filter": {
                "key_": key_list
            },
            "sortfield": "name"
        },
        "auth": token,
        "id": 3
    }
    headers = {'Content-Type': 'application/json-rpc'}
    resp = requests.post(url=zabbix_url, json=data, headers=headers)
    print(resp.status_code, resp.content)
    if resp.status_code == 200:
        s = json.loads(resp.content)
        ret = dict()
        for r in s["result"]:
            if r["hostid"] in ret:
                ret[r["hostid"]].append(r["itemid"])
            else:
                ret[r["hostid"]] = [r["itemid"]]
        return ret
    return dict()


def update_monitor_item(token, item_ids, status):
    for _, item_id in item_ids.items():
        data = {
            "jsonrpc": "2.0",
            "method": "item.update",
            "params": {
                "itemid": item_id[0],
                "status": status
            },
            "auth": token,
            "id": 6
        }
        headers = {'Content-Type': 'application/json-rpc'}
        resp = requests.post(url=zabbix_url, json=data, headers=headers)
        print(resp.status_code, resp.content)


def get_history_data(token, item_id_list, value_type=3, time_start=None, time_end=None):
    """
    https://www.zabbix.com/documentation/3.4/zh/manual/api/reference/history/get
    
    history:
        Possible values:可能的值
        0 - numeric float;数字浮点数
        1 - character;字符
        2 - log; 日志
        3 - numeric unsigned; 数字符号
        4 - text.文本
    :param token: 
    :param item_id_list: 
    :param value_type: 
    :param time_start: 
    :param time_end: 
    :return: 
    """
    if time_start and time_end:
        data = {
            "jsonrpc": "2.0",
            "method": "history.get",
            "params": {
                "output": "extend",
                "history": value_type,
                "itemids": item_id_list,
                "sortfield": "clock",
                "sortorder": "DESC",
                "time_from": time_start,
                "time_till": time_end
            },
            "auth": token,
            "id": 4
        }
    else:
        # 获取最后一个值
        data = {
            "jsonrpc": "2.0",
            "method": "history.get",
            "params": {
                "output": "extend",
                "history": value_type,
                "itemids": item_id_list,
                "sortfield": "clock",
                "sortorder": "DESC",
                "limit": 1
            },
            "auth": token,
            "id": 4
        }
    headers = {'Content-Type': 'application/json-rpc'}
    resp = requests.post(url=zabbix_url, json=data, headers=headers)
    # print(resp.status_code, resp.content)
    if resp.status_code == 200:
        s = json.loads(resp.content)
        # '{"jsonrpc":"2.0","result":[{"itemid":"78248","clock":"1560505088","value":"1","ns":"159446572"},
        # {"itemid":"78248","clock":"1560505028","value":"1","ns":"865098001"},
        # {"itemid":"78248","clock":"1560504968","value":"1","ns":"318736807"}],"id":1}'
        return s["result"]
    return

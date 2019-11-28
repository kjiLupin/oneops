#!/usr/bin/python2
# coding:utf-8


import json
import time
import datetime
import re
import sys
import requests
# from dingdingsend import dingdingsend

CMDB_HOST, CMDB_PORT = '172.20.1.47', 5001
OPENSTACK_HOST = '172.21.85.10'
res = {"jsonrpc": "2.0", "id": 1}
headers = {"Content-Type": "application/json"}


def send(data):
    url = "http://%s:%s/api" % (CMDB_HOST, CMDB_PORT)
    r = requests.post(url, headers=headers, json=data)
    print(r.status_code, r.content)


def get_token_project_id():
    url = 'http://{0}:35357/v3/auth/tokens?nocatalog'.format(OPENSTACK_HOST)
    data = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "domain": {
                            "name": "default"
                        },
                        "name": "admin",
                        "password": "xxxxx"
                    }
                }
            },
            "scope": {
                "project": {
                    "domain": {
                        "name": "default"
                    },
                    "name": "admin"
                }
            }
        }
    }
    r = requests.post(url, headers=headers, json=data)
    # print r.status_code, r.content
    resp_header = r.headers
    x_subject_token = resp_header["X-Subject-Token"]
    resp = json.loads(r.content)
    return x_subject_token, resp["token"]["project"]["id"]


def get_openstack_info():
    res["method"] = "server.radd"
    host_info = dict()
    token, project_id = get_token_project_id()
    print('token: ', token)

    # url = 'http://{0}:8774/v2.1/flavors'.format(OPENSTACK_HOST)
    # r = requests.get(url, headers={"X-Auth-Token": token})
    # flavors_info = json.loads(r.content)
    # # print '22222: ', flavors_info
    # for flavors in flavors_info["flavors"]:
    #     id = flavors["id"]
    #     print id
    #
    url = 'http://{0}:8774/v2.1/os-hypervisors/detail'.format(OPENSTACK_HOST)
    r = requests.get(url, headers={"X-Auth-Token": token})
    # print r.content
    resp_dict = json.loads(r.content)
    for hypervisors in resp_dict["hypervisors"]:
        host_info["hostname"] = hypervisors["service"]["host"]
        host_info["cpu_used"] = hypervisors["vcpus_used"]
        host_info["mem_used"] = hypervisors["memory_mb_used"]
        host_info["vm_num"] = hypervisors["running_vms"]
        res['params'] = host_info
        send(res)

    #
    vm_info = dict()
    url = 'http://{0}:8774/v2.1/{1}/servers/detail'.format(OPENSTACK_HOST, project_id)
    r = requests.get(url, headers={"X-Auth-Token": token})
    server_info = json.loads(r.content)
    for server in server_info["servers"]:
        vm_info["parent_host_name"] = server["OS-EXT-SRV-ATTR:host"]
        vm_info["uuid"] = server["id"]
        vm_info["status"] = "running" if server["status"] == 'ACTIVE' else "down"
        res['params'] = vm_info
        send(res)


if __name__ == "__main__":
    get_openstack_info()

#!/usr/bin/python2
# coding:utf-8


import json
import subprocess
import commands
import socket
import time
import re
import os
import platform
import urllib
import urllib2
import httplib

CMDB_HOST, CMDB_PORT = '172.20.1.47', 5001
res = {"jsonrpc": "2.0", "id": 1}


def get_hostname():
    return socket.gethostname()


def get_cpu_info2():
    ret = {"cpu": '', 'num': 0}
    cpu_cmd = "cat /proc/cpuinfo |awk '/model name/' |awk -F':' 'END{print FNR, $2}'"
    status, output = commands.getstatusoutput(cpu_cmd)
    if status == 0:
        ret['num'] = output.split()[0]
        ret['cpu'] = ' '.join(output.split()[1:])
    return ret


def get_cpu_info():
    ret = 0
    cpu_cmd = "cat /proc/cpuinfo |awk '/model name/' |awk -F':' 'END{print FNR}'"
    status, output = commands.getstatusoutput(cpu_cmd)
    if status == 0:
        ret = output
    return ret


def get_disk():
    partition_size = list()
    disk_cmd = "LANG=C fdisk -l 2>/dev/null |grep -E '^Disk' |grep -v 'mapper' | awk '/bytes/{print $5}'"
    output = commands.getoutput(disk_cmd)
    for dev_size in output.split("\n"):
        if dev_size.isdigit():
            partition_size.append(str(int(dev_size)/1024/1024/1024))
    if not partition_size:
        disk_cmd = "LANG=C parted -l 2>/dev/null |grep -E '^Disk' |grep -v 'mapper' | awk '{print +$NF}'"
        output = commands.getoutput(disk_cmd)
        for dev_size in output.split("\n"):
            if dev_size.isdigit():
                partition_size.append(dev_size)
    return " + ".join(partition_size)


def get_manufacturer():
    cmd = "/usr/sbin/dmidecode -t 1"
    ret = {}
    manufacturer_data = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in manufacturer_data.stdout.readlines():
        if "Manufacturer" in line:
            ret['manufacturer'] = line.split(': ')[1].strip()
        elif "Product Name" in line:
            ret['product_name'] = line.split(': ')[1].strip()
        elif "Serial Number" in line:
            ret['sn'] = line.split(': ')[1].strip().replace(' ', '')
        elif "UUID" in line:
            ret['uuid'] = line.split(': ')[1].strip()
    return ret
    # return manufacturer_data.stdout.readline().split(': ')[1].strip()


def get_kvm_info(host_uuid):
    cmd = "virsh list --all --uuid 2>/dev/null |grep -v '^$'"
    vm_num, ret = 0, dict()
    res = {"jsonrpc": "2.0", "id": 1, "method": "server.radd"}
    kvm_data = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in kvm_data.stdout.readlines():
        vm_num += 1
        res.update({
            'params': {"uuid": line.strip(), "parent_host": host_uuid}
        })
        send2(res)
    ret["vm_num"] = vm_num
    return ret


# 出厂日期
def get_rel_date():
    cmd = """/usr/sbin/dmidecode -t 0 |grep -i release"""
    data = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    date = data.stdout.readline().split(': ')[1].strip()
    return re.sub(r'(\d+)/(\d+)/(\d+)', r'\3-\1-\2', date)


def get_os_version():
    return " ".join(platform.linux_distribution())


def get_nic_mac_ip():
    """
    data = {
        ["mac1"]:[
            {"eth0": [ip1, ip2]},
            {"eth0.1": [ip3]}
            ],
        ["mac2"]:...,
    }
    :return: data
    """
    data = {}
    nic_cmd = "ifconfig |awk '!/^ /{print $1}'|grep -E '^eth|^en|^em|^bond|^br' |sed 's/://g'"
    status, output = commands.getstatusoutput(nic_cmd)
    if status == 0:
        for nic in output.split("\n"):
            mac_cmd = "ip link show {0} |awk '/ether/{{print $2}}'".format(nic)
            mac = commands.getoutput(mac_cmd)

            ip_cmd = "ip a s {0} |awk -F'/| *' '/inet /{{print $3}}' |grep -E '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+'".format(nic)
            ips = commands.getoutput(ip_cmd)
            if re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', ips):
                data[mac] = [{nic: ips.split("\n")}]
    return data


def get_memory():
    with open('/proc/meminfo') as mem_open:
        a = int(mem_open.readline().split()[1])
        return a / 1024


def get_tomcat_deploy_info():
    if os.path.exists('/data/'):
        tomcat_ports = list()
        dirs = os.listdir('/data/')
        for dir in dirs:
            port = dir.split("-")[0]
            if re.match(r'^[89]\d\d\d', port):
                tomcat_ports.append(port)

        listen_ports = list()
        status, output = commands.getstatusoutput("ss -lnt |awk '{print $4}'")
        for line in output.split("\n"):
            port = line.split(":")[-1]
            if re.match(r'^[89]\d\d\d', port):
                listen_ports.append(port)
        # 返回交集，即/data目录下有项目代码，并且正监听提供服务的端口
        return list(set(tomcat_ports).intersection(set(listen_ports)))
    else:
        return list()


def run():
    data = dict()
    data['hostname'] = get_hostname()
    data['nic_mac_ip'] = get_nic_mac_ip()
    # data['server_cpu'] = "{cpu} {num}".format(**cpu_info)
    data['server_cpu'] = get_cpu_info()
    data['server_disk'] = get_disk()
    data['server_mem'] = get_memory()
    data.update(get_manufacturer())
    data['release_date'] = get_rel_date()
    data['os'] = get_os_version()
    if "VMware" in data['manufacturer'] or re.match(r'OpenStack|KVM', data['product_name'], re.I):
        data['is_vm'] = 1
    else:
        data['is_vm'] = 0
    data.update(get_kvm_info(data["uuid"]))
    data['tomcat_ports'] = get_tomcat_deploy_info()
    data["status"] = "running"
    res['params'] = data
    res["method"] = "server.radd"
    # print(res)
    send2(res)


# def send(data):
#     import requests
#     headers = {"Content-Type": "application/json"}
#     url = "http://%s:%s/api" % (CMDB_HOST, CMDB_PORT)
#     r = requests.post(url, headers=headers, json=data)
#     print(r.status_code)
#     print(r.content)


def send2(data):
    jdata = json.dumps(data)
    url = "http://%s:%s/api" % (CMDB_HOST, CMDB_PORT)
    req = urllib2.Request(url, jdata)
    req.add_header('Content-Type', 'application/json')
    resp = urllib2.urlopen(req)
    print(resp.read())


if __name__ == "__main__":
    run()

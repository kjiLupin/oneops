#!/usr/bin/python2
# coding:utf-8
# pip install psutil, pyroute2
# yum install python-dmidecode
# https://psutil.readthedocs.io/en/latest/
# https://github.com/huanghao/dmidecode
# https://github.com/kontron/python-ipmi

import traceback
import subprocess
import socket
import re
import os
import json
import platform
import urllib2
import psutil
import sys
from pprint import pprint
from datetime import datetime
reload(sys)
sys.setdefaultencoding("utf-8")


def get_os_version():
    return platform.platform()


def get_hostname():
    return socket.gethostname()


def get_cpu_count():
    return psutil.cpu_count()


def get_cpu_used():
    return '%.1f' % psutil.cpu_percent(interval=3, percpu=False)


def get_memory():
    return psutil.virtual_memory().total


def get_memory_used():
    return '%.1f' % psutil.virtual_memory().percent


def get_disk():
    ret = list()
    for mnt in psutil.disk_partitions(all=False):
        if mnt.fstype == "":
            continue
        disk_used = psutil.disk_usage(mnt.mountpoint)
        ret.append("%s：%d/%.1f%%" % (mnt.mountpoint, disk_used.total, disk_used.percent))
    return ret


def get_manufacturer(os_version):
    if re.search(r'Windows', os_version, re.I):
        cmd = 'wmic computersystem get "Model"'
        ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        product_name = ret.stdout.read().split("\n")[1].strip()
        cmd = 'wmic baseboard get "Manufacturer"'
        ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        manufacturer = ret.stdout.read().split("\n")[1].strip()
        cmd = 'wmic bios get "ReleaseDate"'
        ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        release_date = ret.stdout.read().split("\n")[1].strip()[:8]

        cmd = 'wmic csproduct get "UUID"'
        ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        uuid = ret.stdout.read().split("\n")[1].strip()
        cmd = 'wmic csproduct get "IdentifyingNumber"'
        ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        sn = ret.stdout.read().split("\n")[1].strip()
        return {
            'manufacturer': manufacturer,
            'product_name': product_name,
            'sn': sn,
            'uuid': uuid,
            'release_date': release_date
        }
    else:
        # import dmidecode
        # sys_info = dmidecode.system()
        # bios_info = dmidecode.bios()
        # return {
        #     'manufacturer': sys_info['0x0001']['data']['Manufacturer'],
        #     'product_name': sys_info['0x0001']['data']['Product Name'],
        #     'sn': sys_info['0x0001']['data']['Serial Number'],
        #     'uuid': sys_info['0x0001']['data']['UUID'],
        #     'release_date': bios_info['0x0000']['data']['Relase Date']
        # }
        cmd = "sudo /usr/sbin/dmidecode -t 0,1 |grep -iE 'Release|Manufacturer|Product|Serial\s+Number|UUID'"
        ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        dmi = ret.stdout.read()
        pprint(dmi)
        return {
            'manufacturer': re.findall(r'Manufacturer:\s+(.*)', dmi, re.I)[0],
            'product_name': re.findall(r'Product Name:\s+(.*)', dmi, re.I)[0],
            'sn': re.findall(r'Serial\s+Number:\s+(.*)', dmi, re.I)[0],
            'uuid': re.findall(r'UUID:\s+(.*)', dmi, re.I)[0],
            'release_date': re.findall(r'Release Date:\s+(.*)', dmi, re.I)[0]
        }


def get_nic_mac_ip(os_version):

    """
    data = {
        ["mac1"]:[
            {"eth0": [ip1, ip2]},
            {"eth0:0": [ip3]}
            {"eth0.1": [ip4]}
            ],
        ["mac2"]:...,
    }
    :return: data
    """
    nic_data, nic_mac, alias_nic = dict(), dict(), list()

    for nic_name, snic_addr_list in psutil.net_if_addrs().items():
        # print(nic_name, snic_addr_list)
        ip_list, mac = list(), ""
        if re.search(r'Windows', os_version, re.I):
            nic_name = nic_name.decode('GBK')
            for item in snic_addr_list:
                if item.family == 2 and item.address != "127.0.0.1":
                    ip_list.append(item.address)
                    # item.netmask
                if item.family == -1 and item.address != "00:00:00:00:00:00":
                    mac = item.address
            if mac == "00-00-00-00-00-00-00-E0" and not ip_list:
                continue
        else:
            if not re.match('en|eth|em|br|bond|tun|team', nic_name, re.I):
                continue
            for item in snic_addr_list:
                # snicaddr(family=2, address='172.20.1.47', netmask='255.255.255.0', broadcast='172.20.1.255', ptp=None)
                if item.family == 2 and item.address != "127.0.0.1":
                    ip_list.append(item.address)
                    # item.netmask
                if item.family == 17 and item.address != "00:00:00:00:00:00":
                    mac = item.address
            if ":" in nic_name and mac == "":
                alias_nic.append([nic_name, ip_list])
                continue
        nic_mac[nic_name] = mac
        if mac not in nic_data:
            nic_data[mac] = [{nic_name: ip_list}]
        else:
            nic_data[mac].append({nic_name: ip_list})

    if not re.search(r'Windows', os_version, re.I):
        # 获取其他 net namespace 的网卡
        from pyroute2 import netns, NetNS, IPDB
        for ns in netns.listnetns():
            ip_db = IPDB(nl=NetNS(ns))
            for nic_name, snic_addr in ip_db.interfaces.items():
                if nic_name in [1, 10, "lo"]:
                    continue
                mac = snic_addr['address']
                ip_list = list()
                for i in snic_addr['ipaddr']:
                    # (('10.0.0.1', 24), )
                    ip_list.append(i[0])
                if mac not in nic_data:
                    nic_data[mac] = [{nic_name: ip_list}]
                else:
                    nic_data[mac].append({nic_name: ip_list})
    for nic in alias_nic:
        # ['eth0:0', ['x.x.x.x']]
        root_nic_name = nic[0].split(":")[0]
        nic_data[nic_mac[root_nic_name]].append({nic[0]: nic[1]})
    return nic_data


def get_kvm_info(uuid):
    cmd = "sudo virsh list --all --uuid 2>/dev/null |grep -v '^$'"
    vm_count = 0
    ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in ret.stdout.readlines():
        vm_count += 1
        send({"vm_uuid": line.strip(), "uuid": uuid})
    return {"vm_count": vm_count}


def get_process():
    url = "http://oneops.yadoom.com/cmdb/v1/process/"
    f = urllib2.urlopen(url)
    if f.getcode() == 200:
        resp = json.loads(f.read())
        if resp["code"] == 0:
            for r in resp["result"]:
                print(r["name"], r["version_arg"])

    java_processes = [p.cmdline() for p in psutil.process_iter(attrs=['pid', 'name']) if 'java' in p.info['name']]
    print(java_processes)


def get_tomcat_info():
    if os.path.exists('/data/'):
        tomcat_dir = list()
        for d in os.listdir('/data/'):
            if re.match(r'^[89]\d\d\d-\S+$', d):
                cmd = """LANG=C sudo ps aux|grep -v grep|grep '%s'|grep -w java|awk '{print $11,"-version"}'|bash""" % d
                ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                output = ret.stdout.readline().strip()
                jdk = output.split()[-1].strip('"') if re.search('"\d+\.\d+\.\d+', output) else ""

                cmd = "LANG=C sudo ps aux|grep -w '%s'|grep -iEo 'xms\w+|xmx\w+' |tr '\\n' ' '" % d
                ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                jvm = ret.stdout.readline()

                tomcat_port, app_code = d[:d.index('-')], d[d.index('-') + 1:]
                tomcat_dir.append([tomcat_port, app_code, jdk, jvm])
        return tomcat_dir
        # listen_ports = list()
        # status, output = commands.getstatusoutput("ss -lnt |awk '{print $4}'")
        # for line in output.split("\n"):
        #     port = line.split(":")[-1]
        #     if re.match(r'^[89]\d\d\d', port):
        #         listen_ports.append(int(port))
        # # 返回交集，即/data目录下有项目代码，并且正监听提供服务的端口
        # return list(set(tomcat_dir).intersection(set(listen_ports)))
    else:
        return list()


def get_manage_address():
    cmd = "sudo ipmitool lan print |grep '^IP Address *: *.*' |awk '{print $NF}'"
    ret = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = ret.stdout.readline().strip()
    return output


def send(post_data):
    try:
        pprint(post_data)
        url = "http://oneops.yadoom.com/cmdb/v1/cmdb_agent/"
        # url = "http://192.168.21.241:8888/cmdb/v1/cmdb_agent/"
        req = urllib2.Request(url, json.dumps(post_data))
        req.add_header("Content-Type", "application/json")
        resp = urllib2.urlopen(req)
        print(resp.read())
    except urllib2.HTTPError as e:
        print(e)

if __name__ == "__main__":
    data = dict()
    data['os'] = get_os_version()
    data['hostname'] = get_hostname()
    data['cpu_total'] = get_cpu_count()
    data['cpu_used'] = get_cpu_used()
    data['disk'] = get_disk()
    data['mem_total'] = get_memory()
    data['mem_used'] = get_memory_used()
    data.update(get_manufacturer(data['os']))
    data['nic_mac_ip'] = get_nic_mac_ip(data['os'])

    if not re.search('Windows', data['os'], re.I):
        data.update(get_kvm_info(data["uuid"]))
        data['tomcat'] = get_tomcat_info()
        if not re.search(r'OpenStack|KVM|Virtual', data['product_name'], re.I):
            data["manage_address"] = get_manage_address()
    data["status"] = "running"
    data["date_last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    send(data)

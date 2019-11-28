#!/usr/bin/python2
# coding:utf-8


import json
import subprocess
import commands
import socket
import time
import datetime
import re
import platform
import urllib
import httplib
import pysphere
import ssl
import sys
import pprint
from pysphere import VIServer, MORTypes, VIProperty
from pysphere.resources import VimService_services as VI

# from dingdingsend import dingdingsend

CMDB_HOST, CMDB_PORT = '172.20.1.47', 5001
res = {"jsonrpc": "2.0", "id": 1, "method": "server.radd"}
ssl._create_default_https_context = ssl._create_unverified_context


def send(data):
    import requests
    headers = {"Content-Type": "application/json"}
    url = "http://%s:%s/api" % (CMDB_HOST, CMDB_PORT)
    r = requests.post(url, headers=headers, json=data)
    print(r.status_code, r.content)


def get_host_vm_info(vcsa_host):
    user = "administrator@yadoom.com"
    passwd = "xxxxx"

    server = VIServer()
    server.connect(vcsa_host, user, passwd)
    print('\033[32mVC connect successful...\033[0m')

    host_info = dict()
    for esx_hostname, esx_ip in server.get_hosts().items():
        print(esx_hostname, esx_ip)

        props = server._retrieve_properties_traversal(property_names=[
            'name',
            'summary.overallStatus',
            'summary.quickStats.overallMemoryUsage',
            'summary.quickStats.overallCpuUsage',
            'summary.hardware.memorySize',
            'summary.hardware.numCpuCores',
            'summary.hardware.numCpuThreads',
            'summary.hardware.cpuMhz',
            'summary.hardware.otherIdentifyingInfo',
            'hardware.biosInfo',
            'summary.hardware',
            'datastore'
        ], from_node=esx_hostname, obj_type="HostSystem")
        try:
            for prop_set in props:
                # mor = prop_set.Obj #in case you need it
                for prop in prop_set.PropSet:
                    if prop.Name == "summary.quickStats.overallMemoryUsage":
                        used_mem = prop.Val
                    elif prop.Name == "summary.quickStats.overallCpuUsage":
                        host_used_cpu = prop.Val
                    elif prop.Name == "summary.hardware.otherIdentifyingInfo":
                        identification_info_list = prop.Val.__dict__['_HostSystemIdentificationInfo']
                        host_sn = identification_info_list[-1].__dict__['_identifierValue']
                    elif prop.Name == "summary.hardware.memorySize":
                        host_info["server_mem"] = prop.Val
                    elif prop.Name == "summary.hardware.numCpuThreads":
                        host_cpu_num = prop.Val
                    elif prop.Name == "summary.hardware.numCpuCores":
                        host_cpucores_num = prop.Val
                    elif prop.Name == "summary.hardware.cpuMhz":
                        mhz_per_core = prop.Val
                    elif prop.Name == "summary.overallStatus":
                        host_status = prop.Val
                        if host_status == "green":
                            host_info["status"] = "running"
                        elif host_status == "gray":
                            host_info["status"] = "down"
                        elif host_status == "yellow":
                            host_info["status"] = "running"
                        elif host_status == "red":
                            host_info["status"] = "error"
                    elif prop.Name == "hardware.biosInfo":
                        time_tuple = prop.Val.__dict__['_releaseDate']
                        host_info["release_date"] = time.strftime("%Y-%m-%d", time_tuple)
                    # print HostBiosInfo
                    elif prop.Name == "datastore":
                        datastore_list = prop.Val.__dict__['_ManagedObjectReference']
                        server_disk = dict()
                        disk_all_free = dict()
                        Datastore_All = 0
                        Datastore_Free = 0
                        for index, ds in enumerate(datastore_list):
                            DatastoreCapacity = 0
                            DatastoreFreespace = 0
                            DatastoreUsagePercent = 0
                            props_d = server._retrieve_properties_traversal(
                                property_names=['name', 'summary.capacity', 'summary.freeSpace'], from_node=ds,
                                obj_type="Datastore")
                            for prop_set_d in props_d:
                                for prop_d in prop_set_d.PropSet:
                                    if prop_d.Name == "summary.capacity":
                                        DatastoreCapacity = (prop_d.Val / 1024 / 1024 / 1024)
                                    elif prop_d.Name == "summary.freeSpace":
                                        DatastoreFreespace = (prop_d.Val / 1024 / 1024 / 1024)
                            DatastorePreUsagePercent = (
                            ((DatastoreCapacity - DatastoreFreespace) * 100) / DatastoreCapacity)
                            disk_all_free[ds] = [DatastoreCapacity, DatastoreFreespace, DatastorePreUsagePercent]
                            Datastore_All = Datastore_All + DatastoreCapacity
                            Datastore_Free = Datastore_Free + DatastoreFreespace
                        DatastoreUsagePercent = (((Datastore_All - Datastore_Free) * 100) / Datastore_All)
                        server_disk["total"] = Datastore_All
                        server_disk["free"] = Datastore_Free
                        server_disk["used_pct"] = DatastoreUsagePercent
                        server_disk["detail"] = disk_all_free
                        # print server_disk
                    elif prop.Name == "summary.hardware":
                        # print 'hardware----:', prop.Val.__dict__
                        hardware = prop.Val.__dict__
                        host_info["product_name"] = hardware['_model']
                        host_info["uuid"] = hardware['_uuid']
                        host_info["manufacturer"] = hardware['_vendor']
        except Exception as e:
            # print(prop.Val.__dict__)
            print(e)
            continue
            host_info["vmware_disk"] = server_disk
        host_info["used_cpu"] = (host_used_cpu * 100) / (host_cpucores_num * mhz_per_core)
        host_info["server_cpu"] = host_cpu_num
        host_info["used_mem"] = '%.1f' % ((used_mem * 1024 * 1024 * 100) / host_info["server_mem"])
        host_info["is_vm"] = 0
        host_info['sn'] = host_sn
        host_info["os"] = "VMware ESX"
        host_info["hostname"] = esx_hostname
        host_info["nic_mac_ip"] = {esx_hostname: [{esx_hostname: [esx_ip]}]}
        host_info["check_update_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # host_running_num = len(server.get_registered_vms(esx_hostname, status='poweredOn'))
        # host_stop_num = len(server.get_registered_vms(esx_hostname, status='poweredOff'))
        host_info["vm_num"] = len(server.get_registered_vms(esx_hostname))
        res['params'] = host_info
        print(esx_ip, host_info)
        send(res)

    # vm host
    vms_info = dict()
    properties = [
        'summary.vm',
        'summary.config.numEthernetCards',
        'summary.config.annotation',
        'summary.config.numVirtualDisks',
        'summary.quickStats.overallCpuUsage',
        'summary.quickStats.guestMemoryUsage',
        'summary.quickStats.ftLogBandwidth',
        'summary.quickStats.hostMemoryUsage',
        'summary.quickStats.uptimeSeconds',
        'summary.runtime.powerState',
        'summary.runtime.bootTime',
        'summary.runtime.host',
        'summary.runtime.maxCpuUsage',
        'summary.runtime.maxMemoryUsage',
        'summary.storage.committed',
        'summary.storage.uncommitted',
        'summary.storage.unshared',
        'summary.storage.timestamp',
        'guestHeartbeatStatus',
        'guest.toolsStatus',
        'guest.toolsVersionStatus',
        'guest.toolsVersion',
        'guest.guestId',
        'guest.guestFullName',
        'guest.guestState',
        'guest.ipAddress',
        'guest.hostName',
        'name',
        'parent',
        'config.template',
        'config.hardware.numCPU',
        'config.hardware.memoryMB',
        'config.uuid'
    ]

    # 通过_retrieve_properties_traversal方法传入API接口定义拿到对象类型为 VirtualMachine 的信息
    props = server._retrieve_properties_traversal(property_names=properties, obj_type='VirtualMachine')
    server.disconnect()

    # 通过server.get_hosts()拿到VC下面所有的host信息（字典）；
    # 通过这个方法可以把'guest.hostName'取出的MOR对象转换成实际的hostname
    # hostname = server.get_hosts().items()

    for prop in props:
        mor = prop.Obj
        vm = {}
        for p in prop.PropSet:
            vm[p.Name] = p.Val
        vms_info[mor] = vm

    vms_dict = vms_info.values()
    vm_info = {}
    for i in range(len(vms_dict)):
        vm = vms_dict[i]
        """
        {'config.hardware.numCPU': 2, 'guest.guestId': 'centos64Guest', 'guest.guestFullName': 'CentOS 4/5 or later (64-bit)', 
        'summary.quickStats.hostMemoryUsage': 3846, 'summary.storage.committed': 68898546142, 'guest.hostName': 'JF-PROD-zk02', 
        'summary.quickStats.uptimeSeconds': 63854590, 'summary.runtime.maxMemoryUsage': 4096, 
        'config.uuid': '564d162d-99ee-19a4-9b2d-6721d5e6f9f1', 'guest.ipAddress': '172.20.1.27', 
        'config.template': False, 'guest.toolsVersionStatus': 'guestToolsCurrent', 'summary.quickStats.ftLogBandwidth': -1, 
        'summary.config.numEthernetCards': 1, 'summary.storage.uncommitted': 1002, 'config.hardware.memoryMB': 4096, 
        'summary.runtime.host': 'host-396', 'summary.config.annotation': '', 'parent': 'group-v372', 
        'summary.quickStats.overallCpuUsage': 66, 'summary.runtime.powerState': 'poweredOn', 'summary.runtime.maxCpuUsage': 4400, 
        'guest.toolsVersion': '9536', 'guest.guestState': 'running', 'guestHeartbeatStatus': 'green', 'name': 'JF-PROD-zk02', 
        'summary.storage.timestamp': (2018, 11, 30, 15, 25, 30, 654, 0, 0), 'summary.storage.unshared': 64424509440, 
        'summary.config.numVirtualDisks': 2, 'summary.quickStats.guestMemoryUsage': 327, 
        'summary.runtime.bootTime': (2016, 9, 18, 23, 20, 56, 724, 0, 0), 'guest.toolsStatus': 'toolsOk', 'summary.vm': 'vm-401'}
        """
        # vm_info["hostname"] = vm["name"]
        vm_info["parent_host"] = vm["summary.runtime.host"]
        vm_info["uuid"] = vm["config.uuid"]
        vm_info["status"] = vm["guest.guestState"]
        print(vm_info)
        res['params'] = vm_info
        send(res)


if __name__ == "__main__":
    vcsa_list = ['vcsa.yadoom.com']
    for host in vcsa_list:
        get_host_vm_info(host)

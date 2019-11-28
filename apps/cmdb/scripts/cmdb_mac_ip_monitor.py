#!/usr/bin/env python
# -*- coding: utf-8 -*-
from scapy.all import srp, Ether, ARP, conf
import socket
import fcntl
import struct
import urllib
import urllib2
import httplib
import requests
import json


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,
        struct.pack('256s', ifname[:15])
    )[20:24])


def get_hw_addr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', ifname[:15]))
    return ':'.join(['%02x' % ord(char) for char in info[18:24]])


def ip_mac(ipscan):
    dic_ip_mac = {}
    try:
        ans, unans = srp(Ether(dst="FF:FF:FF:FF:FF:FF") / ARP(pdst=ipscan), timeout=3, retry=3, verbose=False)
    except Exception as e:
        print(e)
    else:
        for snd, rcv in ans:
            mac = rcv.sprintf("%Ether.src%")
            ip = rcv.sprintf("%ARP.psrc%")
            dic_ip_mac[ip] = mac
        dic_ip_mac[l_ip] = l_mac
        return dic_ip_mac


def send(data):
    url = "http://%s:%s/cmdb/v1/ip_check/" % (CMDB_HOST, CMDB_PORT)
    headers = {'Content-Type': 'application/json'}
    resp = requests.post(url, headers=headers, json=data)
    print(resp.status_code, resp.content)


CMDB_HOST = '172.20.1.47'
CMDB_PORT = '5001'
send_data1 = {}
send_data2 = {}
l_ip = get_ip_address('eth0')
l_mac = get_hw_addr('eth0')
ipscan = "%s.1/24" % '.'.join(get_ip_address('eth0').split('.')[0:3])
dic_ip_mac = ip_mac(ipscan)
send(dic_ip_mac)
# send_data1['ipmac']=ip_mac_l[0]
# send_data2['ipmac']=ip_mac_l[1]
# send(send_data1)
# send(send_data2)

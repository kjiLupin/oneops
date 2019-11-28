#!/usr/bin/python
# coding:utf-8


import json
import commands
import re
import os
import urllib
import httplib
import traceback
import requests
import socket
import sys
from IPy import IP
reload(sys)
sys.setdefaultencoding("utf-8")

CMDB_HOST = '172.20.1.47'
base_dir = os.path.abspath(os.path.dirname(__file__))

exclude_segment = ['101.71.14.16/28', '112.13.101.224/29', '115.236.20.128/29', '122.224.169.16/29',
                   '122.225.192.56/29', '124.160.116.240/29', '183.129.132.224/29', '183.129.134.8/29',
                   '183.129.150.16/28', '183.129.155.176/29', '223.95.75.167',
                   '172.20.8.0/24', '172.20.200.0/24', '172.25.1.0/24', '172.21.244.0/24', '172.25.128.0/22']
# 排除呼叫中心ip
exclude_ip = ["172.20.100." + str(i) for i in range(140, 152)]

local_ip_file = os.path.join(base_dir, "total_ip.list")
local_segment_file = os.path.join(base_dir, "total_segment.list")


def send_mail(contents, mail_to, sub=u'运维告警邮件'):
    try:
        contents = contents.replace('\n', '<br>')
        my_dict = {'to': ','.join(mail_to), 'subject': sub, 'contents': contents}
        http_conn = httplib.HTTPConnection(CMDB_HOST, 80)
        uri_ = '/mailsender.php?%s' % urllib.urlencode(my_dict)
        http_conn.request('POST', uri_)
        res = http_conn.getresponse()
        http_res = res.read()
        if res.status != 200:
            print("No2 邮件发送失败：%s" % http_res)
        else:
            print("Send success: ", http_res)
    except Exception:
        print("No1 邮件发送失败：%s" % str(traceback.print_exc()))


def get_list_from_file(file_name):
    if not os.path.exists(file_name):
        return []
    with open(file_name, "r") as f1:
        return f1.readlines()


def write_content_to_file(cont_list, file_name):
    with open(file_name, "w") as f1:
        for line_cont in cont_list:
            f1.write(line_cont + "\n")


def get_segment_ip_list(env):
    _segment_list, _ip_list = list(), list()
    resp = requests.get("http://oneops.yadoom.com/cmdb/v1/ip/")
    if int(resp.status_code) == 200:
        ret = json.loads(resp.content)
        if int(ret["code"]) == 0:
            for _idc in ret["result"]:
                for _vlan in _idc["vlan_list"]:
                    for _segment in _vlan["segment_list"]:
                        seg = IP("{0}/{1}".format(_segment["segment"], _segment["netmask"]), make_net=True).strNormal()
                        if seg not in exclude_segment:
                            if env == "prod" and re.match(r'^192\.168\.|^172\.20\.100\.|^172\.30\.4\.|^172\.25\.', seg):
                                continue
                            elif env == "test" and not re.match(r'^172\.20\.100\.|^172\.30\.4\.|^172\.25\.', seg):
                                continue
                            elif env == "dev" and not re.match(r'^192\.168\.', seg):
                                continue
                            else:
                                _segment_list.append(seg)
                                for _ip in _segment["ip_list"]:
                                    if _ip not in exclude_ip:
                                        _ip_list.append(_ip)
                        else:
                            continue
            # 将本次查出的内容，写入本地文件缓存
            print("将本次查出的内容，写入本地文件缓存:", _segment_list)
            write_content_to_file(_segment_list, local_segment_file)
            write_content_to_file(_ip_list, local_ip_file)
            return _segment_list, _ip_list
        else:
            # 查询失败，读取本地文件
            print("查询失败，读取本地文件")
    else:
        # HTTP 请求失败，读取本地文件
        print("HTTP 请求失败，读取本地文件", resp.content)

    _segment_list.extend(get_list_from_file(local_segment_file))
    _ip_list.append(get_list_from_file(local_ip_file))
    return _segment_list, _ip_list


def get_ssh_session(ip, user, password):
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=22, username=user, password=password, timeout=30)
        transport = ssh.get_transport()
        transport.set_keepalive(30)
        transport.use_compression(True)
        return ssh, ''
    except Exception as e:
        return None, str(e)


def get_sftp_session(ip, user, password):
    try:
        import paramiko
        transport = paramiko.Transport((ip, 22))
        transport.connect(username=user, password=password)
        transport.set_keepalive(30)
        transport.use_compression(True)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp
    except Exception as e:
        print(ip, user, e)
        return None, str(e)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Using: python %s [prod|test|dev]" % sys.argv[0])
        sys.exit()
    elif sys.argv[1] not in ["prod", "test", "dev"]:
        print("Using: python %s [prod|test|dev]" % sys.argv[0])
        sys.exit()
    not_in_cmdb, ip_is_down = list(), list()
    segment_list, ip_list = get_segment_ip_list(sys.argv[1])
    for segment in segment_list:
        try:
            print(segment)
            fping_cmd = "%s/fping -g %s -c 3  -p 200 -i 10 -q >/dev/null 2>/tmp/fping.log" % (base_dir, segment.strip())
            os.system(fping_cmd)
            dead_ip = "cat /tmp/fping.log | awk '$5 ~ /100%/{print $1}'"
            for line in commands.getoutput(dead_ip).split("\n"):
                if line and line in ip_list:
                    print('The machine %s is Down.' % line)
                    ip_is_down.append(line)
            alive_ip = "cat /tmp/fping.log | awk '$1 !~ /ICMP/ && $5 !~ /100%/{print $1}'"
            for line in commands.getoutput(alive_ip).split("\n"):
                if line and line not in ip_list and line not in exclude_ip:
                    # 假如是网络设备，则自动录入到cmdb
                    cmd = """snmpget -v 2c -c wdpublic {0} sysName.0 |awk '{{print $NF}}'""".format(line)
                    status, sys_name = commands.getstatusoutput(cmd)
                    if status == 0 and "Timeout" not in sys_name:
                        cmd = """snmpget -v 2c -c wdpublic {0} sysDescr.0 |awk '{{$1="";$2="";$3="";print}}'""".format(line)
                        _, descr = commands.getstatusoutput(cmd)
                        if descr.strip() != "" and re.match(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', line):
                            data = {"sys_name": sys_name, "login_type": "telnet", "snmp": line + ":161",
                                    "login_address": line, "product_name": descr, "comment": "脚本自动添加！"}
                            headers = {'Content-Type': 'application/json'}
                            url = "http://oneops.yadoom.com/cmdb/v1/net_device_list/"
                            resp = requests.post(url, headers=headers, json=data)
                            print(resp.status_code, resp.content)
                            continue
                    # 假如是服务器，则使用默认密码尝试登录，并添加免密密钥
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        try:
                            s.connect((line, 3389))
                            s.shutdown(2)
                            not_in_cmdb.append(line + " Windows!")
                            continue
                        except:
                            try:
                                s.connect((line, 22))
                                s.shutdown(2)
                                s.close()
                            except:
                                not_in_cmdb.append(line + " 22端口不通！")
                                continue
                        user, password = "root", "xxxxx"
                        _ssh, _ = get_ssh_session(line, user, password)
                        if _ssh is None:
                            user, password = "root", "xxxxx"
                            _ssh, _ = get_ssh_session(line, user, password)
                            if _ssh is None:
                                not_in_cmdb.append(line + " 默认密码登陆失败")
                                continue
                        _, _, stderr = _ssh.exec_command("ls /root/.ssh/authorized_keys")
                        if stderr.read().strip():
                            _, _, _ = _ssh.exec_command("mkdir -p -m 700 /root/.ssh/")
                            _sftp = get_sftp_session(line, user, password)
                            _sftp.put("/root/.ssh/id_rsa.pub", "/root/.ssh/authorized_keys")
                            _sftp.close()
                            _, _, _ = _ssh.exec_command("chmod 600 /root/.ssh/authorized_keys")
                        else:
                            # authorized_keys 文件已存在，则追加公钥到 authorized_keys
                            id_rsa_pub = commands.getoutput('cat /root/.ssh/id_rsa.pub')
                            cmd = """if ! grep 'yunwei' {0}; then echo '{1}' >> {0}; fi""".format(
                                '/root/.ssh/authorized_keys', id_rsa_pub
                            )
                            _, _, _ = _ssh.exec_command(cmd)

                        _, stdout, stderr = _ssh.exec_command("hostname")
                        output, error = stdout.read().strip(), stderr.read().strip()
                        if error:
                            not_in_cmdb.append(line + " 添加免密登陆失败：" + error)
                        else:
                            not_in_cmdb.append("{0} {1} 已添加免密登陆！".format(line, output))
                        _ssh.close()
                    except Exception as e:
                        not_in_cmdb.append(line + " 默认密码登陆失败：%s" % (str(e)))
            # os.remove("/tmp/fping.log")
        except:
            print(traceback.print_exc())
    # 告警
    print('Not in cmdb:', not_in_cmdb)
    if not_in_cmdb:
        send_mail('请登陆服务器手动执行CMDB Agent，查看报错：\n' + '\n'.join(not_in_cmdb),
                  ['yukai_44134@yadoom.com'], u'以下ip未登记到基础库')
    # if ip_is_down:
    #     send_mail('请确认是否可以释放ip资源：\n' + '\n'.join(ip_is_down),
    #               ['yukai_44134@yadoom.com'], u'以下ip 已经关机')

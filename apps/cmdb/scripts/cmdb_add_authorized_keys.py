#!/usr/bin/python
# coding:utf-8

import paramiko
import commands
import urllib
import httplib
import traceback
import sys
from IPy import IP
reload(sys)
sys.setdefaultencoding("utf-8")


def send_mail(contents, mail_to, sub=u'运维告警邮件'):
    try:
        contents = contents.replace('\n', '<br>')
        my_dict = {'to': ','.join(mail_to), 'subject': sub, 'contents': contents}
        http_conn = httplib.HTTPConnection("172.20.1.47", 80)
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


def get_ssh_session(ip, user, password):
    try:
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
        print("Using: python %s <192.168.0.0/24>" % sys.argv[0])
        sys.exit()
    password_wrong_list, add_authorized_key_failed_list, add_success = list(), list(), list()
    try:
        for ip in IP(sys.argv[1]):
            ip = str(ip)
            try:
                ssh_file = "/root/.ssh/id_rsa"
                ssh = paramiko.SSHClient()
                ssh.load_system_host_keys()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                key = paramiko.RSAKey.from_private_key_file(filename=ssh_file, password="")
                ssh.connect(ip, port=22, username="root", pkey=key, timeout=3)
                ssh.close()
            except paramiko.ssh_exception.AuthenticationException as e:
                try:
                    user, password = "root", "xxxxx"
                    _ssh, _ = get_ssh_session(ip, user, password)
                    if _ssh is None:
                        user, password = "root", "xxxxx"
                        _ssh, _ = get_ssh_session(ip, user, password)
                        if _ssh is None:
                            password_wrong_list.append(ip + " 默认密码登陆失败！")
                            continue
                    _, _, stderr = _ssh.exec_command("ls /root/.ssh/authorized_keys")
                    if stderr.read().strip():
                        _, _, _ = _ssh.exec_command("mkdir -p -m 700 /root/.ssh/")
                        _sftp = get_sftp_session(ip, user, password)
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
                        add_authorized_key_failed_list.append(ip + " 添加免密登陆失败！")
                    else:
                        add_success.append("{0} {1} 已添加免密登陆！".format(ip, output))
                    _ssh.close()
                except Exception as e:
                    add_authorized_key_failed_list.append(ip + " 添加免密登陆失败：%s" % (str(e)))
            except Exception as e:
                pass
    except:
        traceback.print_exc()
    if password_wrong_list or add_authorized_key_failed_list or add_success:
        send_mail('{0}\n{1}\n{2}'.format('\n'.join(password_wrong_list),
                                         '\n'.join(add_authorized_key_failed_list),
                                         '\n'.join(add_success)),
                  ['yukai_44134@yadoom.com'], u'添加免密登陆脚本执行结果')

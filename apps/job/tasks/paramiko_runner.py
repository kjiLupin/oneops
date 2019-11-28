# coding: utf-8

import paramiko
import datetime
import os
from common.utils.base import BASE_DIR

FILE_UPLOAD_TMP_DIR = os.path.join(BASE_DIR, 'logs/upload/')
FILE_DOWNLOAD_TMP_DIR = os.path.join(BASE_DIR, 'logs/download/')


class MyTaskRunner(object):
    def __init__(self, host_id, hostuser, task_id):
        self.host = Asset.objects.get(id=host_id)
        self.hostuser = HostUser.objects.get(id=hostuser)
        self.task = task_id
        self.ssh = None
        self.sftp = None
        
    def save_batch_task(self, cmd_result, res_status):
        task = TaskLog.objects.get(id=self.task)
        task.result = cmd_result
        task.status = res_status
        task.end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task.save()
        self.close_connect()
    
    def save_scheduled_task_log(self, date_start, cmd_result, res_status):
        date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task = ScheduledTask.objects.get(id=self.task)
        scheduled_task_log = ScheduledTaskLog(task=task, host=self.host, hostuser=self.hostuser, command='changepasswd', cmd_result=cmd_result, res_status=res_status,
                                              start_time=date_start, end_time=date_now)
        scheduled_task_log.save()
        self.close_connect()
        
    def save_asset_mes(self, passwd_auth_active, hosts_allow, hosts_deny, illegal_login_info, sys_time, redis_ports):
        assetmes = AssetMes.objects.filter(host_id=self.host.id)
        if assetmes:
            assetmes = assetmes[0]
            assetmes.passwd_auth_active = passwd_auth_active
            assetmes.hosts_allow = hosts_allow
            assetmes.hosts_deny = hosts_deny
            assetmes.sys_time = sys_time
            assetmes.redis_ports = redis_ports
            assetmes.illegal_login_info = illegal_login_info
        else:
            assetmes = AssetMes(host=self.host, passwd_auth_active=passwd_auth_active, hosts_allow=hosts_allow, hosts_deny=hosts_deny,
                                sys_time=sys_time, redis_ports=redis_ports, illegal_login_info=illegal_login_info)
        assetmes.save()
        self.close_connect()
            
    def get_connect(self):
        
        try:
            ssh = paramiko.SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.hostuser.login_type == 'K':
                mykey = paramiko.RSAKey.from_private_key_file(filename=self.hostuser.key_file, password=CRYPTOR.decrypt(self.hostuser.ssh_passwd))
                ssh.connect(self.host.ip, port=int(self.host.port), username=self.hostuser.username, pkey=mykey, timeout=30)
            else:
                ssh.connect(self.host.ip, port=int(self.host.port), username=self.hostuser.username, password=CRYPTOR.decrypt(self.hostuser.password), compress=True, look_for_keys=False, timeout=30)
            transport = ssh.get_transport()
            transport.set_keepalive(30)
            transport.use_compression(True)
            self.ssh = ssh
            connect_result = ''
        except Exception as e:
            connect_result = e
        return connect_result

    def get_sftp(self):
        try:
            transport = paramiko.Transport((self.host.ip, int(self.host.port)))
            if self.hostuser.login_type == 'K':
                mykey = paramiko.RSAKey.from_private_key_file(filename=self.hostuser.key_file, password=CRYPTOR.decrypt(self.hostuser.ssh_passwd))
                transport.connect(username=self.hostuser.username, pkey=mykey)
            else:
                transport.connect(username=self.hostuser.username, password=CRYPTOR.decrypt(self.hostuser.password))
            transport.set_keepalive(30)
            transport.use_compression(True)
            sftp = paramiko.SFTPClient.from_transport(transport)
            self.sftp = sftp
            connect_result = ''
        except Exception as e:
            print 'get sftp Error: ', e
            connect_result = e
        return connect_result

    def exec_command(self, command, code="utf8"):
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command, timeout=120)
            cmd_result = ''
            res_status = 'success'
            output = stdout.read().strip()
            error = stderr.read().strip()
            # print error, output
            if error:
                cmd_result += error
                res_status = 'failed'
            if output:
                cmd_result += output
                res_status = 'success'
            cmd_result = cmd_result.decode(code, "ignore").strip()
        except Exception as e:
            cmd_result = 'myError: ' + str(e)
            res_status = 'failed'
        return cmd_result, res_status

    def exec_upload(self, source_file, des_file, code='UTF-8'):
        try:
            task_log = TaskLog.objects.get(id=self.task)
            batch_task = BatchTask.objects.get(id=task_log.task_id)
            local_path = "%s/%s" % (FILE_TMP_DIR, batch_task.user.username)
            source_file_list = source_file.split("|")
            for filename in source_file_list:
                desfiname = des_file + "/" + filename
                file_path = local_path + "/" + filename
                self.sftp.put(file_path, desfiname.encode(code))
            cmd_result = '%s  ' % source_file
            cmd_result += " sent to remote path [%s] is completed" % des_file
            res_status = 'success'
        except Exception as e:
            cmd_result = e
            res_status = 'failed'
        return cmd_result, res_status   

    def exec_download(self, des_path, local_path, code='UTF-8'):
        try:
            filename = local_path + "/" + des_path.split('/')[-1]+"_"+self.host.ip+"_"+datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            self.sftp.get(des_path.encode(code), filename)
            cmd_result = filename
            res_status = 'success'
        except Exception as e:
            print e
            cmd_result = e
            res_status = 'failed'
        return cmd_result, res_status
  
    def close_connect(self):
        if self.ssh is not None:
            self.ssh.close()
        if self.sftp is not None:
            self.sftp.close()


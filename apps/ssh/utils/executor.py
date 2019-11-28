#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paramiko
import traceback
from ssh.utils.host_user import get_host_user


class Executor(object):

    def __init__(self, ip, port, user='root'):
        self.ip = ip
        self.port = int(port)
        self.host_user = get_host_user(ip, port, user)
        self.ssh = None
        self.sftp = None

    def get_connect(self):
        try:
            if self.host_user is None:
                return False, "未绑定HostUser！"
            else:
                _ssh = paramiko.SSHClient()
                _ssh.load_system_host_keys()
                _ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                if self.host_user.login_type == 'K':
                    _key = paramiko.RSAKey.from_private_key_file(filename=self.host_user.key_path,
                                                                 password=self.host_user.key_password)
                    _ssh.connect(self.ip, port=self.port, username=self.host_user.username, pkey=_key, timeout=30)
                else:
                    _ssh.connect(self.ip, port=self.port, username=self.host_user.username,
                                 password=self.host_user.password, compress=True,
                                 look_for_keys=False, timeout=30)
            transport = _ssh.get_transport()
            transport.set_keepalive(30)
            transport.use_compression(True)
            self.ssh = _ssh
            return True, "success"
        except Exception as e:
            traceback.print_exc()
            return False, str(e)

    def get_sftp(self):
        try:
            if self.host_user is None:
                return False, "未绑定HostUser！"
            transport = paramiko.Transport(self.ip, self.port)
            if self.host_user.login_type == 'K':
                _key = paramiko.RSAKey.from_private_key_file(filename=self.host_user.key_path,
                                                             password=self.host_user.key_password)
                transport.connect(username=self.host_user.username, pkey=_key)
            else:
                transport.connect(username=self.host_user.username, password=self.host_user.password)
            transport.set_keepalive(30)
            transport.use_compression(True)
            _sftp = paramiko.SFTPClient.from_transport(transport)
            self.sftp = _sftp
            return True, "success"
        except Exception:
            return False, traceback.print_exc()

    def exec_command(self, cmd):
        _, stdout, stderr = self.ssh.exec_command(cmd)
        output, error = stdout.read().strip(), stderr.read().strip()
        if error:
            return str(error, encoding='utf-8')
        return str(output, encoding='utf-8')

    def close_connect(self):
        if self.ssh is not None:
            self.ssh.close()
        if self.sftp is not None:
            self.sftp.close()

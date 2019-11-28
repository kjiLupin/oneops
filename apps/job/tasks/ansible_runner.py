# coding: utf-8
from .ansible_api import AnsibleAPI


class AnsibleRunner(AnsibleAPI):
    def __init__(self, host, resource, hosts_file, hostuser, task_id, *args, **kwargs):
        self.host = host
        self.hostuser = hostuser
        self.playbook = None
        self.task = task_id
        super(AnsibleAPI, self).__init__(resource, hosts_file, *args, **kwargs)
        
    def save_task_log(self):
        super(AnsibleRunner, self).save_result()

    def run_ad_hoc(self, host, module_name, module_args):
        """
        :param host:
        :param module_name: command, shell, copy
        :param module_args:  "src=%s dest=%s" % (src, dest)
        :return:
        """
        super(AnsibleRunner, self).run_ad_hoc(host, module_name, module_args)

    def run_playbook(self, playbook, extra_vars=None):
        """
        :param playbook: ['']
        :param extra_vars: {"key": "value"}
        :return:
        """
        super(AnsibleRunner, self).run_playbook(playbook, extra_vars)

# -*- coding: utf-8 -*-
from cmdb.models.asset import Server
from cmdb.models.business import App
from ssh.models.host_user import HostUserAsset


class GenResource(object):

    @staticmethod
    def gen_host_list(host_ids):
        """
        生成格式为：[{"ip": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}, ...]
        :return:
        """
        host_list = []
        for host_id in host_ids:
            host = {}
            s = Server.objects.get(id=host_id)
            host['hostname'] = s.hostname
            host['ip'] = s.login_address.split(":")[0]
            host['port'] = int(s.login_address.split(":")[1])

            hua = HostUserAsset.objects.filter(asset=s, host_user__username='root')
            if hua:
                hu = hua[0].host_user
                host['username'] = hu.username
                if hu.login_type == "K":
                    host['ssh_key'] = hu.key_path
                else:
                    host['password'] = hu.password
            # if host_obj.host_vars:
            #     host_vars = eval(host_obj.host_vars)
            #     for k, v in host_vars.items():
            #         host[k] = v
            host_list.append(host)
        return host_list
    #
    # @staticmethod
    # def gen_host_dict(group_ids):
    #     """
    #     生成所选主机组内的主机地址, 生成格式是[{'host_id': host.id, 'host_ip': host.ip}, {...}]
    #     :return:
    #     """
    #     hosts_temp = []
    #     for group_id in group_ids:
    #         host_list = AnsibleInventory.objects.prefetch_related('ans_group_hosts').get(
    #             id=group_id).ans_group_hosts.all()
    #         host_d = [{'host_id': host.id, 'host_ip': host.assets.asset_management_ip} for host in host_list]
    #         hosts_temp.extend(host_d)
    #
    #     hosts = []
    #     for i in hosts_temp:
    #         if i not in hosts:
    #             hosts.append(i)
    #
    #     return hosts
    #
    # def gen_group_dict(self, group_ids):
    #     """
    #     生成格式为:
    #     {
    #             "group1": {
    #                 "hosts": [{"ip": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}, ...],
    #                 "group_vars": {"var1": value1, "var2": value2, ...}
    #             }
    #         }
    #     :return:
    #     """
    #     resource = {}
    #     group_names = []
    #     for group_id in group_ids:
    #         group_values = {}
    #         group_obj = AnsibleInventory.objects.prefetch_related('ans_group_hosts').get(id=group_id)
    #         group_names.append(group_obj.ans_group_name)
    #         host_ids = [host.id for host in group_obj.ans_group_hosts.all()]
    #         group_values['hosts'] = self.gen_host_list(host_ids)
    #         if group_obj.ans_group_vars:
    #             group_values['group_vars'] = eval(group_obj.ans_group_vars)
    #         resource[group_obj.ans_group_name] = group_values
    #     return resource, group_names

    def gen_host_dict_by_app_id(self, app_id):
        """
        生成格式为:
        {
                "group1": {
                    "hosts": [{"ip": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}, ...],
                    "group_vars": {"var1": value1, "var2": value2, ...}
                }
            }
        :return:
        """
        app = App.objects.get(id=app_id)
        host_ids = [host.id for host in app.app_server.all()]
        host_list = self.gen_host_list(host_ids)
        return {
            app.app_code: {'hosts': host_list}
        }

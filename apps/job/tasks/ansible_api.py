#!/usr/bin/env python
import traceback
import json
import shutil
import datetime
from collections import namedtuple
from ansible.errors import AnsibleParserError
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.inventory.group import Group
from ansible.inventory.host import Host
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase
import ansible.constants as C
from job.models.job import HostUser, Task, TaskLog
from job.tasks.redis import AnsibleRedisPool

C.HOST_KEY_CHECKING = False


class AdHocResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """

    def __init__(self, uuid, sock, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}
        self.redis_key = uuid
        self.sock = sock

    def v2_runner_on_unreachable(self, result):
        print('unreachable-', result._result)
        if 'msg' in result._result:
            msg = result._result.get('msg').encode().decode('utf-8')
            data = '<code style="color: #FF0000">\n{host} | unreachable | rc={rc} >> \n{stdout}\n</code>'.format(
                host=result._host.name, rc=result._result.get('rc'), stdout=msg)
        else:
            msg = json.dumps(result._result, indent=4, ensure_ascii=False)
            data = '<code style="color: #FF0000">\n{host} | unreachable >> \n{stdout}\n</code>'.format(
                host=result._host.name, stdout=msg)
        if self.sock:
            self.sock.send(data)
        self.host_unreachable[result._host.name] = msg
        AnsibleRedisPool.set_hash_redis(self.redis_key, 'unreach', result._result["stdout"])
        AnsibleRedisPool.expire(self.redis_key, 43200)

    def v2_runner_on_ok(self, result, *args, **kwargs):
        print('ok-', result._result)
        if 'stdout' in result._result and 'rc' in result._result:
            msg = result._result.get('stdout').encode().decode('utf-8')
            data = '<code style="color: #008000">\n{host} | success | rc={rc} >> \n{stdout}\n</code>'.format(
                host=result._host.name, rc=result._result.get('rc'), stdout=msg)
        elif 'results' in result._result and 'rc' in result._result:
            msg = result._result.get('results')[0].encode().decode('utf-8')
            data = '<code style="color: #008000">\n{host} | success | rc={rc} >> \n{stdout}\n</code>'.format(
                host=result._host.name, rc=result._result.get('rc'), stdout=msg)
        elif 'module_stdout' in result._result and 'rc' in result._result:
            msg = result._result.get('module_stdout').encode().decode('utf-8')
            data = '<code style="color: #008000">\n{host} | success | rc={rc} >> \n{stdout}\n</code>'.format(
                host=result._host.name, rc=result._result.get('rc'), stdout=msg)
        else:
            msg = json.dumps(result._result, indent=4, ensure_ascii=False)
            data = '<code style="color: #008000">\n{host} | success >> \n{stdout}\n</code>'.format(
                host=result._host.name, stdout=msg)
        if self.sock:
            self.sock.send(data)
        #
        # if result.task_name == "copy":
        #     msg = "upload to " + result._result["dest"] + " success."
        # elif result.task_name == "fetch":
        #     msg = "download " + result._result["file"] + " success."
        # else:
        #     msg = result._result["stdout"]
        self.host_ok[result._host.name] = msg
        AnsibleRedisPool.set_hash_redis(self.redis_key, 'success', result._result["stdout"])
        AnsibleRedisPool.expire(self.redis_key, 43200)

    def v2_runner_on_failed(self, result, *args, **kwargs):
        print('failed-', result._result)
        if 'stderr' in result._result:
            msg = result._result.get('stderr').encode().decode('utf-8')
            data = '<code style="color: #FF0000">\n{host} | failed | rc={rc} >> \n{stdout}\n</code>'.format(
                host=result._host.name, rc=result._result.get('rc'), stdout=msg)
        elif 'module_stdout' in result._result:
            msg = result._result.get('module_stdout').encode().decode('utf-8')
            data = '<code style="color: #FF0000">\n{host} | failed | rc={rc} >> \n{stdout}\n</code>'.format(
                host=result._host.name, rc=result._result.get('rc'), stdout=msg)
        else:
            msg = json.dumps(result._result, indent=4, ensure_ascii=False)
            data = '<code style="color: #FF0000">\n{host} | failed >> \n{stdout}\n</code>'.format(
                host=result._host.name, stdout=msg)
        if self.sock:
            self.sock.send(data)
        self.host_failed[result._host.name] = msg
        AnsibleRedisPool.set_hash_redis(self.redis_key, 'failed', result._result["stdout"])
        AnsibleRedisPool.expire(self.redis_key, 43200)


class PlaybookResultCallback(CallbackBase):

    def __init__(self, uuid, sock, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}
        self.redis_key = uuid
        self.sock = sock

    def v2_playbook_on_play_start(self, play):
        name = play.get_name().strip()
        if name:
            data = format(f'<code style="color: #FFFFFF">\nPLAY [{name}]', '*<150') + ' \n</code>'
        else:
            data = format('<code style="color: #FFFFFF">\nPLAY', '*<150') + ' \n</code>'
        if self.sock:
            self.sock.send(data)

    def v2_playbook_on_task_start(self, task, is_conditional):
        data = format(f'<code style="color: #FFFFFF">\nTASK [{task.get_name()}]', '*<150') + ' \n</code>'
        if self.sock:
            self.sock.send(data)

    def v2_runner_on_skipped(self, result):
        if 'changed' in result._result:
            del result._result['changed']
        data = '<code style="color: #FFFF00">[{}]=> {}: {}\n</code>'.format(
            result._host.name, 'skipped', self._dump_results(result._result))
        if self.sock:
            self.sock.send(data)

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        data = format('<code style="color: #FFFFFF">\nPLAY RECAP ', '*<150') + '\n'
        self.sock.send(data)
        for h in hosts:
            s = stats.summarize(h)
            data = '<code style="color: #FFFFFF">{} : ok={} changed={} unreachable={} failed={} skipped={}\n</code>'.format(
                h, s['ok'], s['changed'], s['unreachable'], s['failures'], s['skipped'])
            if self.sock:
                self.sock.send(data)

    def v2_runner_on_unreachable(self, result):
        print('unreachable-', result._result)
        data = '<code style="color: #FF0000">[{}]=> {}: {}\n</code>'.format(
            result._host.name, 'unreachable', self._dump_results(result._result))
        if self.sock:
            self.sock.send(data)
        self.host_unreachable[result._host.get_name()] = self._dump_results(result._result)
        AnsibleRedisPool.set_hash_redis(self.redis_key, 'unreach', result._result["stdout"])
        AnsibleRedisPool.expire(self.redis_key, 43200)

    def v2_runner_on_ok(self, result, *args, **kwargs):
        print('ok-', result._result)
        # if result.task_name == "copy":
        #     msg = "upload to " + result._result["dest"] + " success."
        # elif result.task_name == "fetch":
        #     msg = "download " + result._result["file"] + " success."
        # else:
        #     msg = result._result["stdout"]
        if result.is_changed():
            data = '<code style="color: #FFFF00">[{}]=> changed\n</code>'.format(result._host.name)
        else:
            data = '<code style="color: #008000">[{}]=> ok\n</code>'.format(result._host.name)
        if self.sock:
            self.sock.send(data)
        self.host_ok[result._host.get_name()] = result._result["stdout"]
        AnsibleRedisPool.set_hash_redis(self.redis_key, 'success', result._result["stdout"])
        AnsibleRedisPool.expire(self.redis_key, 43200)

    def v2_runner_on_failed(self, result, *args, **kwargs):
        print('failed-', result._result)
        if 'changed' in result._result:
            del result._result['changed']
        data = '<code style="color: #FF0000">[{}]=> {}: {}\n</code>'.format(
            result._host.name, 'failed', self._dump_results(result._result))
        if self.sock:
            self.sock.send(data)
        self.host_failed[result._host.get_name()] = self._dump_results(result._result)
        AnsibleRedisPool.set_hash_redis(self.redis_key, 'failed', result._result["stdout"])
        AnsibleRedisPool.expire(self.redis_key, 43200)


class MyInventory(InventoryManager):

    def __init__(self, loader, resource, hosts_file):
        """
        resource的数据格式是一个列表字典，比如
            {
                "group1": {
                    "hosts": [{"hostname": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}, ...],
                    "group_vars": {"var1": value1, "var2": value2, ...}
                }
            }

        如果你只传入1个列表，这默认该列表内的所有主机属于default_group组,比如
            [{"hostname": "10.0.0.0", "port": "22", "username": "test", "password": "pass"}, ...]
        sources是原生的方法，参数是配置的inventory文件路径，可以指定一个，也可以以列表的形式可以指定多个。
        """
        super(MyInventory, self).__init__(loader=loader, sources=hosts_file)
        self.resource = resource
        self.gen_inventory()

    def my_add_group(self, hosts, group_name, group_vars=None):
        """
        add hosts to a group
        """
        self.add_group(group_name)

        # if group variables exists, add them to group
        if group_vars:
            for key, value in group_vars.items():
                self.groups[group_name].set_variable(key, value)
        for host in hosts:
            # set connection variables
            hostname = host.get("hostname")
            login_ip = host.get('ip', hostname)
            login_port = host.get("port", 22)
            self.add_host(login_ip, group_name, login_port)

            username = host.get("username")
            password = host.get("password")
            ssh_key = host.get("ssh_key")
            self.get_host(login_ip).set_variable('ansible_ssh_host', login_ip)
            self.get_host(login_ip).set_variable('ansible_ssh_port', login_port)
            self.get_host(login_ip).set_variable('ansible_ssh_user', username)
            self.get_host(login_ip).set_variable('ansible_ssh_pass', password)
            self.get_host(login_ip).set_variable('ansible_ssh_private_key_file', ssh_key)

            # set other variables
            for key, value in host.items():
                if key not in ["hostname", "ip", "port", "username", "password"]:
                    self.get_host(login_ip).set_variable(key, value)

        # my_group = Group(name=group_name)
        #
        # # if group variables exists, add them to group
        # if group_vars:
        #     for key, value in group_vars.items():
        #         my_group.set_variable(key, value)
        # for host in hosts:
        #     # set connection variables
        #     hostname = host.get("hostname")
        #     login_ip = host.get('ip', hostname)
        #     login_port = host.get("port", 22)
        #     username = host.get("username")
        #     password = host.get("password")
        #     ssh_key = host.get("ssh_key")
        #
        #     my_host = Host(name=hostname, port=login_port)
        #     my_host.set_variable('ansible_ssh_host', login_ip)
        #     my_host.set_variable('ansible_ssh_port', login_port)
        #     my_host.set_variable('ansible_ssh_user', username)
        #     my_host.set_variable('ansible_ssh_pass', password)
        #     my_host.set_variable('ansible_ssh_private_key_file', ssh_key)
        #
        #     # set other variables
        #     for key, value in host.iteritems():
        #         if key not in ["hostname", "port", "username", "password"]:
        #             my_host.set_variable(key, value)
        #     # add to group
        #     my_group.add_host(my_host)
        #
        # self.inventory.add_group(my_group)

    def gen_inventory(self):
        """
        add hosts to inventory.
        """
        if self.resource:
            if isinstance(self.resource, list):
                self.my_add_group(self.resource, 'default_group')
            elif isinstance(self.resource, dict):
                for name, hosts_and_vars in self.resource.items():
                    self.my_add_group(hosts_and_vars.get("hosts"), name, hosts_and_vars.get("group_vars"))


class AnsibleAPI(object):
    """
    This is a General object for parallel execute modules.
    """

    def __init__(self, task_id, uuid, sock=None, *args, **kwargs):
        self.task_id = task_id
        self.uuid = uuid
        self.sock = sock
        self.resource = kwargs.pop('resource')
        self.hosts_file = kwargs.pop('hosts_file')
        self.remote_user = 'root'
        self.passwords = None
        self.private_key_file = None

        host_user_id = kwargs.get('host_user')
        if host_user_id:
            host_user = HostUser.objects.get(id=host_user_id)
            kwargs["host_user"] = "{}({})".format(host_user.username, host_user.description)
            self.remote_user = host_user.username
            if host_user.login_type == "K":
                self.private_key_file = host_user.key_path
            else:
                self.passwords = dict(vault_pass=host_user.password)
        self.task_info = kwargs
        self.inventory = None
        self.variable_manager = None
        self.loader = None
        self.options = None
        self.callback = None
        self.__initialize_data()
        self.results_raw = {}

    def __initialize_data(self):
        Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'async',
                                         'remote_user', 'ask_pass', 'private_key_file', 'ssh_common_args',
                                         'ssh_extra_args', 'sftp_extra_args', 'scp_extra_args', 'timeout',
                                         'become', 'become_method', 'become_user', 'check', 'diff', 'listhosts',
                                         'listtasks', 'listtags',
                                         'syntax'])
        # initialize needed objects
        self.loader = DataLoader()
        # if self.passwords is None:
        self.options = Options(connection='smart', module_path=None, forks=10, async=5,
                               remote_user=self.remote_user, ask_pass=False, private_key_file=self.private_key_file,
                               ssh_common_args=None,
                               ssh_extra_args=None, sftp_extra_args=None, scp_extra_args=None, timeout=10,
                               become=None, become_method=None, become_user=None, check=False, diff=False,
                               listhosts=False, listtasks=False,
                               syntax=False, listtags=None)

        self.inventory = MyInventory(self.loader, self.resource, self.hosts_file)
        self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)

    def run_ad_hoc(self, host, module_name, module_args):
        """
        run module from andible ad-hoc.
        module_name: ansible module_name
        module_args: ansible module args
        """

        self.callback = AdHocResultCallback(self.uuid, self.sock)

        # create play with tasks
        play_source = dict(
            name="Ansible ad-hoc",
            hosts=host,
            gather_facts='no',
            tasks=[dict(action=dict(module=module_name, args=module_args))]
        )

        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)

        # actually run it
        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords=self.passwords,
            )
            tqm._stdout_callback = self.callback
            C.HOST_KEY_CHECKING = False
            tqm.run(play)
        except Exception as e:
            Task.objects.filter(id=self.task_id).update(error_msg=str(e), executed=True)
        finally:
            if tqm is not None:
                tqm.cleanup()
            shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)

    def run_playbook(self, playbook, extra_vars):
        """
        run ansible palybook
        """
        try:
            self.callback = PlaybookResultCallback(self.uuid, self.sock)
            self.variable_manager.extra_vars = extra_vars
            # actually run it
            pbex = PlaybookExecutor(
                playbooks=playbook, inventory=self.inventory, variable_manager=self.variable_manager,
                loader=self.loader, options=self.options, passwords=self.passwords,
            )
            pbex._tqm._stdout_callback = self.callback
            C.HOST_KEY_CHECKING = False
            pbex.run()
        except AnsibleParserError:
            code = 1001
            results = {'playbook': ','.join(playbook), 'msg': 'playbook have syntax error', 'flag': False}
            return code, results
        except Exception as e:
            traceback.print_exc()
            Task.objects.filter(id=self.task_id).update(error_msg=str(e))

    def save_result(self):
        self.results_raw = {}
        for host, result in self.callback.host_ok.items():
            print("host_success", host, result)
            TaskLog.objects.create(
                task_id=self.task_id,
                host=host,
                host_user=self.task_info.get('host_user'),
                module_name=self.task_info.get('module_name'),
                module_args=self.task_info.get('module_args'),
                playbook_name=self.task_info.get('playbook_name'),
                playbook=self.task_info.get('playbook'),
                extra_vars=self.task_info.get('extra_vars'),
                result=result,
                end_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status='success'
            )

        for host, result in self.callback.host_failed.items():
            print("host_failed", host, result)
            TaskLog.objects.create(
                task_id=self.task_id,
                host=host,
                host_user=self.task_info.get('host_user'),
                module_name=self.task_info.get('module_name'),
                module_args=self.task_info.get('module_args'),
                playbook_name=self.task_info.get('playbook_name'),
                playbook=self.task_info.get('playbook'),
                extra_vars=self.task_info.get('extra_vars'),
                result=result,
                end_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status='failed'
            )

        for host, result in self.callback.host_unreachable.items():
            print("host_unreachable", host, result)
            TaskLog.objects.create(
                task_id=self.task_id,
                host=host,
                host_user=self.task_info.get('host_user'),
                module_name=self.task_info.get('module_name'),
                module_args=self.task_info.get('module_args'),
                playbook_name=self.task_info.get('playbook_name'),
                playbook=self.task_info.get('playbook'),
                extra_vars=self.task_info.get('extra_vars'),
                result=result,
                end_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status='failed'
            )

        # self.results_raw = {'success': {}, 'failed': {}, 'unreachable': {}}
        # for host, result in self.callback.host_ok.items():
        #     self.results_raw['success'][host] = result._result
        #
        # for host, result in self.callback.host_failed.items():
        #     self.results_raw['failed'][host] = result._result.get('msg') or result._result
        #
        # for host, result in self.callback.host_unreachable.items():
        #     self.results_raw['unreachable'][host] = result
        #
        # return self.results_raw

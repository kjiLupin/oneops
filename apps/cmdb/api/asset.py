# -*- coding: utf-8 -*-
import traceback
import re
import datetime
import simplejson as json
from dateutil.relativedelta import relativedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin

from django.views.generic import View
from cmdb.models.base import IDC, Ip
from cmdb.models.asset import AppEnv, Server, NetDevice, Nic, Storage, AppResource, ServerResource
from cmdb.models.business import BizMgtDept, App
from cmdb.api.ip import get_segment_by_ip, get_or_create_ip_obj
from cmdb.views.business import get_total_dept_child_node_id
from common.utils.base import send_msg_to_admin
from common.mixins import RPCIpWhiteMixin, JSONResponseMixin


@csrf_exempt
def api_compatibility(request):
    post_data = json.loads(request.body.decode('utf-8'))
    if 'hostname' in post_data and 'sn' in post_data:
        if post_data['os'] != 'VMware ESX':
            send_msg_to_admin("还在跑老cmdb_agent脚本:" + post_data.get('hostname') + ' sn:' + post_data.get('sn'))
    jsonrpc_id = post_data['id']
    func = post_data['method']
    print(jsonrpc_id, type(jsonrpc_id), func)
    if jsonrpc_id == 1 and func == 'server.radd':
        try:
            data = post_data['params']
            if "server_cpu" in data:
                data['cpu_total'] = data.pop('server_cpu')
            if "server_mem" in data:
                data['mem_total'] = data.pop('server_mem')
            if "used_cpu" in data:
                data['cpu_used'] = data.pop('used_cpu')
            if "used_mem" in data:
                data['mem_used'] = data.pop('used_mem')
            if "server_disk" in data:
                data['disk'] = data.pop('server_disk')
            if "disk_used" in data:
                data.pop("disk_used")
            if "vendor" in data:
                data["manufacturer"] = data.pop("vendor")
            if "vm_num" in data:
                data['vm_count'] = data.pop('vm_num')
            storage_info = dict()
            if "vmware_disk" in data:
                vmware_disk = data.pop('vmware_disk')
                print(vmware_disk)
                data["disk"] = '{}/{}%'.format(vmware_disk["total"], vmware_disk["used_pct"])
                storage_info = vmware_disk["detail"]

            # 从esx获取信息时，可得到宿主机的hostname，将其转换成 parent_id
            if "parent_host" in data:
                parent_host_name = data.pop("parent_host")
                if Server.objects.filter(hostname=parent_host_name).exists():
                    data["parent_id"] = Server.objects.get(hostname=parent_host_name).id

            # 从openstack获取信息，可获取宿主机的hostname和虚拟机的uuid。所以要根据宿主机的hostname得到parent_id。
            # 当根据 hostname取出多台或0台，则不做处理。
            if "parent_host_name" in data:
                parent_host_name = data.pop("parent_host_name")
                if parent_host_name == "":
                    return JsonResponse({'code': 1, 'errmsg': 'parent hostname is null!'})
                if Server.objects.filter(hostname=parent_host_name).count() == 1:
                    data["parent_id"] = Server.objects.get(hostname=parent_host_name).id

            # 从openstack获取信息，版本太低获取不到 虚拟主机的uuid。只能根据hostname来确定主机。
            # 当根据 hostname取出多台或0台，则不做处理。
            if "uuid" not in data:
                if Server.objects.filter(hostname=data["hostname"]).count() == 1:
                    data["uuid"] = Server.objects.get(hostname=data["hostname"]).uuid

            if "nic_mac_ip" in data:
                nic_mac_ip_dict = data.pop("nic_mac_ip")
                if isinstance(nic_mac_ip_dict, str):
                    nic_mac_ip_dict = json.loads(nic_mac_ip_dict)
            else:
                nic_mac_ip_dict = {}
            if "tomcat_ports" in data:
                tomcat_ports = data.pop("tomcat_ports")
            else:
                tomcat_ports = list()
            if "check_update_time" in data:
                data["date_last_checked"] = data.pop("check_update_time")
            else:
                data["date_last_checked"] = datetime.datetime.now()

            if "product_name" in data:
                if re.search(r'OpenStack|KVM|Virtual', data['product_name'], re.I):
                    data['is_vm'] = True

            if "uuid" in data and data["uuid"] != "":
                if "hostname" in data:
                    server_query = Server.objects.filter(uuid=data["uuid"])
                    if server_query.exists():
                        server_query.update(**data)
                        server = Server.objects.filter(uuid=data["uuid"])[0]
                    else:
                        # server 不存在
                        server = Server.objects.create(**data)
                else:
                    Server.objects.filter(uuid=data["uuid"]).update(**data)
                    return JsonResponse({'code': 0, 'result': 'update server success'})
            else:
                # uuid 为空，则无法精确匹配到server，直接退出
                return JsonResponse({'code': 1, 'errmsg': 'uuid is null!'})

            # 重新绑定vmware存储
            if storage_info:
                Storage.objects.filter(server=server).delete()
                for k, v in storage_info.items():
                    Storage.objects.create(server=server, name=k, total=v[0], free=v[1], used_pct=v[2])

            # 录入资源使用率
            ServerResource.objects.create(s=server, cpu_used=data['cpu_used'], mem_used=data['mem_used'])

            # 重新绑定该服务器 和 应用
            tomcat_ports = [int(p) for p in tomcat_ports]

            if re.match(r'^jf-prod-|^jf-pre-', data['hostname'], re.I):
                tomcat_ports_last = [a.tomcat_port for a in server.app.all()]
                tomcat_ports_pre = [a.tomcat_port for a in server.pre_app.all()]
                # 之前存在，这次不存在。说明该应用已下线
                yixiaxian = [port for port in tomcat_ports_last if port not in tomcat_ports]
                # 之前不存在，这次存在。说明该应用刚上线
                yufenpeishangxian, weifenpeishangxian = list(), list()
                for port in tomcat_ports:
                    if port not in tomcat_ports_last and port in tomcat_ports_pre:
                        yufenpeishangxian.append(port)
                    if port not in tomcat_ports_last and port not in tomcat_ports_pre:
                        weifenpeishangxian.append(port)
                if yixiaxian or yufenpeishangxian or weifenpeishangxian:
                    msg = """应用变动告警：{}\n下线：{}\n预分配应用上线：{}\n未预分配应用上线：{}\n未录入端口：{}""".format(
                        server.hostname,
                        " ".join(
                            [str(a.tomcat_port) + "-" + a.app_code for a in
                             App.objects.filter(tomcat_port__in=yixiaxian)]),
                        " ".join(
                            [str(a.tomcat_port) + "-" + a.app_code for a in
                             App.objects.filter(tomcat_port__in=yufenpeishangxian)]),
                        " ".join(
                            [str(a.tomcat_port) + "-" + a.app_code for a in
                             App.objects.filter(tomcat_port__in=weifenpeishangxian)]),
                        " ".join(
                            [str(p) for p in tomcat_ports if not App.objects.filter(tomcat_port=p).exists()])
                    )
                    send_msg_to_admin(msg)

            server.app.set(App.objects.filter(tomcat_port__in=tomcat_ports))
            for app in App.objects.filter(tomcat_port__in=tomcat_ports):
                server.pre_app.remove(app)

            if re.match(r'^(JF|wry)-prod-(?!beta)', data['hostname'], re.I):
                server.app_env = 'prod'
            elif re.match(r'^(JF|wry)-prod-beta-', data['hostname'], re.I):
                server.app_env = 'beta'
            elif re.match(r'^(JF|wry)-pre-', data['hostname'], re.I):
                server.app_env = 'pre'
            elif re.match(r'^mdc-|wry-stable-', data['hostname'], re.I):
                server.app_env = 'test'
            else:
                server.app_env = 'unknown'

            if re.search(r'-it\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='it')
            elif re.search(r'-yunwei\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='yunwei')
            elif re.search(r'-bigdata\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='bigdata')
            elif re.search(r'-zhifu\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='zhifu')
            elif re.search(r'-zichan\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='zichan')
            elif re.search(r'-zhongjianjian\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='zhongjianjian')
            elif re.search(r'-zijin\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='zijin')
            idc = None
            if nic_mac_ip_dict:
                # 取出nic表所有该 server 的记录，下面会将该server 不存在的nic 删除。
                last_nic_ids = [n.id for n in Nic.objects.filter(server=server)]

                """
                data = {
                    ["mac1"]:[
                        {"eth0": [ip1, ip2]},
                        {"eth0.1": [ip3]}
                        ],
                    ["mac2"]:...,
                }
                """
                print(type(nic_mac_ip_dict), nic_mac_ip_dict)
                ip_total = list()
                for (mac, nic_ips_list) in nic_mac_ip_dict.items():
                    print(type(nic_ips_list), nic_ips_list)
                    for nic_ips in nic_ips_list:
                        for (nic, ips) in nic_ips.items():
                            print(mac, nic, ips, type(ips))

                            if nic == mac:
                                # vmware host
                                if Nic.objects.filter(nic_name=mac).exists():
                                    # vmware host
                                    nic = Nic.objects.get(nic_name=mac)
                                    last_nic_ids.remove(nic.id) if nic.id in last_nic_ids else None
                                else:
                                    nic_data = {'nic_name': nic, 'mac_address': mac,
                                                'server': server, 'date_last_checked': datetime.datetime.now()}
                                    nic = Nic.objects.create(**nic_data)
                            else:
                                # 网卡处理，先解绑该网卡绑定的所有ip。然后再给该网卡绑定 本次扫描到的ip。
                                nic_query = Nic.objects.filter(nic_name=nic, mac_address=mac.lower().replace('-', ':'))
                                if nic_query.exists():
                                    # 网卡已存在，则更新其 nic_name和server
                                    nic_query.update(**{'server': server, 'date_last_checked': datetime.datetime.now()})
                                    nic = nic_query[0]
                                    last_nic_ids.remove(nic.id) if nic.id in last_nic_ids else None
                                else:
                                    # 根据mac查不到网卡，则创建网卡记录，并绑定server
                                    nic_data = {'nic_name': nic, 'mac_address': mac.lower().replace('-', ':'),
                                                'server': server, 'date_last_checked': datetime.datetime.now()}
                                    nic = Nic.objects.create(**nic_data)

                            # ip 处理
                            for ip in ips:
                                ip_total.append(ip)
                                ip_query = Ip.objects.filter(ip=ip)
                                if ip_query:
                                    ip = ip_query[0]
                                    idc = ip.segment.vlan.idc
                                    # IP已存在，则更新last_detected 最后一次检测到的时间
                                    ip_query.update(**{'last_detected': datetime.datetime.now()})
                                    # 删除nic表中该ip的记录，下面会重新创建绑定
                                    for n in Nic.objects.filter(ip=ip):
                                        n.ip.remove(ip)
                                else:
                                    # IP 不存在，则新建
                                    seg = get_segment_by_ip(ip)
                                    ip = get_or_create_ip_obj(seg.vlan.idc.idc_name, seg.vlan.vlan_num, ip, seg.netmask)
                                    idc = seg.vlan.idc
                                if isinstance(ip, Ip):
                                    # 重新绑定nic和ip
                                    nic.ip.add(ip)

                if len(ip_total) == 1:
                    if not server.login_address or server.login_address == '127.0.0.1:22':
                        server.login_address = ip_total[0]
                    elif re.match(r'^\d{,3}\.\d{,3}\.\d{,3}\.\d{,3}$', server.login_address):
                        server.login_address = server.login_address + ':22'
                    elif not re.match(r'\d{,3}\.\d{,3}\.\d{,3}\.\d{,3}:\d{,5}', server.login_address):
                        send_msg_to_admin(
                            'Login_address error: {} {}!'.format(server.hostname, server.login_address))

                # 在脚本取到网卡的前提下，上一次记录last_nic_ids，这次还未重新绑定的，表示它不再与server 有关联，需删除该条垃圾数据
                if last_nic_ids and nic_mac_ip_dict:
                    Nic.objects.filter(id__in=last_nic_ids).delete()
            if idc:
                # 根据ip推出主机所在的机房
                server.idc = idc
            server.save()
            return JsonResponse({'code': 0, 'result': 'create server  success'})
        except Exception as e:
            print(traceback.print_exc())
            return JsonResponse({'code': 1, 'errmsg': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class CmdbAgentAPIView(JSONResponseMixin, RPCIpWhiteMixin, View):
    url_name = 'api-cmdb-agent'

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode('utf-8'))
        try:
            print(data)
            if "release_date" in data:
                release_date = data.pop("release_date")
                if re.search(r'(\d\d/\d\d/\d\d\d\d)$', release_date, re.I):
                    # 12/14/2018
                    release_date = re.findall(r'(\d\d/\d\d/\d\d\d\d)$', release_date, re.I)[0]
                    data["release_date"] = datetime.datetime.strptime(release_date, "%m/%d/%Y").strftime("%Y-%m-%d")
                elif re.search(r'(\d\d\d\d\d\d\d\d)$', release_date, re.I):
                    # 20181214
                    data["release_date"] = datetime.datetime.strptime(release_date, "%Y%m%d").strftime("%Y-%m-%d")
                elif release_date:
                    # 2018-12-14
                    data["release_date"] = release_date
            if "disk" in data:
                data["disk"] = "\n".join(data.pop("disk"))
            if "nic_mac_ip" in data:
                nic_mac_ip_dict = data.pop("nic_mac_ip")
                if isinstance(nic_mac_ip_dict, str):
                    nic_mac_ip_dict = json.loads(nic_mac_ip_dict)
            else:
                nic_mac_ip_dict = {}
            if "time" in data:
                send_msg_to_admin("还在跑老cmdb_agent脚本:" + data.get('hostname') + ' sn:' + data.get('sn'))
                data["date_last_checked"] = data.pop("time")
            if "tomcat_dirs" in data:
                data.pop("tomcat_dirs")
            if "tomcat" in data:
                tomcat_info = data.pop("tomcat")
            else:
                tomcat_info = list()
            if "vendor" in data:
                data["manufacturer"] = data.pop("vendor")
            # data['is_vm'] = False
            if "manage_address" in data:
                seg = get_segment_by_ip(data['manage_address'])
                if seg:
                    get_or_create_ip_obj(seg.vlan.idc.idc_name, seg.vlan.vlan_num, data['manage_address'])
            if "product_name" in data:
                if re.search(r'OpenStack|KVM|Virtual', data['product_name'], re.I):
                    data['is_vm'] = True
                else:
                    data['is_vm'] = False
            if "uuid" in data:
                if "vm_uuid" in data:
                    # {"vm_uuid": vm_uuid, "uuid": uuid}
                    parent_host = Server.objects.get(uuid=data['uuid'])
                    Server.objects.filter(uuid=data["vm_uuid"]).update(**{'parent_id': parent_host.id})
                    return JsonResponse({'code': 0, 'result': 'update server success'})

                if data["uuid"] == "":
                    if "hostname" in data:
                        server_query = Server.objects.filter(hostname=data["hostname"])
                        if server_query.count() == 1:
                            server_query.update(**data)
                            server = Server.objects.get(hostname=data["hostname"])
                        else:
                            return JsonResponse({'code': 1, 'errmsg': 'hostname：{}  不唯一!'.format(data["hostname"])})
                    else:
                        return JsonResponse({'code': 1, 'errmsg': 'uuid和hostname都为空!'})
                else:
                    server_query = Server.objects.filter(uuid=data["uuid"])
                    if server_query.count() == 0:
                        # server 不存在，则新建
                        server = Server.objects.create(**data)
                    elif server_query.count() == 1:
                        server_query.update(**data)
                        server = Server.objects.get(uuid=data["uuid"])
                    else:
                        # server uuid重复
                        return JsonResponse({'code': 1, 'errmsg': 'uuid：{} 不唯一!'.format(data["uuid"])})
            else:
                # 无 uuid，直接退出
                return JsonResponse({'code': 1, 'errmsg': 'uuid is null!'})

            # 录入资源使用率
            ServerResource.objects.create(s=server, cpu_used=data['cpu_used'], mem_used=data['mem_used'])

            tomcat_dir_prod = ['{}-{}'.format(str(a.tomcat_port), a.app_code.lower()) for a in server.app.all()]
            tomcat_dir_pre = ['{}-{}'.format(str(a.tomcat_port), a.app_code.lower()) for a in server.pre_app.all()]
            tomcat_dir_now = ['{}-{}'.format(str(t[0]), t[1].lower()) for t in tomcat_info]
            # 重新绑定该服务器 和 应用
            app_ids, unknown_app = list(), list()
            for t in tomcat_info:
                tomcat_port, app_code, jdk = t[0], t[1], t[2]
                app = App.objects.filter(tomcat_port=tomcat_port, app_code=app_code)
                if app:
                    if jdk != "" and jdk != app[0].jdk:
                        app.update(jdk=jdk)
                    app_ids.append(app[0].id)

                    if len(t) > 3:
                        xms = re.findall(r'xms(\d+\w)', t[3], re.I)[0]
                        xmx = re.findall(r'xmx(\d+\w)', t[3], re.I)[0]
                        AppResource.objects.update_or_create(s=server, app=app[0],
                                                             defaults={'xms': xms, 'xmx': xmx})
                else:
                    unknown_app.append("{}-{}".format(tomcat_port, app_code))
            server.app.set(App.objects.filter(id__in=app_ids))
            for app in App.objects.filter(id__in=app_ids):
                server.pre_app.remove(app)

            if re.match(r'^jf-prod-|^jf-pre-', data['hostname'], re.I):
                # 之前存在，这次不存在。说明该应用已下线
                yixiaxian = [_dir for _dir in tomcat_dir_prod if _dir not in tomcat_dir_now]
                # 之前不存在，这次存在。说明该应用刚上线
                yufenpeishangxian, weifenpeishangxian = list(), list()
                for _dir in tomcat_dir_now:
                    if _dir not in tomcat_dir_prod and _dir in tomcat_dir_pre:
                        yufenpeishangxian.append(_dir)
                    if _dir not in tomcat_dir_prod and _dir not in tomcat_dir_pre:
                        weifenpeishangxian.append(_dir)
                if yixiaxian or yufenpeishangxian or weifenpeishangxian:
                    msg = """应用变动告警：{}\n下线：{}\n预分配应用上线：{}\n未预分配应用上线：{}\n未知应用：{}""".format(
                        server.hostname,
                        " ".join(yixiaxian),
                        " ".join(yufenpeishangxian),
                        " ".join(weifenpeishangxian),
                        " ".join(unknown_app)
                    )
                    send_msg_to_admin(msg)

            if re.match(r'^(JF|wry)-prod-(?!beta)', data['hostname'], re.I):
                server.app_env = 'prod'
            elif re.match(r'^(JF|wry)-prod-beta-', data['hostname'], re.I):
                server.app_env = 'beta'
            elif re.match(r'^(JF|wry)-pre-', data['hostname'], re.I):
                server.app_env = 'pre'
            elif re.match(r'^mdc-|wry-stable-', data['hostname'], re.I):
                server.app_env = 'test'
            else:
                server.app_env = 'unknown'

            if re.search(r'-it\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='it')
            elif re.search(r'-yunwei\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='yunwei')
            elif re.search(r'-bigdata\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='bigdata')
            elif re.search(r'-zhifu\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='zhifu')
            elif re.search(r'-zichan\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='zichan')
            elif re.search(r'-zhongjianjian\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='zhongjianjian')
            elif re.search(r'-zijin\d?', data['hostname'], re.I):
                server.department = BizMgtDept.objects.get(dept_code='zijin')
            idc = None
            if nic_mac_ip_dict:
                # 取出nic表所有该 server 的记录，下面会将该server 不存在的nic 删除。
                last_nic_ids = [n.id for n in Nic.objects.filter(server=server)]

                """
                data = {
                    ["mac1"]:[
                        {"eth0": [ip1, ip2]},
                        {"eth0.1": [ip3]}
                        ],
                    ["mac2"]:...,
                }
                """
                print(type(nic_mac_ip_dict), nic_mac_ip_dict)
                ip_total = list()
                for (mac, nic_ips_list) in nic_mac_ip_dict.items():
                    print(type(nic_ips_list), nic_ips_list)
                    for nic_ips in nic_ips_list:
                        for (nic, ips) in nic_ips.items():
                            print(mac, nic, ips, type(ips))
                            if mac == "00-00-00-00-00-00-00-E0" and not ips:
                                continue

                            if nic == mac:
                                # vmware host
                                if Nic.objects.filter(nic_name=mac).exists():
                                    # vmware host
                                    nic = Nic.objects.get(nic_name=mac)
                                    last_nic_ids.remove(nic.id) if nic.id in last_nic_ids else None
                                else:
                                    nic_data = {'nic_name': nic, 'mac_address': mac,
                                                'server': server, 'date_last_checked': datetime.datetime.now()}
                                    nic = Nic.objects.create(**nic_data)
                            else:
                                # 网卡处理，先解绑该网卡绑定的所有ip。然后再给该网卡绑定 本次扫描到的ip。
                                nic_query = Nic.objects.filter(nic_name=nic, mac_address=mac.lower().replace('-', ':'))
                                if nic_query.exists():
                                    # 网卡已存在，则更新其 nic_name和server
                                    nic_query.update(**{'server': server, 'date_last_checked': datetime.datetime.now()})
                                    nic = nic_query[0]
                                    last_nic_ids.remove(nic.id) if nic.id in last_nic_ids else None
                                else:
                                    # 根据mac查不到网卡，则创建网卡记录，并绑定server
                                    nic_data = {'nic_name': nic, 'mac_address': mac.lower().replace('-', ':'),
                                                'server': server, 'date_last_checked': datetime.datetime.now()}
                                    nic = Nic.objects.create(**nic_data)

                            # ip 处理
                            for ip in ips:
                                ip_query = Ip.objects.filter(ip=ip)
                                if ip_query:
                                    ip_total.append(ip)
                                    ip = ip_query[0]
                                    idc = ip.segment.vlan.idc
                                    # IP已存在，则更新last_detected 最后一次检测到的时间
                                    ip_query.update(**{'last_detected': datetime.datetime.now()})
                                    # 删除nic表中该ip的记录，下面会重新创建绑定
                                    for n in Nic.objects.filter(ip=ip):
                                        n.ip.remove(ip)
                                else:
                                    # IP 不存在，则新建
                                    seg = get_segment_by_ip(ip)
                                    if seg is None:
                                        continue
                                    ip = get_or_create_ip_obj(seg.vlan.idc.idc_name, seg.vlan.vlan_num, ip, seg.netmask)
                                    idc = seg.vlan.idc
                                if isinstance(ip, Ip):
                                    # 重新绑定nic和ip
                                    nic.ip.add(ip)

                if len(ip_total) == 1:
                    if not server.login_address or server.login_address == '127.0.0.1:22':
                        server.login_address = ip_total[0]
                    elif re.match(r'^\d{,3}\.\d{,3}\.\d{,3}\.\d{,3}$', server.login_address):
                        server.login_address = server.login_address + ':22'
                    elif not re.match(r'\d{,3}\.\d{,3}\.\d{,3}\.\d{,3}:\d{,5}', server.login_address):
                        send_msg_to_admin('Login_address error: {} {}!'.format(server.hostname, server.login_address))

                # 在脚本取到网卡的前提下，上一次记录last_nic_ids，这次还未重新绑定的，表示它不再与server 有关联，需删除该条垃圾数据
                if last_nic_ids and nic_mac_ip_dict:
                    Nic.objects.filter(id__in=last_nic_ids).delete()
            if idc:
                # 根据ip推出主机所在的机房
                server.idc = idc
            server.save()
            return JsonResponse({'code': 0, 'result': 'create server success'})
        except Exception as e:
            print(traceback.print_exc())
            return JsonResponse({'code': 1, 'errmsg': str(e)})


class ServerPreAppAPIView(PermissionRequiredMixin, JSONResponseMixin, View):
    permission_required = 'auth.perm_cmdb_business_edit'

    def post(self, request, *args, **kwargs):
        # 更新主机的预分配应用
        try:
            server_id = kwargs.get('id')
            app_list = request.POST.getlist('pre_app')
            server = Server.objects.get(id=server_id)
            for app in App.objects.filter(app_code__in=app_list):
                server.pre_app.remove(app)
            return self.render_json_response({'code': 0, 'result': "所选应用已移除！"})
        except Exception as e:
            return self.render_json_response({'code': 1, 'errmsg': str(e)})


@method_decorator(csrf_exempt, name='dispatch')
class PodListAPIView(JSONResponseMixin, RPCIpWhiteMixin, View):
    url_name = 'api-pod-list'

    def post(self, request, **kwargs):
        try:
            #
            post_data = json.loads(request.body)
            app_code = post_data.pop('app_name')
            app = App.objects.get(app_code=app_code)
            ip = post_data.pop('ip')
            seg = get_segment_by_ip(ip, '255.255.252.0')
            ip = get_or_create_ip_obj(seg.vlan.idc.idc_name, seg.vlan.vlan_num, ip, '255.255.252.0')
            node_name = post_data.pop('node_name')
            node = Server.objects.get(hostname=node_name)
            post_data['parent_id'] = node.id
            post_data['is_vm'] = True
            post_data['idc'] = node.idc
            post_data['status'] = 'running'
            post_data['department'] = node.department
            post_data['comment'] = 'pod'
            node.pre_app.remove(app)

            if re.match(r'^mdc-|wry-stable-', node_name, re.I):
                post_data['app_env'] = 'test'

            # 新建或更新 K8s Pod，绑定ip 和 app
            if Server.objects.filter(hostname=post_data['hostname']).exists():
                Server.objects.filter(hostname=post_data['hostname']).update(**post_data)
                pod = Server.objects.get(hostname=post_data['hostname'])
            else:
                pod = Server.objects.create(**post_data)

            nic, _ = Nic.objects.update_or_create(
                nic_name=pod.hostname, mac_address=pod.hostname,
                defaults={'server': pod, 'date_last_checked': datetime.datetime.now()}
            )
            nic.ip.add(ip)
            pod.app.clear()
            pod.app.add(app)
            res = {'code': 0, 'result': '成功！'}
        except Server.DoesNotExist:
            res = {'code': 1, 'errmsg': 'Node未找到！'}
        except App.DoesNotExist:
            res = {'code': 1, 'errmsg': 'App未找到！'}
        return self.render_json_response(res)


@method_decorator(csrf_exempt, name='dispatch')
class NetDeviceListAPIView(JSONResponseMixin, RPCIpWhiteMixin, View):
    url_name = 'api-net-device-list'

    def post(self, request, **kwargs):
        try:
            post_data = json.loads(request.body)
            sys_name = post_data.get('sys_name')
            login_address = post_data.get('login_address')
            device = NetDevice.objects.filter(sys_name=sys_name)
            if device.exists():
                device = device[0]
            else:
                device = NetDevice.objects.create(**post_data)
            if Ip.objects.filter(ip=login_address).exists():
                ip = Ip.objects.get(ip=login_address)
            else:
                seg = get_segment_by_ip(login_address)
                ip = get_or_create_ip_obj(seg.vlan.idc.idc_name, seg.vlan.vlan_num, login_address)
            if not device.idc:
                device.idc = ip.segment.vlan.idc
                device.save(update_fields=['idc'])
            if ip not in device.ip.all():
                device.ip.add(ip)
            # device = NetDevice.objects.filter(login_address=login_address)
            # if device.exists():
            #     device = device[0]
            #     if Ip.objects.filter(ip=login_address).exists():
            #         ip = Ip.objects.get(ip=login_address)
            #         if ip not in device.ip.all():
            #             device.ip.add(ip)
            #     device.sys_name = sys_name
            #     device.save(update_fields=['sys_name'])
            res = {'code': 0,
                   'result': 'Success: Automatic add ip:%s to NetDevice:%s!' % (login_address, device.sys_name)}
        except Exception as e:
            res = {'code': 1, 'errmsg': 'Failed: /cmdb/v1/net_device_list/\n' + str(e)}
        send_msg_to_admin(json.dumps(res))
        return self.render_json_response(res)


class ServerCountView(JSONResponseMixin, View):

    def get(self, request, **kwargs):
        _filter = request.GET.get("filter")
        if _filter == "idc":
            not_known_count = Server.objects.filter(idc=None).exclude(status__in=['deleted', 'ots']).count()
            if not_known_count > 0:
                idc_name_list = ['其他']
                server_counts_list = [not_known_count]
            else:
                idc_name_list, server_counts_list = list(), list()
            for idc in IDC.objects.all():
                idc_name_list.append(idc.idc_name)
                server_counts_list.append(Server.objects.filter(idc=idc).exclude(status__in=['deleted', 'ots']).count())
            data = {
                'idc_name': idc_name_list,
                'server_counts': server_counts_list
            }
        elif _filter == "app_env":
            app_env_list = list()
            server_counts_list = list()
            for k, v in AppEnv.items():
                if k == "unknown":
                    continue
                app_env_list.append(v)
                server_counts_list.append(Server.objects.filter(app_env=k).exclude(status__in=['deleted', 'ots']).count())
            data = {
                'app_env': app_env_list,
                'server_counts': server_counts_list
            }
        elif _filter == "os":
            os_list = ['其他', 'Windows', 'Linux', 'VMware']
            server_counts_list = [Server.objects.filter(os=None).exclude(status__in=['deleted', 'ots']).count()]
            for _os in os_list[1:]:
                if _os == 'Linux':
                    server_counts_list.append(
                        Server.objects.filter(os__iregex='Linux|centos').exclude(status__in=['deleted', 'ots']).count())
                else:
                    server_counts_list.append(
                        Server.objects.filter(os__iregex=_os).exclude(status__in=['deleted', 'ots']).count())
            data = {
                'os': os_list,
                'server_counts': server_counts_list
            }
        elif _filter == "manufacturer":
            manufacturer_list = ['其他', 'Dell', 'Huawei', 'Inspur']
            server_counts_list = [Server.objects.filter(manufacturer=None).exclude(status__in=['deleted', 'ots']).count()]
            for manufacturer in manufacturer_list[1:]:
                server_counts_list.append(
                        Server.objects.filter(manufacturer__iregex=manufacturer).exclude(status__in=['deleted', 'ots']).count())
            data = {
                'manufacturer': manufacturer_list,
                'server_counts': server_counts_list
            }
        else:
            # 默认按部门分
            res = dict()
            dept_name_list = list()
            for k, v in AppEnv.items():
                if k == "unknown":
                    continue
                res[v] = list()

                for dept in BizMgtDept.objects.filter(parent_id=2):
                    if dept.dept_name not in dept_name_list:
                        dept_name_list.append(dept.dept_name)
                    dept_id_list = get_total_dept_child_node_id(dept.id)
                    res[v].append(
                        Server.objects.filter(
                            app_env=k, department_id__in=dept_id_list).exclude(status__in=['deleted', 'ots']).count())
            data = {
                'dept_name': dept_name_list,
                'counts_detail': res
            }
        return self.render_json_response(data)


class ServerHistoryCountView(JSONResponseMixin, View):

    def get(self, request, **kwargs):
        # 返回近半年服务器数量变化
        _filter = request.GET.get("filter")
        if _filter == "idc":
            data = {}
        elif _filter == "app_env":
            data = {}
        else:
            # 默认按部门分
            history = dict()
            date_time_list = list()
            for i in range(6):
                date_time_list.insert(0, '%s月' % (datetime.datetime.now() - relativedelta(months=i)).month)
            for dept in BizMgtDept.objects.filter(parent_id=2):
                dept_id_list = get_total_dept_child_node_id(dept.id)
                counts = []
                for i in range(6):
                    _date = (datetime.datetime.now() - relativedelta(months=i - 1)).strftime("%Y-%m-01")
                    _counts = Server.objects.filter(department_id__in=dept_id_list, date_created__lte=_date).count()
                    _del_counts = Server.objects.filter(department_id__in=dept_id_list,
                                                        status__in=['deleted', 'ots'],
                                                        date_last_checked__lte=_date).count()
                    counts.insert(0, _counts - _del_counts)
                history[dept.dept_name] = counts
            data = {
                'date_time_list': date_time_list,
                'history': history
            }
        return self.render_json_response(data)


class ServerResUsageView(JSONResponseMixin, View):

    def get(self, request, **kwargs):
        res = dict()
        cpu_used_list = list()
        mem_used_list = list()
        date_time_list = list()
        item = request.GET.get("item", 'memory')
        server_id = request.GET.get("server_id")
        dept_name = request.GET.get("dept_name")
        if server_id:
            s = Server.objects.get(id=server_id)
            for sr in ServerResource.objects.filter(s=s).order_by('-id')[:5]:
                cpu_used_list.insert(0, sr.cpu_used)
                mem_used_list.insert(0, sr.mem_used)
                date_time_list.insert(0, sr.created_date)
            res.update({
                'id': s.id,
                'hostname': s.hostname,
                'ip': s.login_address if s.login_address else "",
                'cpu_used': cpu_used_list,
                'memory_used': mem_used_list,
                'date_time': date_time_list
            })
        else:
            # 获取资源使用率占比
            if item == 'memory':
                if dept_name:
                    dept = BizMgtDept.objects.get(dept_name=dept_name, parent_id=2)
                    dept_id_list = get_total_dept_child_node_id(dept.id)
                    for i in range(10):
                        mem_used_list.append(Server.objects.filter(department_id__in=dept_id_list,
                                                                   mem_used__gte=10 * i,
                                                                   mem_used__lt=10 * (i + 1)).count())
                else:
                    for i in range(10):
                        mem_used_list.append(Server.objects.filter(mem_used__gte=10 * i,
                                                                   mem_used__lt=10 * (i + 1)).count())
                res['memory_used'] = mem_used_list
        return self.render_json_response(res)

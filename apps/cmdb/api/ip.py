# -*- coding: utf-8 -*-
import json
import traceback
import datetime
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from IPy import IP
from cmdb.models.base import IDC, VLan, NetworkSegment, Ip
from cmdb.models.asset import Server, NetDevice, Nic
from common.mixins import JSONResponseMixin
from common.utils.base import send_msg_to_admin


def get_or_create_ip_obj(idc, vlan, ip, netmask='255.255.255.0'):
    print(idc, vlan, ip)
    try:
        if IDC.objects.filter(idc_name=idc).exists():
            idc = IDC.objects.get(idc_name=idc)
            ipy = IP(ip).make_net(netmask)
            if vlan is not None:
                segment = NetworkSegment.objects.filter(vlan__vlan_num=vlan, segment=str(ipy.net()))
            else:
                vlan_list = [vlan for vlan in idc.vlan_set.all()]
                segment = NetworkSegment.objects.filter(vlan__in=vlan_list, segment=str(ipy.net()))

            if segment:
                if Ip.objects.filter(ip=ip, segment=segment[0]).exists():
                    return Ip.objects.get(ip=ip, segment=segment[0])
                return Ip.objects.create(ip=ip, segment=segment[0])
            else:
                send_msg_to_admin("Create Ip Instance Failed:{} {} {}\n无法找到该ip对应的网段！".format(idc, vlan, ip))
        else:
            send_msg_to_admin("Create Ip Instance Failed:{} {} {}\n无法找到该IDC！".format(idc, vlan, ip))
    except Exception as e:
        traceback.print_exc()
        send_msg_to_admin("Create Ip Instance Failed:{} {} {}\n{}".format(idc, vlan, ip, str(e)))
    return None


def get_segment_by_ip(ip, netmask='255.255.255.0'):
    ipy = IP(ip).make_net(netmask)
    segment = NetworkSegment.objects.filter(segment=str(ipy.net()))
    if segment:
        return segment[0]
    else:
        ipy = IP(ip).make_net("255.255.252.0")
        segment = NetworkSegment.objects.filter(segment=str(ipy.net()))
        if segment:
            return segment[0]
        else:
            print('%s 无法找到该ip对应的网段！' % ip)
            return None


def get_mac_by_ip(ip):
    if not isinstance(ip, Ip):
        ip = Ip.objects.get(ip=ip)
    nic = Nic.objects.filter(ip=ip)
    if nic:
        return nic[0].mac_address
    return None


class IpListAPIView(JSONResponseMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            result = list()
            for idc in IDC.objects.get_queryset():
                vlan_list = list()
                for vlan in VLan.objects.filter(idc=idc):
                    segment_list = list()
                    for segment in NetworkSegment.objects.filter(vlan=vlan):
                        ip_list = list()
                        for ip in Ip.objects.filter(segment=segment):
                            ip_list.append(ip.ip)
                        segment_list.append({"segment": segment.segment, "netmask": segment.netmask, "ip_list": ip_list})
                    vlan_list.append({"vlan": vlan.vlan_num, "segment_list": segment_list})
                result.append({"idc": idc.idc_name, "vlan_list": vlan_list})
            res = {'code': 0, 'result': result}
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
        return self.render_json_response(res)


@method_decorator(csrf_exempt, name='dispatch')
class IpCheckView(JSONResponseMixin, View):

    def post(self, request, *args, **kwargs):
        ip_mac_changed, ip_not_bonded, ip_not_exists = list(), list(), list()
        try:
            print(request.body)
            post_data = json.loads(request.body.decode("utf-8"))
            segment = "" if len(post_data) == 0 else str(IP(list(post_data.keys())[0]).make_net('255.255.255.0').net())
            for ip, mac in post_data.items():
                if Ip.objects.filter(ip=ip).exists():
                    Ip.objects.filter(ip=ip).update(last_detected=datetime.datetime.now())
                    if Nic.objects.filter(mac_address=mac.lower(), ip__ip=ip).exists():
                        pass
                    elif Server.objects.filter(manage_address=ip).exists():
                        pass
                    elif NetDevice.objects.filter(ip__ip=ip).exists():
                        pass
                    elif Nic.objects.filter(mac_address=mac.lower()).exists():
                        ip = Ip.objects.get(ip=ip)
                        Nic.objects.get(mac_address=mac.lower()).ip.add(ip)
                    else:
                        # 根据 mac_address 找不到网卡，ip 地址可以查到网卡，且该 网卡 绑定的网卡名和mac都是其 hostname
                        # 说明该网卡是esx采集脚本采集而来，server 是vmware 主机。所以，更新该网卡的mac_address为真正的mac地址
                        nic = Nic.objects.filter(ip__ip=ip)
                        if nic:
                            nic = nic[0]
                            if nic.nic_name == nic.mac_address == nic.server.hostname:
                                nic.mac_address = mac
                                nic.save(update_fields=['mac_address'])
                            else:
                                ip_mac_changed.append("{} {}".format(ip, mac))
                        else:
                            ip_not_bonded.append("{} {}".format(ip, mac))
                else:
                    ip_not_exists.append("{} {}".format(ip, mac))
            res = {'code': 0, 'result': '执行成功',
                   'ip_mac_changed': '%s' % ','.join(ip_mac_changed),
                   'ip_not_bonded': '%s' % ','.join(ip_not_bonded),
                   'ip_not_exists': '%s' % ','.join(ip_not_exists)}
            send_msg = "检测ip段：{0}/24\nip存在，mac不同：\n{1}\nip未绑定：\n{2}\nip不存在：\n{3}".format(
                segment, '\n'.join(ip_mac_changed), '\n'.join(ip_not_bonded), '\n'.join(ip_not_exists))
        except Exception as e:
            res = {'code': 1, 'errmsg': '执行出错：%s' % str(e)}
            send_msg = "/cmdb/v1/ip_check/ 执行出错：\n%s" % str(e)
        send_msg_to_admin(send_msg)
        return self.render_json_response(res)

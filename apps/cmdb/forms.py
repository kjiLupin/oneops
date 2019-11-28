# _*_ coding: utf-8 _*_

from django.forms import ModelForm
from cmdb.models.asset import Server, NetDevice
from cmdb.models.base import IDC, NetworkSegment, Cabinet, VLan, Ip
from cmdb.models.business import BizMgtDept, Process, App


class PhysicalServerForm(ModelForm):
    class Meta:
        model = Server
        fields = ['hostname', 'login_address', 'manage_address', 'trade_date', 'expired_date', 'supplier',
                  'supplier_phone', 'is_vm', 'sn', 'model', 'idc', 'cabinet', 'cabinet_pos', 'applicant', 'comment']


class VirtualServerForm(ModelForm):
    class Meta:
        model = Server
        fields = ['hostname', 'login_address', 'parent_id', 'is_vm', 'applicant']


class NetDeviceForm(ModelForm):
    class Meta:
        model = NetDevice
        fields = ['sys_name', 'login_type', 'login_address', 'snmp', 'type', 'manufacturer', 'os', 'product_name', 'model',
                  'version', 'idc', 'cabinet', 'cabinet_pos', 'supplier', 'supplier_phone', 'comment', 'status']


class IDCForm(ModelForm):
    class Meta:
        model = IDC
        fields = ['idc_name', 'address', 'phone', 'email', 'cabinet_num', 'comment']


class CabinetForm(ModelForm):
    class Meta:
        model = Cabinet
        fields = ['name', 'idc', 'power']


class VLanForm(ModelForm):
    class Meta:
        model = VLan
        fields = ['idc', 'vlan_num', 'comment']


class NetworkSegmentForm(ModelForm):
    class Meta:
        model = NetworkSegment
        fields = ['vlan', 'segment', 'netmask', 'comment']


class IpForm(ModelForm):
    class Meta:
        model = Ip
        fields = ['segment', 'ip', 'comment']


class BizMgtDeptForm(ModelForm):
    class Meta:
        model = BizMgtDept
        fields = ['dept_name', 'parent_id']


class ProcessForm(ModelForm):
    class Meta:
        model = Process
        fields = ['name', 'comment']


class AppForm(ModelForm):
    class Meta:
        model = App
        fields = ['app_code', 'app_name', 'app_type', 'scm_url', 'domain_name', 'importance', 'tomcat_port',
                  'primary', 'secondary', 'status', 'comment']

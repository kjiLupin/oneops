from django.contrib import admin

# Register your models here.
from cmdb.models.base import IDC, Cabinet, VLan, NetworkSegment, Ip, CDN, OSS
from cmdb.models.asset import Server, Pod, NetDevice, Storage, Nic
from cmdb.models.business import BizMgtDept, Process, App
from cmdb.models.accessory import CPU, Memory, Disk, Caddy, NetworkAdapter, NetworkCable, \
            OpticalTransceiver, JumpWire, Accessory, UseRecord, InventoryRecord


@admin.register(IDC)
class IDCAdmin(admin.ModelAdmin):
    list_display = ('id', 'idc_name', 'address', 'phone', 'email', 'cabinet_num', 'comment')
    search_fields = ['idc_name', 'address', 'comment']


@admin.register(VLan)
class VLanAdmin(admin.ModelAdmin):
    list_display = ('id', 'idc', 'vlan_num', 'comment')
    search_fields = ['vlan_num', 'comment']
    list_filter = ('idc',)


@admin.register(NetworkSegment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'vlan', 'segment', 'netmask', 'comment')
    search_fields = ['segment', 'comment']


@admin.register(Ip)
class IpAdmin(admin.ModelAdmin):
    list_display = ('id', 'ip', 'segment', 'comment')
    search_fields = ['ip', 'comment']
    list_filter = ('segment',)


@admin.register(CDN)
class CDNAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'account', 'secret', 'end_point', 'comment', 'is_active')
    search_fields = ['end_point', 'comment']


@admin.register(OSS)
class OSSAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'account', 'secret', 'end_point', 'container', 'comment', 'is_active')
    search_fields = ['end_point', 'container', 'comment']


@admin.register(Cabinet)
class CabinetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'idc', 'power')
    search_fields = ['name', 'idc']
    list_filter = ('idc',)


@admin.register(BizMgtDept)
class BizMgtDeptAdmin(admin.ModelAdmin):
    list_display = ('id', 'dept_name', 'dept_code', 'parent_id', 'comment')
    search_fields = ['dept_name', 'dept_code', 'comment']
    list_filter = ('parent_id',)


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'version_arg', 'comment', 'create_date')
    search_fields = ['name', 'comment']


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('id', 'app_code', 'app_name', 'biz_mgt_dept', 'primary', 'secondary', 'app_type', 'scm_url',
                    'tomcat_port', 'domain_name', 'domain_name_test', 'process', 'jdk', 'xms', 'xmx', 'comment',
                    'modify_date', 'parent_id')
    search_fields = ['app_code', 'app_name', 'primary', 'secondary', 'comment']
    list_filter = ('biz_mgt_dept', 'primary', 'secondary', 'process', 'parent_id',)


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'hostname', 'sn', 'uuid', 'cpu_total', 'cpu_used', 'mem_total', 'mem_used', 'disk', 'os'
                    , 'login_address', 'manage_address', 'manufacturer', 'product_name', 'release_date', 'trade_date'
                    , 'expired_date', 'supplier', 'supplier_phone', 'is_vm', 'vm_count', 'parent_id', 'model'
                    , 'idc', 'cabinet', 'cabinet_pos', 'applicant', 'status', 'app_env', 'date_created', 'date_last_checked')
    filter_horizontal = ('app',)
    search_fields = ['hostname', 'sn', 'uuid', 'login_address', 'manage_address', 'manufacturer', 'product_name', 'supplier',
                     'comment', 'applicant']
    list_filter = ('idc', 'manufacturer', 'supplier')


@admin.register(Pod)
class PodAdmin(admin.ModelAdmin):
    list_display = ('id', 'hostname', 'uuid', 'cpu', 'memory', 'parent_id', 'ip', 'app_env',
                    'status', 'date_created')
    filter_horizontal = ('app',)
    search_fields = ['hostname', 'ip', 'comment']
    list_filter = ('parent_id', 'status')


@admin.register(Nic)
class NicAdmin(admin.ModelAdmin):
    list_display = ('id', 'nic_name', 'mac_address', 'server')
    filter_horizontal = ('ip', )
    search_fields = ['nic_name', 'mac_address']


@admin.register(NetDevice)
class NetDeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'sys_name', 'login_type', 'login_address', 'snmp', 'type', 'manufacturer', 'os',
                    'product_name','model', 'version', 'cabinet', 'cabinet_pos', 'supplier', 'supplier_phone',
                    'comment', 'idc', 'status', 'date_created', 'date_last_checked')
    search_fields = ['sys_name', 'login_address', 'manufacturer', 'product_name', 'version', 'comment', 'supplier']
    list_filter = ('type', 'idc', 'manufacturer', 'supplier', 'status')
    filter_horizontal = ('ip',)


@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    list_display = ('id', 'server', 'name', 'total', 'free', 'used_pct', 'comment')
    search_fields = ['name', 'comment']


@admin.register(CPU)
class CPUAdmin(admin.ModelAdmin):
    list_display = ('id', 'version', 'speed', 'process', 'created_date')
    search_fields = ['version', 'speed']
    list_filter = ('version', 'speed', 'process')


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'ram_type', 'ram_size', 'speed', 'created_date')
    search_fields = ['ram_type', 'ram_size']
    list_filter = ('ram_type', 'ram_size', 'speed')


@admin.register(Disk)
class DiskAdmin(admin.ModelAdmin):
    list_display = ('id', 'device_type', 'capacity', 'rpm', 'dimensions', 'created_date')
    search_fields = ['capacity', 'dimensions']
    list_filter = ('device_type', 'capacity', 'rpm', 'dimensions')


@admin.register(Caddy)
class CaddyAdmin(admin.ModelAdmin):
    list_display = ('id', 'dimensions', 'created_date')
    search_fields = ['dimensions']
    list_filter = ('dimensions',)


@admin.register(NetworkAdapter)
class NetworkAdapterAdmin(admin.ModelAdmin):
    list_display = ('id', 'speed', 'created_date')
    search_fields = ['speed']
    list_filter = ('speed',)


@admin.register(NetworkCable)
class ReticuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'cat', 'length', 'created_date')
    search_fields = ['cat', 'length']
    list_filter = ('cat', 'length')


@admin.register(OpticalTransceiver)
class OpticalTransceiverAdmin(admin.ModelAdmin):
    list_display = ('id', 'information', 'mode', 'reach', 'rate', 'image', 'created_date')
    search_fields = ['information', 'reach', 'rate']
    list_filter = ('mode', 'rate', 'rate')


@admin.register(JumpWire)
class JumpWireAdmin(admin.ModelAdmin):
    list_display = ('id', 'information', 'mode', 'interface', 'length', 'image', 'created_date')
    search_fields = ['information', 'mode', 'interface', 'length']
    list_filter = ('mode', 'interface', 'length')


@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'storehouse', 'mode', 'mode_id', 'manufacturer', 'sn', 'vendor', 'trade_date',
                    'expired_date', 'comment', 'is_active', 'created_date')
    search_fields = ['mode', 'mode_id', 'vendor', 'comment']
    list_filter = ('storehouse', 'mode', 'mode_id', 'vendor', 'is_active', )


@admin.register(UseRecord)
class UseRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'accessory', 'server', 'net_device', 'created_date')
    search_fields = ['accessory', 'server', 'net_device']
    list_filter = ('accessory', )


@admin.register(InventoryRecord)
class InventoryRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'accessory', 'server', 'net_device', 'content', 'user', 'created_date')
    search_fields = ['accessory', 'content']
    list_filter = ('accessory', )

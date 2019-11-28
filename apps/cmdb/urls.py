# coding:utf-8
from django.urls import path, re_path
from cmdb.api.asset import CmdbAgentAPIView, PodListAPIView, ServerPreAppAPIView, NetDeviceListAPIView, \
        ServerCountView, ServerHistoryCountView, ServerResUsageView
from cmdb.api.department import BizMgtDeptAPIView
from cmdb.api.app import ProcessListAPIView, AppTemplateView, AppExportView, AppListAPIView, AppDetailAPIView,\
        AppPortDetailAPIView, AppGitDetailAPIView, AppPresortServerAPIView
from cmdb.api.segment import SegmentListAPIView
from cmdb.api.ip import IpListAPIView, IpCheckView
from cmdb.api.accessory import AccessoryResidualAPIView

from cmdb.views.charts import charts, charts_server
from cmdb.views.server import VirtualMachineView, PhysicalMachineView, AppServerView, ServerListView, \
        ServerDetailView, ServerTemplateView
from cmdb.views.net_device import NetDeviceView, NetDeviceListView, NetDeviceDetailView, NetDeviceTemplateView
from cmdb.views.maintenance import MaintenanceView, MaintenanceListView
from cmdb.views.idc import IDCView, IDCListView, IDCDetailView
from cmdb.views.business import BizDeptView, BizDeptListView, BizDeptDetailView, AppView, AppListView, AppDetailView, \
        AppAudit, AppAuditListView
from cmdb.views.cabinet import CabinetView, CabinetListView, CabinetDetailView
from cmdb.views.segment import SegmentView, SegmentListView, SegmentDetailView
from cmdb.views.vlan import VlanView, VLanListView, VlanDetailView
from cmdb.views.ip import IpListView, IpView, IpDetailView
from cmdb.views.accessory import AccessoryView, AccessoryListView, AccessoryTemplateView
from cmdb.views.inventory_record import InventoryRecordView, InventoryRecordListView
from cmdb.views.cpu import CPUView, CPUListView, CPUDetailView
from cmdb.views.memory import MemoryView, MemoryListView, MemoryDetailView
from cmdb.views.disk import DiskView, DiskListView, DiskDetailView
from cmdb.views.network_adapter import NetworkAdapterView, NetworkAdapterListView, NetworkAdapterDetailView
from cmdb.views.optical_transceiver import OpticalTransceiverView, OpticalTransceiverListView, \
        OpticalTransceiverDetailView
from cmdb.views.caddy import CaddyListView, CaddyDetailView
from cmdb.views.network_cable import NetworkCableListView, NetworkCableDetailView
from cmdb.views.jump_wire import JumpWireListView, JumpWireDetailView

app_name = 'cmdb'

# API
urlpatterns = [
        # /v1/server/
        re_path('(?P<version>[v1|v2]+)/cmdb_agent/', CmdbAgentAPIView.as_view(),
                name='api-cmdb-agent'),
        re_path('(?P<version>[v1|v2]+)/pod_list/', PodListAPIView.as_view(), name='api-pod-list'),
        re_path('(?P<version>[v1|v2]+)/net_device_list/', NetDeviceListAPIView.as_view(), name='api-net-device-list'),
        re_path('(?P<version>[v1|v2]+)/server_count/', ServerCountView.as_view(), name='api-server-count'),
        re_path('(?P<version>[v1|v2]+)/server_history_count/', ServerHistoryCountView.as_view(),
                name='api-server-history-count'),
        re_path('(?P<version>[v1|v2]+)/server_res_usage/', ServerResUsageView.as_view(), name='api-server-res-usage'),
        re_path('(?P<version>[v1|v2]+)/server_pre_app/(?P<id>\d+)?/?$', ServerPreAppAPIView.as_view(),
                name='api-server-pre-app'),
        re_path('(?P<version>[v1|v2]+)/biz_dept_move/', BizMgtDeptAPIView.as_view(), name='api-biz-dept-move'),
        re_path('(?P<version>[v1|v2]+)/process/', ProcessListAPIView.as_view(), name='api-process-list'),
        re_path('(?P<version>[v1|v2]+)/app/', AppListAPIView.as_view(), name='api-app-list'),
        re_path('(?P<version>[v1|v2]+)/app_export/', AppExportView.as_view(), name='api-app-export'),
        re_path('(?P<version>[v1|v2]+)/app_detail/(?P<code>[0-9a-zA-Z\-_.]+)?/?$', AppDetailAPIView.as_view(),
                name='api-app-detail'),
        re_path('(?P<version>[v1|v2]+)/app_port_detail/(?P<port>\d+)?/?$', AppPortDetailAPIView.as_view(),
                name='api-app-port-detail'),
        re_path('(?P<version>[v1|v2]+)/app_git_detail/(?P<url>[0-9a-zA-Z\-@_.:/]+)?/?$', AppGitDetailAPIView.as_view(),
                name='api-app-git-detail'),
        re_path('(?P<version>[v1|v2]+)/app_presort_server/(?P<id>\d+)?/?$', AppPresortServerAPIView.as_view(),
                name='api-app-presort-server'),
        re_path('(?P<version>[v1|v2]+)/segment/', SegmentListAPIView.as_view(), name='api-segment-list'),
        re_path('(?P<version>[v1|v2]+)/ip/', IpListAPIView.as_view(), name='api-ip-list'),
        re_path('(?P<version>[v1|v2]+)/ip_check/', IpCheckView.as_view(), name='api-ip-check'),
        re_path('(?P<version>[v1|v2]+)/accessory/residual/', AccessoryResidualAPIView.as_view(), name='api-acc-residual'),
]

urlpatterns += [
        path('charts/', charts, name='charts'),
        path('charts/server/', charts_server, name='charts-server'),

        path('idc/', IDCView.as_view(), name='idc'),
        path('idc_list/', IDCListView.as_view(), name='idc-list'),
        re_path('idc_detail/(?P<pk>\d+)?/?$', IDCDetailView.as_view(), name='idc-detail'),
        path('cabinet/', CabinetView.as_view(), name='cabinet'),
        path('cabinet_list/', CabinetListView.as_view(), name='cabinet-list'),
        re_path('cabinet_detail/(?P<pk>\d+)?/?$', CabinetDetailView.as_view(), name="cabinet-detail"),

        path('vlan/', VlanView.as_view(), name='vlan'),
        path('vlan_list/', VLanListView.as_view(), name='vlan-list'),
        re_path('vlan_detail/(?P<pk>\d+)?/?$', VlanDetailView.as_view(), name="vlan-detail"),
        path('segment/', SegmentView.as_view(), name='segment'),
        path('segment_list/', SegmentListView.as_view(), name='segment-list'),
        re_path('segment_detail/(?P<pk>\d+)?/?$', SegmentDetailView.as_view(), name='segment-detail'),
        path('ip/', IpView.as_view(), name='ip'),
        path('ip_list/', IpListView.as_view(), name='ip-list'),
        re_path('ip_detail/(?P<pk>\d+)?/?$', IpDetailView.as_view(), name='ip-detail'),

        path('vm_list/', VirtualMachineView.as_view(), name='vm-list'),
        path('pm_list/', PhysicalMachineView.as_view(), name='pm-list'),
        path('app_server_list/', AppServerView.as_view(), name='app-server-list'),
        path('server_list/', ServerListView.as_view(), name="server-list"),
        re_path('server_detail/(?P<pk>\d+)?/?$', ServerDetailView.as_view(), name="server-detail"),
        path('server_template_export/', ServerTemplateView.as_view(), name='server-template-export'),
        path('server_template_import/', ServerTemplateView.as_view(), name='server-template-import'),
        path('maintenance/', MaintenanceView.as_view(), name='maintenance'),
        path('maintenance_list/', MaintenanceListView.as_view(), name='maintenance-list'),

        path('accessory/', AccessoryView.as_view(), name='accessory'),
        path('accessory_list/', AccessoryListView.as_view(), name='accessory-list'),
        path('accessory_export/', AccessoryTemplateView.as_view(), name='accessory-export'),
        path('accessory_import/', AccessoryTemplateView.as_view(), name='accessory-import'),
        path('inventory_record/', InventoryRecordView.as_view(), name='inventory-record'),
        path('inventory_record_list/', InventoryRecordListView.as_view(), name='inventory-record-list'),

        path('accessory/cpu/', CPUView.as_view(), name='cpu'),
        path('accessory/cpu_list/', CPUListView.as_view(), name='cpu-list'),
        re_path('accessory/cpu_detail/(?P<acc_id>\d+)?/?$', CPUDetailView.as_view(), name="cpu-detail"),
        path('accessory/memory/', MemoryView.as_view(), name='memory'),
        path('accessory/memory_list/', MemoryListView.as_view(), name='memory-list'),
        re_path('accessory/memory_detail/(?P<acc_id>\d+)?/?$', MemoryDetailView.as_view(), name="memory-detail"),
        path('accessory/disk/', DiskView.as_view(), name='disk'),
        path('accessory/disk_list/', DiskListView.as_view(), name='disk-list'),
        re_path('accessory/disk_detail/(?P<acc_id>\d+)?/?$', DiskDetailView.as_view(), name="disk-detail"),
        path('accessory/network_adapter/', NetworkAdapterView.as_view(), name='network-adapter'),
        path('accessory/network_adapter_list/', NetworkAdapterListView.as_view(), name='network-adapter-list'),
        re_path('accessory/network_adapter_detail/(?P<acc_id>\d+)?/?$', NetworkAdapterDetailView.as_view(),
                name="network-adapter-detail"),
        path('accessory/transceiver/', OpticalTransceiverView.as_view(), name='optical-transceiver'),
        path('accessory/transceiver_list/', OpticalTransceiverListView.as_view(), name='optical-transceiver-list'),
        re_path('accessory/transceiver_detail/(?P<acc_id>\d+)?/?$', OpticalTransceiverDetailView.as_view(),
                name="optical-transceiver-detail"),

        path('accessory/caddy_list/', CaddyListView.as_view(), name='caddy-list'),
        re_path('accessory/caddy_detail/(?P<pk>\d+)?/?$', CaddyDetailView.as_view(), name="caddy-detail"),
        path('accessory/network_cable_list/', NetworkCableListView.as_view(), name='network-cable-list'),
        re_path('accessory/network_cable_detail/(?P<pk>\d+)?/?$', NetworkCableDetailView.as_view(),
                name="network-cable-detail"),
        path('accessory/jump_wire_list/', JumpWireListView.as_view(), name='jump-wire-list'),
        re_path('accessory/jump_wire_detail/(?P<pk>\d+)?/?$', JumpWireDetailView.as_view(), name="jump-wire-detail"),

        path('network_device/', NetDeviceView.as_view(), name='network-device'),
        path('network_device_list/', NetDeviceListView.as_view(), name='network-device-list'),
        path('network_device_export/', NetDeviceTemplateView.as_view(), name='network-device-export'),
        path('network_device_import/', NetDeviceTemplateView.as_view(), name='network-device-import'),
        re_path('network_device_detail/(?P<pk>\d+)?/?$', NetDeviceDetailView.as_view(), name='network-device-detail'),

        path('biz_dept/', BizDeptView.as_view(), name='biz-dept'),
        path('biz_dept_list/', BizDeptListView.as_view(), name='biz-dept-list'),
        re_path('biz_dept_detail/(?P<pk>\d+)?/?$', BizDeptDetailView.as_view(), name='biz-dept-detail'),
        path('app/', AppView.as_view(), name='app'),
        re_path('app_list/', AppListView.as_view(), name='app-list'),
        re_path('app_detail/(?P<pk>\d+)?/?$', AppDetailView.as_view(), name='app-detail'),
        path('app_export/', AppTemplateView.as_view(), name='app-export'),
        path('app_import/', AppTemplateView.as_view(), name='app-import'),
        path('app_audit/', AppAudit.as_view(), name='app-audit'),
        path('app_audit_list/', AppAuditListView.as_view(), name='app-audit-list'),
]

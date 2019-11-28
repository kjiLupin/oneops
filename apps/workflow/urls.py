# coding:utf-8
from django.urls import path, re_path
from workflow.api.workflow import WorkflowInfoAPIView
from workflow.api.ali_cdn import SyncCSFileAPIView
from workflow.api.app import AnsibleHostsGroupInitAPIView, OpsProjectCreateAPIView, OpsRoleListAPIView, \
        AppOfflineCodeBackupAPIView, AppOfflineDisableMonitorAPIView

from workflow.views.workflow import DashboardView, WorkflowView, WorkflowListView, \
        WorkflowStepsListView, WorkflowStepsDetailView
from workflow.views.flow import FlowPendingView, FlowPendingListView, FlowTotalView, FlowTotalListView, \
        FlowOngoingView, FlowOngoingListView, FlowEndView, FlowEndListView
from workflow.views.ali_cdn import AliCDNView, AliCDNDetailView
from workflow.views.ali_oss import AliOSSView, AliOSSDetailView, AliOSSAPKView, AliOSSAPKDetailView
from workflow.views.azure_oss import AzureOSSAPKView, AzureOSSAPKDetailView
from workflow.views.app_apply import AppApplyView, AppApplyDetailView
from workflow.views.app_offline import AppOfflineView, AppOfflineDetailView
from workflow.views.tomcat import TomcatDumpView, TomcatDumpDetailView, TomcatProcessExplorerView, TomcatProcessExplorerDetailView
from workflow.views.network import CrossSegmentAccessView, CrossSegmentAccessDetailView

app_name = 'workflow'

# API
urlpatterns = [
        re_path('(?P<version>[v1|v2]+)/workflow_info/', WorkflowInfoAPIView.as_view(), name='api-wf-info'),
        re_path('(?P<version>[v1|v2]+)/sync_cs_file/', SyncCSFileAPIView.as_view(), name='api-sync-cs-file'),
        re_path('(?P<version>[v1|v2]+)/ansible_hosts_group_init/(?P<flow_id>\d+)?/?$',
                AnsibleHostsGroupInitAPIView.as_view(), name='api-ansible-hosts-group-init'),
        re_path('(?P<version>[v1|v2]+)/app_offline_code_backup/(?P<app_id>\d+)?/?$',
                AppOfflineCodeBackupAPIView.as_view(), name='api-app-offline-code-backup'),
        re_path('(?P<version>[v1|v2]+)/app_offline_disable_monitor/(?P<app_code>[0-9a-zA-Z\-_.]+)?/?$',
                AppOfflineDisableMonitorAPIView.as_view(), name='api-app-offline-disable-monitor'),
        re_path('(?P<version>[v1|v2]+)/ops_project_create/(?P<flow_id>\d+)?/?$',
                OpsProjectCreateAPIView.as_view(), name='api-ops-project-create'),
        re_path('(?P<version>[v1|v2]+)/ops_role_list/', OpsRoleListAPIView.as_view(), name='api-ops-role-list'),
]

urlpatterns += [
        path('dashboard/', DashboardView.as_view(), name='dashboard'),
        path('prod/', DashboardView.as_view(), name='prod'),
        path('test/', DashboardView.as_view(), name='test'),
        path('apply/', DashboardView.as_view(), name='apply'),
        path('ops/', DashboardView.as_view(), name='ops'),
        path('workflow/', WorkflowView.as_view(), name='workflow'),
        path('workflow_list/', WorkflowListView.as_view(), name='wf-list'),
        path('workflow_steps_list/', WorkflowStepsListView.as_view(), name='wf-steps-list'),
        re_path('workflow_steps_detail/(?P<wf_id>\d+)?/?$', WorkflowStepsDetailView.as_view(),
                name='wf-steps-detail'),
        path('flow_pending/', FlowPendingView.as_view(), name='pending'),
        path('flow_pending_list/', FlowPendingListView.as_view(), name='pending-list'),
        path('flow_total/', FlowTotalView.as_view(), name='total'),
        path('flow_total_list/', FlowTotalListView.as_view(), name='total-list'),
        path('flow_ongoing/', FlowOngoingView.as_view(), name='ongoing'),
        path('flow_ongoing_list/', FlowOngoingListView.as_view(), name='ongoing-list'),
        path('flow_end/', FlowEndView.as_view(), name='end'),
        path('flow_end_list/', FlowEndListView.as_view(), name='end-list'),
        path('flow/ali_cdn/', AliCDNView.as_view(), name='flow-ali-cdn'),
        re_path('flow/ali_cdn_detail/(?P<flow_id>\d+)?/?$', AliCDNDetailView.as_view(), name='flow-ali-cdn-detail'),
        path('flow/ali_oss/', AliOSSView.as_view(), name='flow-ali-oss'),
        re_path('flow/ali_oss_detail/(?P<flow_id>\d+)?/?$', AliOSSDetailView.as_view(), name='flow-ali-oss-detail'),
        path('flow/ali_oss_apk/', AliOSSAPKView.as_view(), name='flow-ali-oss-apk'),
        re_path('flow/ali_oss_apk_detail/(?P<flow_id>\d+)?/?$', AliOSSAPKDetailView.as_view(),
                name='flow-ali-oss-apk-detail'),
        path('flow/azure_oss_apk/', AzureOSSAPKView.as_view(), name='flow-azure-oss-apk'),
        re_path('flow/azure_oss_apk_detail/(?P<flow_id>\d+)?/?$', AzureOSSAPKDetailView.as_view(),
                name='flow-azure-oss-apk-detail'),
        path('flow/app_apply/', AppApplyView.as_view(), name='flow-app-apply'),
        re_path('flow/app_apply_detail/(?P<flow_id>\d+)?/?$', AppApplyDetailView.as_view(),
                name='flow-app-apply-detail'),
        path('flow/app_offline/', AppOfflineView.as_view(), name='flow-app-offline'),
        re_path('flow/app_offline_detail/(?P<flow_id>\d+)?/?$', AppOfflineDetailView.as_view(),
                name='flow-app-offline-detail'),
        path('flow/tomcat_dump/', TomcatDumpView.as_view(), name='flow-tomcat-dump'),
        re_path('flow/tomcat_dump_detail/(?P<flow_id>\d+)?/?$', TomcatDumpDetailView.as_view(),
                name='flow-tomcat-dump-detail'),
        path('flow/tomcat_jstack/', TomcatProcessExplorerView.as_view(), name='flow-tomcat-jstack'),
        re_path('flow/tomcat_jstack_detail/(?P<flow_id>\d+)?/?$', TomcatProcessExplorerDetailView.as_view(),
                name='flow-tomcat-jstack-detail'),
        path('flow/cross_segment_access/', CrossSegmentAccessView.as_view(), name='flow-cross-segment-access'),
        re_path('flow/cross_segment_access_detail/(?P<flow_id>\d+)?/?$', CrossSegmentAccessDetailView.as_view(),
                name='flow-cross-segment-access-detail'),
]

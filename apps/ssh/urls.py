# coding:utf-8
from django.urls import path, re_path

from ssh.views.charts import charts
from ssh.views.host_user import HostUserOverviewView, HostUserOverviewListView, HostUserView, HostUserListView, \
        HostUserDetailView, HostUserAssetDetailView
from ssh.views.perilous_cmd import PerilousCmdView, PerilousCmdListView, PerilousCmdDetailView
from ssh.views.perilous_cmd_group import PerilousCmdGroupView, PerilousCmdGroupListView, PerilousCmdGroupDetailView
from ssh.views.perilous_cmd_grant import PerilousCmdGrantView, PerilousCmdGrantListView, PerilousCmdGrantDetailView

app_name = 'ssh'

# API
urlpatterns = [
]

urlpatterns += [
        path('charts/', charts, name='charts'),
        path('host_user_overview/', HostUserOverviewView.as_view(), name='host-user-overview'),
        path('host_user_overview_list/', HostUserOverviewListView.as_view(), name='host-user-overview-list'),
        re_path('host_user/(?P<username>[0-9a-zA-Z\-]+)?/?$', HostUserView.as_view(), name='host-user'),
        re_path('host_user_list/(?P<username>[0-9a-zA-Z\-]+)?/?$', HostUserListView.as_view(), name='host-user-list'),
        re_path('host_user_detail/(?P<pk>\d+)?/?$', HostUserDetailView.as_view(),
                name="host-user-detail"),
        re_path('host_user_asset_detail/(?P<hu_id>\d+)?/?$', HostUserAssetDetailView.as_view(),
                name="host-user-asset-detail"),

        path('perilous_cmd/', PerilousCmdView.as_view(), name='perilous-cmd'),
        path('perilous_cmd_list/', PerilousCmdListView.as_view(), name='perilous-cmd-list'),
        re_path('perilous_cmd_detail/(?P<pk>\d+)?/?$', PerilousCmdDetailView.as_view(), name="perilous-cmd-detail"),

        path('perilous_cmd_group/', PerilousCmdGroupView.as_view(), name='perilous-cmd-group'),
        path('perilous_cmd_group_list/', PerilousCmdGroupListView.as_view(), name='perilous-cmd-group-list'),
        re_path('perilous_cmd_group_detail/(?P<pk>\d+)?/?$', PerilousCmdGroupDetailView.as_view(),
                name="perilous-cmd-group-detail"),

        path('perilous_cmd_grant/', PerilousCmdGrantView.as_view(), name='perilous-cmd-grant'),
        path('perilous_cmd_grant_list/', PerilousCmdGrantListView.as_view(), name='perilous-cmd-grant-list'),
        re_path('perilous_cmd_grant_detail/(?P<ug_id>\d+)?/?$', PerilousCmdGrantDetailView.as_view(),
                name="perilous-cmd-grant-detail"),
]

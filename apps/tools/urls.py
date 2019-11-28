# coding:utf-8
from django.urls import path, re_path
from tools.api.tomcat import TomcatAPIView
from tools.api.encryption import EncryptionAPIView
from tools.api.qizhi import QiZhiCreateHostAPIView

from tools.views.dashboard import dashboard
from tools.views.net_surfing import NetSurfingListView, NetSurfingDetailView, NetSurfingLogsView
from tools.views.tomcat import TomcatView
from tools.views.encryption import EncryptionView
from tools.views.qizhi import QiZhiCreateHostView

app_name = 'tools'

# API
urlpatterns = [
        re_path('(?P<version>[v1|v2]+)/tomcat/', TomcatAPIView.as_view(), name='api-tomcat'),
        re_path('(?P<version>[v1|v2]+)/encryption/', EncryptionAPIView.as_view(), name='api-encryption'),
        re_path('(?P<version>[v1|v2]+)/qizhi/create_host/', QiZhiCreateHostAPIView.as_view(),
                name='api-qizhi-create-host'),
]

urlpatterns += [
        path('dashboard/', dashboard, name='dashboard'),
        path('net-surfing-list/', NetSurfingListView.as_view(), name='net-surfing-list'),
        re_path('net-surfing-detail/(?P<pk>\d+)?/?$', NetSurfingDetailView.as_view(), name='net-surfing-detail'),
        path('net-surfing-logs/', NetSurfingLogsView.as_view(), name='net-surfing-logs'),
        path('tomcat/', TomcatView.as_view(), name='tomcat'),
        path('encryption', EncryptionView.as_view(), name='encryption'),
        path('qizhi/create_host', QiZhiCreateHostView.as_view(), name='qizhi-create-host')
]

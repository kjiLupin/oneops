# coding:utf-8
from django.urls import path, re_path
from dns_pod.api import RecordAPIView
from dns_pod.charts import charts
from dns_pod.views import zone, ZoneListView, ZoneDetailView, record, RecordListView, RecordDetailView, \
        DnsLogIndex, DnsLogList

app_name = 'dns'

# API
urlpatterns = [
        # /v1/env/record/
        re_path('(?P<version>[v1|v2]+)/(?P<env>[a-z]+)/record/', RecordAPIView.as_view(), name='api-record'),
]


urlpatterns += [
        path('charts/', charts, name='charts'),
        path('zone/', zone, name='zone'),
        path('zone_list/', ZoneListView.as_view(), name="zone-list"),
        re_path('zone_detail/(?P<pk>\d+)?/?$', ZoneDetailView.as_view(), name="zone-detail"),
        re_path('record/(?P<env>[0-9a-zA-Z]+)?/(?P<domain_name>[0-9a-zA-Z\-.]+)?/?$', record, name='record'),
        re_path('record_list/(?P<env>[0-9a-zA-Z]+)/(?P<domain_name>[0-9a-zA-Z\-.]+)?/?$',
                RecordListView.as_view(), name='record-list'),
        re_path('record_detail/(?P<env>[0-9a-zA-Z]+)/(?P<domain_name>[0-9a-zA-Z\-.]+)?/(?P<pk>\d+)?/?$',
                RecordDetailView.as_view(), name='record-detail'),
        path('dns_log/', DnsLogIndex.as_view(), name='dns-log'),
        path('dns_log_list/', DnsLogList.as_view(), name='dns-log-list'),
]

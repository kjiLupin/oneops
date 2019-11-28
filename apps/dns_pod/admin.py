# -*- coding: UTF-8 -*-
from django.contrib import admin

# Register your models here.
from dns_pod.models import Zone, Record


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('id', 'domain_name', 'type', 'comment', 'create_time')
    search_fields = ['domain_name', 'comment']
    list_filter = ('type',)


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'zone', 'host', 'type', 'data', 'status', 'ttl', 'mx_priority', 'priority', 'serial',
                    'refresh', 'retry', 'expire', 'minimum', 'resp_person', 'primary_ns', 'update_time', 'create_time')
    search_fields = ['zone', 'host', 'type', 'data']
    list_filter = ('zone', 'type', 'status',)

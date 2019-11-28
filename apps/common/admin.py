from django.contrib import admin
from common.models import RPCIpWhite


@admin.register(RPCIpWhite)
class RPCIpWhiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'url_name', 'ip_list', 'applicant', 'comment')
    search_fields = ['url_name', 'ip_list', 'applicant', 'comment']
    list_filter = ('url_name', 'applicant',)
    readonly_fields = ['url_name', ]

# _*_ coding: utf-8 _*_

from django.forms import ModelForm
from dns_pod.models import Zone, Record


class ZoneForm(ModelForm):
    class Meta:
        model = Zone
        fields = ['domain_name', 'type', 'comment']


class RecordForm(ModelForm):
    class Meta:
        model = Record
        fields = ['zone', 'host', 'type', 'data', 'ttl', 'status']

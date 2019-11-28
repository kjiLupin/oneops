
from rest_framework import serializers
from dns_pod.models import Zone, Record


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ('id', 'domain_name', 'type', 'comment')


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Record
        fields = ('id', 'zone', 'host', 'type', 'data', 'ttl', 'mx_priority', 'view')

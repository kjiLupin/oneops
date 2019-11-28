# -*- coding: utf-8 -*-
from rest_framework import serializers
from job.models.job import JobConfig


class JobConfigSerializer(serializers.Serializer):
    pk = serializers.IntegerField(read_only=True)
    title = serializers.CharField(required=False, allow_blank=True, max_length=100)
    code = serializers.CharField(style={'base_template': 'textarea.html'})
    linenos = serializers.BooleanField(required=False)

    def create(self, validated_data):
        """
        传入验证过的数据, 创建并返回`JobConfig`实例。
        """
        return JobConfig.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        传入验证过的数据, 更新并返回已有的`JobConfig`实例。
        """
        instance.title = validated_data.get('title', instance.title)
        instance.code = validated_data.get('code', instance.code)
        instance.linenos = validated_data.get('linenos', instance.linenos)
        instance.language = validated_data.get('language', instance.language)
        instance.style = validated_data.get('style', instance.style)
        instance.save()
        return instance

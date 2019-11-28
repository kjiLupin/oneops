# -*- coding: utf-8 -*-
from job.models.job import JobConfig


class MyJobConfig(object):
    def __init__(self):
        self.sys_config = {}
        try:
            # 获取系统配置信息
            all_config = JobConfig.objects.all().values('item', 'value')
            for items in all_config:
                self.sys_config[items['item']] = items['value'].strip()
        except Exception:
            pass

job_config = MyJobConfig().sys_config

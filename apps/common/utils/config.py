# -*- coding: utf-8 -*-
from common.models import Config


class SysConfig(object):
    def __init__(self):
        try:
            # 获取系统配置信息
            all_config = Config.objects.all().values('item', 'value')
            sys_config = {}
            for items in all_config:
                sys_config[items['item']] = items['value'].strip()
        except Exception:
            self.sys_config = {}
        else:
            self.sys_config = sys_config

sys_config = SysConfig().sys_config

#!/usr/bin/env python
# -*- coding: utf-8 -*-
from common.utils.redis_api import OPRedis
from job.utils.config import MyJobConfig

job_config = MyJobConfig().sys_config
# 公用一个Redis连接池
ansible_redis = job_config.get('ansible_redis', '')
ansible_redis_pwd = job_config.get('ansible_redis_pwd', '')
AnsibleRedisPool = OPRedis(ansible_redis, ansible_redis_pwd)

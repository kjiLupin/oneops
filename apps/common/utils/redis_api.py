#!/usr/bin/env python
# -*- coding: utf-8 -*-
import redis


class OPRedis(object):

    def __init__(self, uri, password):
        self.url = 'redis://:{}@{}'.format(password, uri)
        self.con = redis.Redis.from_url(self.url, decode_responses=True)

    def expire(self, key, expires=86400):
        res = self.con.expire(key, expires)
        return res

    """
    string类型 {'key':'value'} redis操作
    """
    def set_redis(self, key, value, expires=None):
        # 非空即真，非0即真
        if expires is not None:
            res = self.con.setex(key, value, expires)
        else:
            res = self.con.set(key, value)
        return res

    def get_redis(self, key):
        res = self.con.get(key).decode()
        return res

    def del_redis(self, key):
        res = self.con.delete(key)
        return res

    """
    hash类型，{'name':{'key':'value'}} redis操作
    """
    def set_hash_redis(self, name, key, value):
        res = self.con.hset(name, key, value)
        return res

    def get_hash_redis(self, name, key=None):
        # 判断key是否我为空，不为空，获取指定name内的某个key的value; 为空则获取name对应的所有value
        if key:
            res = self.con.hget(name, key)
        else:
            res = self.con.hgetall(name)
        return res

    def del_hash_redis(self, name, key=None):
        if key:
            res = self.con.hdel(name, key)
        else:
            res = self.con.delete(name)
        return res

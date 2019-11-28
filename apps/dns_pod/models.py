# -*- coding: UTF-8 -*-
import datetime
from django.db import models
from accounts.models import User
# Create your models here.


class Zone(models.Model):
    domain_name = models.CharField('域名', max_length=100)
    type = models.CharField('域名类型', max_length=5, choices=(('prod', '正式'), ('beta', 'Beta'), ('pre', '预发'),
                                                            ('test', '测试'), ('dev', '开发')))
    create_time = models.DateTimeField(auto_now_add=True)
    comment = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return '{}: {}'.format(self.type, self.domain_name)

    class Meta:
        db_table = 'dns_zone'
        ordering = ('create_time',)
        unique_together = (('domain_name', 'type'),)
        verbose_name = u'域名表'
        verbose_name_plural = u'域名表'

Types = {
    'A': 'A', 'MX': 'MX', 'CNAME': 'CNAME',
    'NS': 'NS', 'SOA': 'SOA', 'PTR': 'PTR',
    'TXT': 'TXT', 'AAAA': 'AAAA', 'SVR': 'SVR', 'URL': 'URL'
}

Record_Status = {
    'enable': 'enable',
    'disabled': 'disabled'
}


#
class MyRecordQuerySet(models.QuerySet):

    def update(self, *args, **kwargs):
        # 重写update方法，每一次更新record，serial都增加1。
        # print(kwargs)
        if 'zone' in kwargs and 'host' in kwargs and 'type' in kwargs and 'data' in kwargs:
            kwargs['title'] = '{}-{}-{}-{}'.format(kwargs['zone'], kwargs['host'], kwargs['type'], kwargs['data'])
        super(MyRecordQuerySet, self).update(*args, **kwargs)

    def height_priority(self):
        # Record.objects.all().height_priority()
        return self.filter(priority__gte=10)


class RecordManager(models.Manager):
    def get_queryset(self):
        return MyRecordQuerySet(self.model, using=self._db)

    def all(self):
        # 在这里可以重写all方法，譬如只返回最近一年的记录。
        return super().all()


class Record(models.Model):
    title = models.CharField(max_length=100, unique=True, null=True, blank=True)
    zone = models.CharField('域名', max_length=100)
    host = models.CharField('子域，主机记录', max_length=100, default='@')
    type = models.CharField('记录类型', max_length=5, choices=Types.items(), default='A')
    data = models.CharField('记录值', max_length=255, blank=True, null=True)
    status = models.CharField('状态', max_length=11, choices=Record_Status.items(), default='enable')
    ttl = models.IntegerField(default=60)
    mx_priority = models.IntegerField(blank=True, null=True)
    priority = models.IntegerField(default=10)
    refresh = models.IntegerField(default=28800)
    retry = models.IntegerField(default=14400)
    expire = models.IntegerField(default=86400)
    minimum = models.IntegerField(default=86400)
    serial = models.BigIntegerField(default=int(datetime.datetime.now().strftime("%Y%m%d00")))
    resp_person = models.CharField(max_length=64, default='ddns.net')
    primary_ns = models.CharField(max_length=64, default='ns.ddns.net.')
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)

    objects = RecordManager()

    def __str__(self):
        return '{}'.format(self.title)

    def save(self, *args, **kwargs):
        self.title = '{}-{}-{}-{}'.format(self.zone, self.host, self.type, self.data)
        super(Record, self).save(*args, **kwargs)

    class Meta:
        db_table = 'dns_records'
        index_together = ('zone', 'host')
        unique_together = (('zone', 'host', 'type', 'data'),)
        ordering = ('create_time',)
        verbose_name = u'域名记录表'
        verbose_name_plural = u'域名记录表'


class DnsLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=6, choices=(('add', '添加'), ('delete', '删除'), ('edit', '修改')))
    old_zone = models.CharField(max_length=100, blank=True, null=True)
    new_zone = models.CharField(max_length=100, blank=True, null=True)
    old_record = models.CharField(max_length=100, blank=True, null=True)
    new_record = models.CharField(max_length=100, blank=True, null=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    def __str__(self):
        return '{} {}'.format(self.user.username, self.action)

    class Meta:
        db_table = 'dns_dns_log'
        ordering = ('-create_time',)
        verbose_name = u'域名操作记录表'
        verbose_name_plural = u'域名操作记录表'

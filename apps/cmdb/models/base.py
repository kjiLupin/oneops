from django.db import models
from IPy import IP
# Create your models here.


class IDC(models.Model):
    idc_name = models.CharField('IDC名称', max_length=20, unique=True)
    address = models.CharField('IDC地址', max_length=255, blank=True, null=True)
    phone = models.CharField('代理商维护人联系方式', max_length=15, blank=True, null=True)
    email = models.CharField('代理商维护人邮箱', max_length=30, blank=True, null=True)
    cabinet_num = models.IntegerField('机柜数量', blank=True, null=True)
    comment = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        db_table = 'cmdb_idc'
        verbose_name = u'IDC表'
        verbose_name_plural = u'IDC表'


class Cabinet(models.Model):
    name = models.CharField('机柜名', max_length=30)
    idc = models.ForeignKey(IDC, blank=True, null=True, on_delete=models.SET_NULL)
    power = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'cmdb_cabinet'
        verbose_name = u'机柜表'
        verbose_name_plural = u'机柜表'


class VLan(models.Model):
    idc = models.ForeignKey(IDC, on_delete=models.DO_NOTHING)
    vlan_num = models.IntegerField('vlan号', blank=True, null=True)
    comment = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'cmdb_vlan'
        # unique_together = (('idc', 'vlan_num'),)
        verbose_name = u'VLan表'
        verbose_name_plural = u'VLan表'


class NetworkSegment(models.Model):
    vlan = models.ForeignKey(VLan, on_delete=models.DO_NOTHING)
    segment = models.CharField('网段', max_length=20)
    netmask = models.CharField('子网掩码', max_length=20, default='255.255.255.0')
    comment = models.CharField(max_length=50, blank=True, null=True)

    @property
    def segment_prefix(self):
        return IP("{0}/{1}".format(self.segment, self.netmask), make_net=True).strNormal()

    class Meta:
        db_table = 'cmdb_segment'
        unique_together = (('vlan', 'segment'),)
        verbose_name = u'网段表'
        verbose_name_plural = u'网段表'


class Ip(models.Model):
    ip = models.GenericIPAddressField()
    segment = models.ForeignKey(NetworkSegment, on_delete=models.DO_NOTHING)
    last_detected = models.DateTimeField(blank=True, null=True)
    comment = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'cmdb_ip'
        unique_together = (('ip', 'segment'),)
        verbose_name = u'IP表'
        verbose_name_plural = u'IP表'


class CDN(models.Model):
    supplier = models.CharField(max_length=6, choices=(('aliyun', '阿里云'), ('azure', '微软云')))
    account = models.CharField('账户/ID', max_length=50)
    secret = models.CharField('Key/Secret', max_length=256)
    end_point = models.CharField('EndPoint', max_length=50)
    comment = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cmdb_cdn'
        verbose_name = u'CDN'
        verbose_name_plural = u'CDN'


class OSS(models.Model):
    supplier = models.CharField(max_length=6, choices=(('aliyun', '阿里云'), ('azure', '微软云')))
    account = models.CharField('账户/ID', max_length=50)
    secret = models.CharField('Key/Secret', max_length=256)
    end_point = models.CharField('EndPoint', max_length=50)
    container = models.CharField('Container/Bucket', max_length=50)
    comment = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    create_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cmdb_oss'
        verbose_name = u'OSS'
        verbose_name_plural = u'OSS'

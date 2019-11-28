from django.db import models

# Create your models here.


class Config(models.Model):
    item = models.CharField('配置项', max_length=50, primary_key=True)
    value = models.CharField('配置项值', max_length=200)
    comment = models.CharField('描述', max_length=200, default='', blank=True)

    class Meta:
        db_table = 'common_config'
        verbose_name = u'系统配置'
        verbose_name_plural = u'系统配置'


class RPCIpWhite(models.Model):
    """
    RPC API ip 白名单
    """
    url_name = models.CharField(max_length=255, unique=True)
    ip_list = models.TextField('ip列表，逗号分隔', default='*')
    applicant = models.CharField('申请人', max_length=255)
    comment = models.CharField('申请备注', max_length=200, default='', blank=True)

    class Meta:
        db_table = 'common_rpc_ip_white'
        verbose_name = u'远程调用api接口白名单表'
        verbose_name_plural = u'远程调用api接口白名单表'

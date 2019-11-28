from django.db import models
from cmdb.models.asset import Server


class HostUser(models.Model):
    LOGIN_TYPE_CHOICES = (
        ('M', 'Password'),
        ('K', 'Key'),
    )
    username = models.CharField("主机的系统账户", max_length=25)
    login_type = models.CharField(max_length=1, choices=LOGIN_TYPE_CHOICES, default='M')
    password = models.CharField(max_length=100, blank=True, null=True, help_text="静态密码登录用户的密码")
    key_path = models.CharField(max_length=100, blank=True, null=True, help_text="秘钥文件路径")
    key_password = models.CharField(max_length=100, blank=True, null=True, help_text="ssh秘钥的密码")
    key_pub = models.TextField("公钥", blank=True, null=True)
    key_pvt = models.TextField("私钥", blank=True, null=True)
    version = models.IntegerField("系统用户的版本", blank=True, null=True)
    active = models.BooleanField(default=True)
    description = models.CharField(max_length=100, blank=True, null=True, default='')
    creation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['username']
        db_table = 'ssh_host_user'
        verbose_name = 'SSH系统用户'
        verbose_name_plural = 'SSH系统用户'

    def __unicode__(self):
        return "%s Type.%s Ver.%s" % (self.username, self.login_type, self.version)


class HostUserAsset(models.Model):
    asset = models.ForeignKey(Server, on_delete=models.CASCADE)
    host_user = models.ForeignKey(HostUser, on_delete=models.CASCADE)

    class Meta:
        db_table = 'ssh_host_user_asset'
        verbose_name = 'SSH系统用户主机绑定'
        verbose_name_plural = 'SSH系统用户主机绑定'

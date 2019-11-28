from django.db import models
# Create your models here.


class BizMgtDept(models.Model):
    dept_name = models.CharField(max_length=50, blank=True, null=True)
    dept_code = models.CharField(max_length=30, blank=True, null=True)
    parent_id = models.IntegerField(blank=True, null=True)
    comment = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        db_table = 'cmdb_biz_mgt_dept'
        unique_together = (('dept_name', 'parent_id'),)
        verbose_name = u'业务负责部门表'
        verbose_name_plural = u'业务负责部门表'


class Process(models.Model):
    name = models.CharField('进程名', max_length=50)
    version_arg = models.CharField('获取进程版本的参数', max_length=50, default='--version')
    comment = models.CharField(max_length=50, blank=True, null=True)
    create_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cmdb_process'
        verbose_name = u'进程表'
        verbose_name_plural = u'进程表'


class App(models.Model):
    App_STATUS = (
        (0, u"申请上线"),
        (1, u"已上线"),
        (2, u"申请下线"),
        (3, u"已下线"),
    )
    app_code = models.CharField(max_length=30, null=True, unique=True)
    app_name = models.CharField(max_length=50)
    biz_mgt_dept = models.ForeignKey(BizMgtDept, on_delete=models.DO_NOTHING)
    primary = models.CharField('第一负责人', max_length=256, blank=True, null=True)
    secondary = models.CharField('第二负责人', max_length=256, blank=True, null=True)
    app_type = models.CharField(max_length=3, choices=(('war', 'WAR'), ('jar', 'JAR')))
    scm_url = models.CharField('Git/SVN地址', max_length=100, blank=True, null=True)
    domain_name = models.CharField(max_length=50, blank=True, null=True)
    domain_name_test = models.CharField('测试环境域名', max_length=50, blank=True, null=True)
    importance = models.CharField('应用重要性', max_length=1, choices=(('a', '核心'), ('b', '正式'), ('c', '内部')))
    tomcat_port = models.IntegerField(blank=True, null=True)
    process = models.ForeignKey(Process, blank=True, null=True, on_delete=models.SET_NULL)
    jdk = models.CharField('JDK版本', max_length=10, blank=True, null=True)
    xms = models.CharField('Xms', max_length=20, blank=True, null=True)
    xmx = models.CharField('Xmx', max_length=20, blank=True, null=True)
    comment = models.CharField(max_length=50, blank=True, null=True)
    modify_date = models.DateTimeField(auto_now=True)
    parent_id = models.IntegerField(blank=True, null=True)
    applicant = models.CharField(max_length=50, blank=True, null=True)
    status = models.SmallIntegerField('状态', choices=App_STATUS, default=0)

    class Meta:
        db_table = 'cmdb_app'
        ordering = ['-id']
        verbose_name = u'应用表'
        verbose_name_plural = u'应用表'

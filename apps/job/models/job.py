
from django.db import models
from django.conf import settings
from ssh.models.host_user import HostUser


class Tag(models.Model):
    name = models.CharField(max_length=128)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=False)
    creation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'job_tag'
        verbose_name = 'Job标签表'
        verbose_name_plural = 'Job标签表'

    def __unicode__(self):
        return "%s %s created_by.%s" % (self.name, self.creation_date, self.created_by.username)


TASK_TYPE = (
    ('command', '命令执行'),
    ('upload', '文件上传'),
    ('download', '文件下载')
)
EXECUTE_TYPE = (
    ('paramiko', 'Paramiko'),
    ('ad-hoc', 'Ad-Hoc'),
    ('playbook', 'Playbook')
)


class Job(models.Model):
    """
    作业：可能会多次执行的快速命令，保存为作业方便调用。
    """
    name = models.CharField("作业名", max_length=100)
    host_user = models.ForeignKey(HostUser, blank=True, null=True, on_delete=models.SET_NULL)
    exec_type = models.CharField(max_length=8, choices=EXECUTE_TYPE)
    task_type = models.CharField(max_length=8, choices=TASK_TYPE, default="command")
    source_file = models.TextField("下载：文件在远程主机上的路径", blank=True, null=True)
    destination_file = models.TextField("上传：文件传到远程主机上的路径", blank=True, null=True)
    cmd = models.TextField("Paramiko的命令", blank=True, null=True)
    host = models.CharField("目标机器", max_length=255, blank=True, null=True)
    inventory = models.CharField("hosts文件", max_length=100, blank=True, null=True)
    module_name = models.CharField("Ansible模块", max_length=20, blank=True, null=True)
    module_args = models.TextField("Ansible模块参数", blank=True, null=True)
    playbook = models.TextField('Playbook文件路径', blank=True, null=True)
    extra_vars = models.TextField('Playbook额外参数', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   editable=False)  # not blank=False on purpose for admin!
    creation_date = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, related_name='%(class)s_by_tag')
    public = models.BooleanField(default=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-id']
        db_table = 'job_job'
        verbose_name = 'Job作业表'
        verbose_name_plural = 'Job作业表'

    def __unicode__(self):
        return "%s:%s" % (self.name, self.description)


class Task(models.Model):
    """
        快速命令执行
    """
    uuid = models.CharField("UUID", max_length=36)
    job = models.ForeignKey(Job, blank=True, null=True, on_delete=models.SET_NULL)
    name = models.CharField("用户名+时间，或者IP加时间（接口调用产生的）", max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL)
    exec_type = models.CharField(max_length=8, choices=EXECUTE_TYPE)
    task_type = models.CharField(max_length=8, choices=TASK_TYPE, default="command")
    source_file = models.TextField("下载：文件在远程主机上的路径", null=True)
    destination_file = models.TextField("上传：文件传到远程主机上的路径", null=True)
    host = models.CharField("目标机器", max_length=255, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    task_nums = models.PositiveIntegerField("总任务数", null=True)
    executed = models.BooleanField('是否已执行完毕', default=False)
    error_msg = models.TextField("保存出错信息", null=True)

    class Meta:
        db_table = 'job_task'
        ordering = ['-id']
        verbose_name = 'Job任务表'
        verbose_name_plural = 'Job任务表'

    def __unicode__(self):
        return "%s:%s %s" % (self.name, self.exec_type, self.task_type)


class TaskLog(models.Model):
    """
        快速命令执行的结果，每个执行的任务都会被记录
    """
    EXECUTE_STATUS = (
        ('prepared', '准备'),
        ('executing', '执行中'),
        ('success', '成功'),
        ('failed', '失败')
    )
    task = models.ForeignKey(Task, blank=True, null=True, on_delete=models.SET_NULL)
    host = models.CharField("ip或主机名", max_length=50)
    host_user = models.CharField("远程用户", max_length=50)
    cmd = models.TextField(blank=True, null=True)
    module_name = models.CharField("Ansible模块", max_length=20, blank=True, null=True)
    module_args = models.TextField("Ansible模块参数", blank=True, null=True)
    playbook_name = models.CharField("Playbook文件名", max_length=50, blank=True, null=True)
    playbook = models.TextField('Playbook内容', blank=True, null=True)
    extra_vars = models.TextField('Playbook额外参数', blank=True, null=True)
    result = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=EXECUTE_STATUS, default='prepared')
    start_time = models.DateTimeField("开始执行的时间", blank=True, null=True)
    end_time = models.DateTimeField("执行完成的时间", blank=True, null=True)

    class Meta:
        db_table = 'job_task_log'
        ordering = ['-id']
        verbose_name = 'Job任务日志表'
        verbose_name_plural = 'Job任务日志表'

    def __unicode__(self):
        return "%s:%s" % (self.host, self.result)


class JobConfig(models.Model):
    item = models.CharField('配置项', max_length=50, primary_key=True)
    value = models.CharField('配置项值', max_length=200)
    description = models.CharField('描述', max_length=200, default='', blank=True)

    class Meta:
        db_table = 'job_config'
        verbose_name = 'Job配置表'
        verbose_name_plural = 'Job配置表'

    def __unicode__(self):
        return "%s-%s-%s" % (self.item, self.value, self.description)

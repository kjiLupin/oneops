from django.db import models
from django.contrib.auth.models import Group


COMMAND_DETAIL_TYPE = (('white', '白名单命令'), ('sensitive', '敏感命令'), ('perilous', '高危命令'))


class PerilousCommand(models.Model):
    """
    最基础的分类，不同用户组对一个命令，即可视为黑名单，也可以视为白名单。
    """
    cmd_regex = models.CharField("高危命令，正则", max_length=255)
    cmd_type = models.CharField(max_length=5, choices=(('black', '黑名单'), ('white', '白名单')), default='black')
    comment = models.CharField(max_length=100, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ssh_perilous_cmd'
        verbose_name = 'SSH高危命令表'
        verbose_name_plural = 'SSH高危命令表'

    def __unicode__(self):
        return "%s %s %s" % (self.cmd_regex, self.cmd_type, self.comment)


class CommandDetail(models.Model):
    """
    添加命令到命令组
    """
    perilous_command = models.ForeignKey(PerilousCommand, null=True, on_delete=models.SET_NULL)
    cmd_type = models.CharField(max_length=9, choices=COMMAND_DETAIL_TYPE, default='perilous')

    class Meta:
        db_table = 'ssh_perilous_cmd_detail'
        verbose_name = 'SSH高危命令详细表'
        verbose_name_plural = 'SSH高危命令详细表'

    def __unicode__(self):
        return "%s %s" % (self.command.cmd_regex, self.cmd_type)


class CommandGroup(models.Model):
    name = models.CharField(max_length=50, null=False, help_text="命令组名称")
    command_detail = models.ManyToManyField(CommandDetail)
    comment = models.CharField(blank=True, null=True, max_length=50)
    group_type = models.CharField(max_length=5, choices=(('black', '黑名单组'), ('white', '白名单组')), default='black')
    creation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ssh_perilous_cmd_group'
        verbose_name = 'SSH高危命令组表'
        verbose_name_plural = 'SSH高危命令组表'

    def __unicode__(self):
        return '%s %s %s' % (self.name, self.comment, self.type)


class UserGroupCommand(models.Model):
    command_group = models.ManyToManyField(CommandGroup, help_text="命令组")
    user_group = models.ForeignKey(Group, null=True, on_delete=models.SET_NULL, help_text="用户组")
    comment = models.CharField(blank=True, null=True, max_length=50)
    creation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ssh_user_group_cmd'
        verbose_name = 'SSH用户组命令表'
        verbose_name_plural = 'SSH用户组命令表'

    def __unicode__(self):
        return self.user_group.name

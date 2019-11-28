from django.db import models

SCM_TYPE_CHOICES = (
    ('git', 'Git'),
    ('svn', 'SVN'),
)

DEPLOY_MODEL_CHOICES = (
    ('branch', 'branch'),
    ('tag', 'tag'),
)


class Project(models.Model):
    jenkins_name = models.CharField('Jenkins项目名', max_length=50)
    app_code = models.CharField('项目名', max_length=50)
    scm_type = models.CharField(max_length=5, choices=SCM_TYPE_CHOICES)
    scm_url = models.CharField('Git/SVN地址', max_length=50, blank=True, null=True)
    pre_hosts = models.CharField(max_length=50, null=True, blank=True)
    beta_hosts = models.CharField(max_length=50, null=True, blank=True)
    prod_hosts = models.CharField(max_length=50, null=True, blank=True)
    description = models.CharField(max_length=128, null=True, blank=True)
    deploy_script = models.CharField(max_length=128, null=True, blank=True)
    playbook = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        db_table = 'job_project'
        verbose_name = 'Job项目表'
        verbose_name_plural = 'Job项目表'


class DeployRecord(models.Model):
    """
    status: 0:构建中，未发布，1:预发，2:beta，3：正式
    """
    project = models.ForeignKey(Project, null=True, on_delete=models.SET_NULL)
    deploy_model = models.CharField(max_length=6, choices=DEPLOY_MODEL_CHOICES, default='branch')
    deploy_ver = models.CharField('分支名或版本名', max_length=50, null=True, blank=True)
    applicant = models.CharField('申请人', max_length=50, null=True, blank=True)
    commits = models.PositiveIntegerField('构建总次数', blank=True, default=0)
    status = models.PositiveSmallIntegerField('状态', blank=True, default=0)
    apply_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'job_deploy_record'
        verbose_name = 'Job项目发布历史表'
        verbose_name_plural = 'Job项目发布历史表'

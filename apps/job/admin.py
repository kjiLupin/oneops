from django.contrib import admin
from job.models.job import Job, Task, Tag, JobConfig
from job.models.continuous_deploy import Project, DeployRecord


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'host_user', 'exec_type', 'task_type', 'source_file', 'destination_file',
                    'cmd', 'host', 'inventory', 'module_name', 'module_args', 'playbook', 'extra_vars',
                    'description', 'created_by', 'creation_date', 'public', 'active')
    search_fields = ['exec_type', 'task_type', 'public', 'active']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'uuid', 'job', 'name', 'user', 'exec_type', 'task_type', 'source_file', 'destination_file',
                    'host', 'creation_date', 'task_nums', 'executed', 'error_msg')
    search_fields = ['exec_type', 'task_type']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_by', 'creation_date')
    search_fields = ['name']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'jenkins_name', 'app_code', 'scm_type', 'pre_hosts', 'beta_hosts', 'prod_hosts',
                    'description', 'deploy_script', 'playbook')
    search_fields = ['jenkins_name', 'app_code', 'description']


@admin.register(DeployRecord)
class DeployRecordAdmin(admin.ModelAdmin):
    list_display = ('project', 'deploy_model', 'deploy_ver', 'applicant', 'commits', 'status')
    search_fields = ['project']


@admin.register(JobConfig)
class JobConfigAdmin(admin.ModelAdmin):
    list_display = ('item', 'value', 'description')
    search_fields = ['item']

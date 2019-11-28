# coding:utf-8
from django.urls import path, re_path

from job.api.inventory import InventoryListAPIView, InventoryConflictAPIView
from job.api.scripts import ScriptsListAPIView, ScriptsDirListAPIView
from job.api.playbook import PlaybookListAPIView, PlaybookConflictAPIView
from job.api.job import JobListAPIView, JobDetailAPIView

from job.views.charts import charts
from job.views.config import JobSettingsView, JobConfigListView
from job.views.inventory import InventoryView, InventoryListView, InventoryDetailView, InventoryHostsFileView,\
        InventoryHostsFileListView
from job.views.playbook import PlaybookView, PlaybookListView, PlaybookDetailView, PlaybookFileListView,\
        PlaybookFileView
from job.views.galaxy import GalaxyView, GalaxyRolesListView, GalaxyRolesFileView
from job.views.scripts import ScriptsView, ScriptsListView, ScriptsDetailView, ScriptsFileListView,\
        ScriptsFileView
from job.views.cmd_execute import CmdExecute
from job.views.task import TaskView, TaskListView, TaskLogView, TaskLogListView
from job.views.file import FileUploadView, FileDownloadView, FileDownloadExportView
from job.views.job import JobAddView, JobExecuteView, JobView, JobListView, JobDetailView, JobLogView, JobLogListView
from job.views.job_periodic_task import PeriodicTaskView, PeriodicTaskListView, PeriodicTaskDetailView

app_name = 'job'

urlpatterns = [
        # /v1/inventory/
        re_path('(?P<version>[v1|v2]+)/inventory/', InventoryListAPIView.as_view(), name='api-inventory'),
        re_path('(?P<version>[v1|v2]+)/scripts/', ScriptsListAPIView.as_view(), name='api-scripts'),
        re_path('(?P<version>[v1|v2]+)/scripts_directory/', ScriptsDirListAPIView.as_view(), name='api-scripts-dir'),
        re_path('(?P<version>[v1|v2]+)/playbook/', PlaybookListAPIView.as_view(), name='api-playbook'),
        re_path('(?P<version>[v1|v2]+)/job_list/', JobListAPIView.as_view(), name='api-job-list'),
        re_path('(?P<version>[v1|v2]+)/job_detail/(?P<pk>\d+)?$', JobDetailAPIView.as_view(), name='api-job-detail'),
]

urlpatterns += [
        path('charts/', charts, name='charts'),
        path('cmd_execute/', CmdExecute.as_view(), name='cmd-execute'),
        path('file_upload/', FileUploadView.as_view(), name='file-upload'),
        path('file_download/', FileDownloadView.as_view(), name='file-download'),
        re_path('file_download_export/(?P<id>[0-9]+)?', FileDownloadExportView.as_view(), name='file-download-export'),

        path('task/', TaskView.as_view(), name='task'),
        path('task_list/', TaskListView.as_view(), name='task-list'),
        re_path('task_log/(?P<id>[0-9]+)?', TaskLogView.as_view(), name='task-log'),
        re_path('task_log_list/(?P<id>[0-9]+)?', TaskLogListView.as_view(), name='task-log-list'),

        path('job_execute/', JobExecuteView.as_view(), name='job-execute'),
        path('job_add/', JobAddView.as_view(), name='job-add'),
        path('job/', JobView.as_view(), name='job'),
        path('job_list/', JobListView.as_view(), name='job-list'),
        re_path('job_detail/(?P<pk>\d+)?$', JobDetailView.as_view(), name='job-detail'),
        path('periodic_task/', PeriodicTaskView.as_view(), name='periodic-task'),
        path('periodic_task_list/', PeriodicTaskListView.as_view(), name='periodic-task-list'),
        re_path('periodic_task_detail/(?P<pk>[0-9]+)?', PeriodicTaskDetailView.as_view(), name='periodic-task-detail'),

        path('job_log/', JobLogView.as_view(), name='job-log'),
        path('job_log_list/', JobLogListView.as_view(), name='job-log-list'),

        path('inventory/', InventoryView.as_view(), name='inventory'),
        path('inventory_list/', InventoryListView.as_view(), name='inventory-list'),
        path('inventory_detail/', InventoryDetailView.as_view(), name='inventory-detail'),
        path('inventory_file_list/', InventoryHostsFileListView.as_view(), name='inventory-file-list'),
        re_path('inventory_file/(?P<file>[0-9a-zA-Z\-_./]+)$', InventoryHostsFileView.as_view(), name='inventory-file'),
        path('inventory_conflict', InventoryConflictAPIView.as_view(), name='inventory-conflict'),

        path('playbook/', PlaybookView.as_view(), name='playbook'),
        path('playbook_list/', PlaybookListView.as_view(), name='playbook-list'),
        path('playbook_detail/', PlaybookDetailView.as_view(), name='playbook-detail'),
        path('playbook_file_list/', PlaybookFileListView.as_view(), name='playbook-file-list'),
        re_path('playbook_file/(?P<file>[0-9a-zA-Z\-_./]+)?', PlaybookFileView.as_view(), name='playbook-file'),
        path('playbook_conflict', PlaybookConflictAPIView.as_view(), name='playbook-conflict'),

        path('galaxy/', GalaxyView.as_view(), name='galaxy'),
        path('galaxy_list/', GalaxyRolesListView.as_view(), name='galaxy-list'),
        re_path('galaxy_roles_file_detail/(?P<file>[0-9a-zA-Z\-_./]+)?', GalaxyRolesFileView.as_view(),
                name='galaxy-roles-file-detail'),

        path('scripts/', ScriptsView.as_view(), name='scripts'),
        path('scripts_list/', ScriptsListView.as_view(), name='scripts-list'),
        path('scripts_detail/', ScriptsDetailView.as_view(), name='scripts-detail'),
        path('scripts_file_list/', ScriptsFileListView.as_view(), name='scripts-file-list'),
        re_path('scripts_file/(?P<file>[0-9a-zA-Z\-_./]+)?', ScriptsFileView.as_view(), name='scripts-file'),

        path('settings/', JobSettingsView.as_view(), name='settings'),
        path('config_list/', JobConfigListView.as_view(), name='config-list'),
]

# coding:utf-8
"""wdoneops URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static, serve
from .views import index, install, dashboard
from cmdb.api import api_compatibility


urlpatterns = [
    re_path('^$', index),
    path('install/', install),
    path('dashboard/', dashboard),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('workflow/', include('workflow.urls', namespace='workflow')),
    path('common/', include('common.urls', namespace='common')),
    path('cmdb/', include('cmdb.urls', namespace='cmdb')),
    path('dns/', include('dns_pod.urls', namespace='dns')),
    path('ssh/', include('ssh.urls', namespace='ssh')),
    path('job/', include('job.urls', namespace='job')),
    path('tools/', include('tools.urls', namespace='tools')),
    re_path(r'media/(?P<path>.*)/$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# 兼容老版本cmdb api
urlpatterns += [
    path('api', api_compatibility),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

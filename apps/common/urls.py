# coding:utf-8
from django.urls import path
from .views import email_check, settings

app_name = 'common'

# API
urlpatterns = [
]

urlpatterns += [
        path('email/check/', email_check),
        path('settings/', settings, name='settings'),
]

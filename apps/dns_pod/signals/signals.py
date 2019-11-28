# coding:utf-8

from django.dispatch import Signal

post_save = Signal(providing_args=["record"])
post_update = Signal(providing_args=["record"])

post_save = Signal(providing_args=["record"])
post_delete = Signal(providing_args=["record"])

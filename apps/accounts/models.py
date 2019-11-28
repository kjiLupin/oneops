from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    password2 = models.CharField('可逆向解密', max_length=50, null=True, blank=True)
    display = models.CharField('中文名', max_length=50, blank=True)
    ding_dept_id = models.CharField('钉钉中的部门ID', max_length=50, blank=True)
    ding_user_id = models.CharField('钉钉中的用户ID', max_length=50, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'accounts_user'
        verbose_name = u'用户表'
        verbose_name_plural = u'用户表'


class RetiredEmployeeRecord(models.Model):
    work_no = models.CharField(max_length=10)
    display = models.CharField(max_length=50)
    comment = models.CharField(max_length=50)
    date_retired = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'retired_employee_record'
        verbose_name = u'员工离职记录表'
        verbose_name_plural = u'员工离职记录表'

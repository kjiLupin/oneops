from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
# Register your models here.
from accounts.models import User, RetiredEmployeeRecord


# 用户管理
@admin.register(User)
class UsersAdmin(UserAdmin):
    def __init__(self, *args, **kwargs):
        super(UserAdmin, self).__init__(*args, **kwargs)
        self.list_display = ('id', 'ding_dept_id', 'ding_user_id', 'username', 'display', 'email', 'is_superuser',
                             'is_staff', 'is_active')
        self.search_fields = ('id', 'username', 'display', 'email')

    def changelist_view(self, request, extra_context=None):
        # 这个方法在源码的admin/options.py文件的ModelAdmin这个类中定义，我们要重新定义它，以达到不同权限的用户，返回的表单内容不同
        if request.user.is_superuser:
            # 此字段定义UserChangeForm表单中的具体显示内容，并可以分类显示
            self.fieldsets = (
                ('认证信息', {'fields': ('username', 'password')}),
                ('个人信息', {'fields': ('ding_dept_id', 'ding_user_id', 'display', 'email')}),
                ('权限信息', {'fields': ('is_superuser', 'is_active', 'is_staff', 'groups', 'user_permissions')}),
                ('其他信息', {'fields': ('last_login', 'date_joined')}),
            )
            # 此字段定义UserCreationForm表单中的具体显示内容
            self.add_fieldsets = (
                (None, {'fields': ('username', 'display', 'email', 'password1', 'password2'), }),
            )
        return super(UserAdmin, self).changelist_view(request, extra_context)


@admin.register(RetiredEmployeeRecord)
class RetiredEmployeeRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'work_no', 'display', 'comment', 'date_retired')
    search_fields = ['work_no', 'display', 'comment']

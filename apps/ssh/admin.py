from django.contrib import admin
from ssh.models.host_user import HostUser
from ssh.models.perilous_command import PerilousCommand, CommandDetail, CommandGroup, UserGroupCommand


@admin.register(HostUser)
class HostUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'login_type', 'password', 'key_password', 'key_path', 'key_pub', 'key_pvt',
                    'version', 'active', 'description', 'creation_date')
    search_fields = ['username', 'description']
    list_filter = ('login_type',)


@admin.register(PerilousCommand)
class PerilousCommandAdmin(admin.ModelAdmin):
    list_display = ('id', 'cmd_regex', 'cmd_type', 'comment', 'creation_date')
    search_fields = ['cmd_regex', 'comment']
    list_filter = ('cmd_type',)


@admin.register(CommandGroup)
class CommandGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'comment', 'group_type', 'creation_date')
    search_fields = ['name', 'comment']
    list_filter = ('group_type',)


@admin.register(UserGroupCommand)
class UserGroupCommandAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_command_groups', 'user_group', 'creation_date')

    @staticmethod
    def get_command_groups(obj):
        return "\n".join([p.name for p in obj.command_group.all()])

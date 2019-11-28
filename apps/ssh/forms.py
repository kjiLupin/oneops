# _*_ coding: utf-8 _*_

from django.forms import ModelForm
from ssh.models.host_user import HostUser
from ssh.models.perilous_command import PerilousCommand, CommandDetail, CommandGroup


class HostUserForm(ModelForm):
    class Meta:
        model = HostUser
        fields = ["username", "login_type", "password", "key_password", "key_path", "key_pub", "key_pvt",
                  "version", "active", "description"]


class PerilousCommandForm(ModelForm):
    class Meta:
        model = PerilousCommand
        fields = ["cmd_regex", "cmd_type", "comment"]


class CommandDetailForm(ModelForm):
    class Meta:
        model = CommandDetail
        fields = ["perilous_command", "cmd_type"]


class CommandGroupForm(ModelForm):
    class Meta:
        model = CommandGroup
        fields = ["name", "command_detail", "comment", "group_type"]

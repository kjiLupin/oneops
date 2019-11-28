
import re
import simplejson as json
from ssh.models.perilous_command import UserGroupCommand


def get_perilous_cmd(user):
    # 遍历用户所属所有用户组，检查该用户组是否绑定了 高危命令组。将白名单，黑名单命令汇总返回。

    white_cmds, perilous_cmds, sensitive_cmds = list(), list(), list()
    for user_group in user.groups.all():
        for user_group_cmd in UserGroupCommand.objects.filter(user_group=user_group):

            for cmd_group in user_group_cmd.command_group.all():
                if cmd_group.group_type == "white":
                    white_cmds.extend([cd.perilous_command.cmd_regex for cd in cmd_group.command_detail.all()])
                elif cmd_group.group_type == "black":
                    for cd in cmd_group.command_detail.all():
                        if cd.cmd_type == "perilous":
                            perilous_cmds.append(cd.perilous_command.cmd_regex)
                        else:
                            sensitive_cmds.append(cd.perilous_command.cmd_regex)
    return white_cmds, perilous_cmds, sensitive_cmds


def perilous_cmd_check(user_input_cmd, white_cmds, perilous_cmds, sensitive_cmds):
    # 若既有白名单命令，又有黑名单命令，则白名单命令生效。
    cmd_list = re.split('&&|\|\||;', user_input_cmd)
    flag = True
    if white_cmds:
        for cmd in cmd_list:
            for cmd_regex in white_cmds:
                # 用户输入的命令分解后，其中一条不能匹配到白名单命令，就表示非法
                if not re.match(cmd, cmd_regex):
                    flag = False
    elif perilous_cmds or sensitive_cmds:
        for cmd in cmd_list:
            for cmd_regex in perilous_cmds:
                # 若匹配到黑名单命令中的高危命令，则表示非法
                if re.match(cmd, cmd_regex):
                    flag = False

            for cmd_regex in sensitive_cmds:
                # 若能匹配到黑名单命令中的敏感命令，则表示合法，但要记录在日志中
                if re.match(cmd, cmd_regex):
                    # 记录日志代码暂时未实现
                    pass
    # 没有设置任何黑名单命令
    return flag

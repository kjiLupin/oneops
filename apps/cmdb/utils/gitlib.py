# -*- coding: utf-8 -*-
from common.utils.cryptor import cryptor
import gitlab
import traceback

gitlab_url = 'http://git.yadoom.com'
gitlab_username = "jenkins@yadoom.com"
gitlab_password = "775c36d2cf164e57abed52bc7ec2699c"


def get_gitlab_instance():
    password = cryptor.decrypt(gitlab_password)
    gitlab_server = gitlab.Gitlab(gitlab_url, email=gitlab_username, password=password)
    gitlab_server.auth()
    return gitlab_server


def get_gitlib_group_list():
    gitlab_server = get_gitlab_instance()
    groups = gitlab_server.groups.list(all=True)
    return [group.name for group in groups]

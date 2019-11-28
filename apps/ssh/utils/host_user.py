#!/usr/bin/env python
# -*- coding: utf-8 -*-

import traceback
from cmdb.models.asset import Server
from ssh.models.host_user import HostUserAsset


def get_host_user(ip, port, user):
    try:
        host = Server.objects.get(login_address='{}:{}'.format(ip, str(port)))
        hua = HostUserAsset.objects.get(asset=host, host_user__username=user, host_user__active=True)
        return hua.host_user
    except Server.DoesNotExist:
        traceback.print_exc()
    except HostUserAsset.DoesNotExist:
        traceback.print_exc()
    except Exception:
        traceback.print_exc()
    return

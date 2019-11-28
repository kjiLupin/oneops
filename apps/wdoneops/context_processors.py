# -*- coding: UTF-8 -*-


def global_info(request):
    """存放用户，菜单信息等."""
    user = request.user
    if user:
        # 获取待办数量
        try:
            todo = 0
        except Exception:
            todo = 0
    else:
        todo = 0
    request.session.set_expiry(86400)
    info = {
        'todo': todo
    }
    return info

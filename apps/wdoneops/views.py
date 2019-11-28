from django.shortcuts import render
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType


@login_required
def index(request):
    return render(request, 'index.html')


@login_required
def dashboard(request):
    return render(request, 'index.html')


def install(request):
    # 初始化
    from accounts.models import User
    from cmdb.models import IDC, BizMgtDept
    if User.objects.filter(id=5000).exists():
        return render('message.html', {'message': '警告：请勿重复初始化！'})
    try:
        User.objects.create(id=5000, username="admin", display="超级管理员", email='admin@localhost', is_superuser=True)
        IDC.objects.create(id=1, idc_name='默认', comment='默认IDC')
        BizMgtDept.objects.create(id=1, dept_name='未知', comment='用于保存未指定部门的业务')
        # 初始化权限项
        Permission.objects.filter(codename__startswith='perm_').delete()
        content_type = ContentType.objects.get_for_model(Permission)
        for item in [
            {"codename": "perm_accounts_charts", "name": "账户 图表可视化", "content_type": content_type},
            {"codename": "perm_accounts_user_view", "name": "用户查看", "content_type": content_type},
            {"codename": "perm_accounts_user_edit", "name": "用户编辑", "content_type": content_type},
            {"codename": "perm_accounts_perm_view", "name": "权限项查看", "content_type": content_type},
            {"codename": "perm_accounts_perm_edit", "name": "权限项编辑", "content_type": content_type},
            {"codename": "perm_common_settings_view", "name": "配置项查看", "content_type": content_type},
            {"codename": "perm_common_settings_edit", "name": "配置项编辑", "content_type": content_type},

            {"codename": "perm_cmdb_idc_view", "name": "IDC查看", "content_type": content_type},
            {"codename": "perm_cmdb_idc_edit", "name": "IDC编辑", "content_type": content_type},
            {"codename": "perm_cmdb_cabinet_view", "name": "机柜查看", "content_type": content_type},
            {"codename": "perm_cmdb_cabinet_edit", "name": "机柜编辑", "content_type": content_type},
            {"codename": "perm_cmdb_vlan_view", "name": "VLAN查看", "content_type": content_type},
            {"codename": "perm_cmdb_vlan_edit", "name": "VLAN编辑", "content_type": content_type},
            {"codename": "perm_cmdb_segment_view", "name": "网段查看", "content_type": content_type},
            {"codename": "perm_cmdb_segment_edit", "name": "网段编辑", "content_type": content_type},
            {"codename": "perm_cmdb_ip_view", "name": "IP查看", "content_type": content_type},
            {"codename": "perm_cmdb_ip_edit", "name": "IP编辑", "content_type": content_type},
            {"codename": "perm_cmdb_asset_view_dev", "name": "资产查看（开发视角）", "content_type": content_type},
            {"codename": "perm_cmdb_asset_view", "name": "资产查看", "content_type": content_type},
            {"codename": "perm_cmdb_asset_edit", "name": "资产编辑", "content_type": content_type},
            {"codename": "perm_cmdb_business_view", "name": "业务（应用）查看", "content_type": content_type},
            {"codename": "perm_cmdb_business_edit", "name": "业务（应用）编辑", "content_type": content_type},

            {"codename": "perm_dns_zone_view", "name": "DNS域名查看", "content_type": content_type},
            {"codename": "perm_dns_zone_edit", "name": "DNS域名编辑", "content_type": content_type},
            {"codename": "perm_dns_record_view", "name": "DNS记录查看", "content_type": content_type},
            {"codename": "perm_dns_record_edit", "name": "DNS记录编辑", "content_type": content_type},
            {"codename": "perm_dns_log_view", "name": "DNS操作日志查看", "content_type": content_type},

            {"codename": "perm_ssh_host_user_view", "name": "SSH HostUser查看", "content_type": content_type},
            {"codename": "perm_ssh_host_user_edit", "name": "SSH HostUser编辑", "content_type": content_type},
            {"codename": "perm_ssh_perilous_cmd_view", "name": "SSH高危命令查看", "content_type": content_type},
            {"codename": "perm_ssh_perilous_cmd_edit", "name": "SSH高危命令编辑", "content_type": content_type},
            {"codename": "perm_ssh_perilous_cmd_grant_view", "name": "SSH高危命令授权查看", "content_type": content_type},
            {"codename": "perm_ssh_perilous_cmd_grant_edit", "name": "SSH高危命令授权编辑", "content_type": content_type},

            {"codename": "perm_job_job_execute", "name": "Job作业执行", "content_type": content_type},
            {"codename": "perm_job_job_view", "name": "Job作业查看", "content_type": content_type},
            {"codename": "perm_job_job_edit", "name": "Job作业编辑", "content_type": content_type},
            {"codename": "perm_job_cmd_execute", "name": "Job命令执行", "content_type": content_type},
            {"codename": "perm_job_file_upload", "name": "Job文件上传", "content_type": content_type},
            {"codename": "perm_job_file_download", "name": "Job文件下载", "content_type": content_type},
            {"codename": "perm_job_task_log", "name": "Job任务日志查看", "content_type": content_type},
            {"codename": "perm_job_job_log", "name": "Job作业日志查看", "content_type": content_type},
            {"codename": "perm_job_inventory_view", "name": "Job Inventory查看", "content_type": content_type},
            {"codename": "perm_job_inventory_edit", "name": "Job Inventory编辑", "content_type": content_type},
            {"codename": "perm_job_playbook_view", "name": "Job Playbook查看", "content_type": content_type},
            {"codename": "perm_job_playbook_edit", "name": "Job Playbook编辑", "content_type": content_type},
            {"codename": "perm_job_galaxy_view", "name": "Job Galaxy查看", "content_type": content_type},
            {"codename": "perm_job_galaxy_edit", "name": "Job Galaxy编辑", "content_type": content_type},
            {"codename": "perm_job_scripts_view", "name": "Job Scripts查看", "content_type": content_type},
            {"codename": "perm_job_scripts_edit", "name": "Job Scripts编辑", "content_type": content_type},
            {"codename": "perm_job_settings", "name": "Job全局设置", "content_type": content_type}
        ]:
            Permission.objects.create(**item)
        # 权限组
        Group.objects.create(id=1, name='默认组')
    except Exception as e:
        try:
            User.objects.filter(id=5000).delete()
            IDC.objects.filter(id=1).delete()
            BizMgtDept.objects.filter(id=1).delete()
            Permission.objects.filter(codename__startswith='perm_').delete()
            Group.objects.filter(id=1).delete()
        except Exception:
            pass
        return render(request, 'message.html', {'message': '失败：%s！' % str(e)})
    return render(request, 'message.html', {'message': '成功：OneOps初始化成功！'})

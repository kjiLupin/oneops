
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from cmdb.models.business import BizMgtDept

@login_required
def charts(request):
    path1, path2 = 'CMDB', '可视化'
    return render(request, 'cmdb/charts.html', locals())


@login_required
def charts_server(request):
    path1, path2 = 'CMDB', '服务器使用率'
    dept_name = request.GET.get('dept_name')
    pct_range = request.GET.get('pct_range')
    dept_list = BizMgtDept.objects.filter(parent_id=2)
    return render(request, 'cmdb/charts_server.html', locals())

from django.db import models
from accounts.models import User
from .business import BizMgtDept, App
from .base import IDC, Cabinet, Ip
# Create your models here.

ServerStatus = {
    'running': '运行中', 'down': '宕机', 'pause': '暂停', 'deleted': '已删除', 'ots': '已下架', 'loss': '未知', 'error': '错误'
}

NetDeviceType = {
    'l2-switch': '二层交换机', 'l3-switch': '三层交换机', 'fc-san-switch': '光纤交换机',
    'router': '路由器', 'firewall': '防火墙', 'load-balancer': '负载均衡'
}

NetDeviceVendor = {
    'cisco': '思科', 'h3c': '新华三', 'huawei': '华为', 'juniper': 'Juniper', 'f5': 'F5', 'a10': 'A10', 'brocade': 'Brocade'
}

NetDeviceOS = {
    'NX-OS': 'NX-OS', 'IOS': 'IOS', 'ASA': 'ASA', 'IOS-XE': 'IOS-XE', 'FOS': 'FOS'
}

AppEnv = {
    'unknown': '未知', 'dev': '开发', 'test': '测试', 'pre': '预发', 'beta': 'Beta', 'prod': '正式'
}


class Server(models.Model):
    asset_id = models.CharField('资产编号', max_length=50, blank=True, null=True)
    hostname = models.CharField(max_length=50)
    uuid = models.CharField(max_length=100)         # unique=True，也可添加唯一性约束。但有一些第三方设备无法获取uuid。
    cpu_total = models.IntegerField(blank=True, null=True)
    cpu_used = models.FloatField(blank=True, null=True)
    mem_total = models.CharField(max_length=20, blank=True, null=True)
    mem_used = models.FloatField(blank=True, null=True)
    disk = models.TextField('硬盘', default='')
    os = models.CharField('操作系统版本', max_length=100, blank=True, null=True)
    login_address = models.CharField('登陆地址', max_length=21, default='127.0.0.1:22')
    manage_address = models.CharField('管理地址', max_length=21, default='127.0.0.1:22')

    model = models.IntegerField('U数', blank=True, null=True)
    manufacturer = models.CharField('硬件供应商', max_length=100, blank=True, null=True)
    product_name = models.CharField('硬件产品型号', max_length=100, blank=True, null=True)
    release_date = models.DateField('硬件出厂时间', blank=True, null=True)
    trade_date = models.DateField('采购时间', blank=True, null=True)
    expired_date = models.DateField('过保时间', blank=True, null=True)
    sn = models.CharField('Serial number', max_length=100, blank=True, null=True)
    supplier = models.CharField('直接供应商，或代理商', max_length=30, blank=True, null=True)
    supplier_phone = models.CharField('直接供应商联系方式', max_length=20, blank=True, null=True)

    is_vm = models.BooleanField('是否虚拟机', default=False)
    vm_count = models.IntegerField('该宿主机的虚拟机数量', blank=True, null=True)
    parent_id = models.IntegerField('该虚拟机的宿主机id', blank=True, null=True)

    idc = models.ForeignKey(IDC, blank=True, null=True, on_delete=models.SET_NULL)
    cabinet = models.ForeignKey(Cabinet, blank=True, null=True, on_delete=models.DO_NOTHING, help_text='机柜')
    cabinet_pos = models.IntegerField('机柜槽位', blank=True, null=True)

    applicant = models.CharField('申请人及用途', max_length=30, blank=True, null=True)
    comment = models.CharField(max_length=256, blank=True, null=True)
    status = models.CharField(max_length=7, choices=ServerStatus.items(), default='loss')
    date_created = models.DateTimeField('上架时间/创建时间', auto_now_add=True)
    date_last_checked = models.DateTimeField(auto_now=True)

    department = models.ForeignKey(BizMgtDept, blank=True, null=True, on_delete=models.SET_NULL, help_text='机器所属业务部门')
    pre_app = models.ManyToManyField(App, blank=True, related_name='pre_app_server', help_text='待部署（预分配）应用')
    app = models.ManyToManyField(App, blank=True, related_name='app_server', help_text='已部署的应用')
    app_env = models.CharField(max_length=7, choices=AppEnv.items(), default='unknown')

    class Meta:
        db_table = 'cmdb_server'
        verbose_name = u'服务器表'
        verbose_name_plural = u'服务器表'


class Pod(models.Model):
    hostname = models.CharField(max_length=50)
    uuid = models.CharField(max_length=100)
    cpu = models.IntegerField(blank=True, null=True)
    memory = models.CharField(max_length=10, blank=True, null=True)
    ip = models.CharField('IP', max_length=15, blank=True, null=True)
    parent_id = models.IntegerField('该pod所属Node主机的id', blank=True, null=True)

    comment = models.CharField(max_length=256, blank=True, null=True)
    status = models.CharField(max_length=7, choices=ServerStatus.items(), default='loss')
    date_created = models.DateTimeField('上架时间/创建时间', auto_now_add=True)

    app = models.ManyToManyField(App, blank=True, help_text='已部署的应用')
    app_env = models.CharField(max_length=7, choices=AppEnv.items(), default='unknown')

    class Meta:
        db_table = 'cmdb_k8s_pod'
        verbose_name = u'K8s Pod表'
        verbose_name_plural = u'K8s Pod表'


class NetDevice(models.Model):
    """
    网络设备可拥有多个ip地址，但login_address应该是ssh或telnet地址。
    snmp 访问地址如：192.168.0.1:161
    """
    asset_id = models.CharField('资产编号', max_length=50, blank=True, null=True)
    sys_name = models.CharField(max_length=50, blank=True, null=True)
    login_type = models.CharField('登录方式', max_length=6, choices=(('ssh', 'SSH'), ('telnet', 'Telnet')))
    login_address = models.GenericIPAddressField('登陆地址', default='127.0.0.1')
    ip = models.ManyToManyField(Ip, blank=True)
    snmp = models.CharField('SNMP访问', max_length=26, blank=True, null=True)

    type = models.CharField(max_length=20, choices=NetDeviceType.items(), default='l3-switch')
    manufacturer = models.CharField('硬件供应商', max_length=20, choices=NetDeviceVendor.items(), default='cisco')
    os = models.CharField('操作系统', max_length=20, choices=NetDeviceOS.items(), default='IOS')
    product_name = models.CharField('产品型号', max_length=100, blank=True, null=True)
    trade_date = models.DateField('采购时间', blank=True, null=True)
    expired_date = models.DateField('过保时间', blank=True, null=True)
    sn = models.CharField('Serial number', max_length=50, blank=True, null=True)
    model = models.IntegerField('U数', blank=True, null=True)
    version = models.CharField('固件版本号', max_length=50, blank=True, null=True)

    idc = models.ForeignKey(IDC, blank=True, null=True, on_delete=models.SET_NULL)
    cabinet = models.ForeignKey(Cabinet, blank=True, null=True, on_delete=models.DO_NOTHING, help_text='机柜')
    cabinet_pos = models.IntegerField('机柜槽位', blank=True, null=True)

    supplier = models.CharField('直接供应商，或代理商', max_length=30, blank=True, null=True)
    supplier_phone = models.CharField('直接供应商联系方式', max_length=20, blank=True, null=True)

    comment = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=10, choices=(('unused', '未上架'), ('used', '已上架')), default='used')
    date_created = models.DateTimeField('上架时间/创建时间', auto_now_add=True)
    date_last_checked = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cmdb_netdev'
        verbose_name = u'网络设备表'
        verbose_name_plural = u'网络设备表'


class Nic(models.Model):
    nic_name = models.CharField(max_length=30, blank=True, null=True)
    mac_address = models.CharField(max_length=30)
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    ip = models.ManyToManyField(Ip, blank=True)
    date_last_checked = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.mac_address = self.mac_address.lower()
        super(Nic, self).save(*args, **kwargs)

    class Meta:
        db_table = 'cmdb_nic'
        unique_together = ('nic_name', 'mac_address')
        verbose_name = u'网卡表'
        verbose_name_plural = u'网卡表'


class Storage(models.Model):
    """
    Vmware Storage
    """
    server = models.ForeignKey(Server, blank=True, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=50, blank=True, null=True)
    total = models.PositiveIntegerField(blank=True, null=True)
    free = models.PositiveIntegerField(blank=True, null=True)
    used_pct = models.SmallIntegerField(blank=True, null=True)
    comment = models.CharField(max_length=50, blank=True, null=True)
    date_created = models.DateTimeField('上架时间/创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_storage'
        verbose_name = u'存储设备表'
        verbose_name_plural = u'存储设备表'


class Maintenance(models.Model):
    server = models.ForeignKey(Server, on_delete=models.CASCADE, help_text='服务器', blank=True, null=True)
    net_device = models.ForeignKey(NetDevice, on_delete=models.CASCADE, help_text='网络设备', blank=True, null=True)
    content = models.CharField('内容', max_length=250, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text='记录员')
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_asset_maint'
        verbose_name = u'设备维保记录表'
        verbose_name_plural = u'设备维保记录表'


class ServerResource(models.Model):
    s = models.ForeignKey(Server, on_delete=models.CASCADE, help_text='服务器')
    cpu_used = models.FloatField()
    mem_used = models.FloatField()
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cmdb_server_res'
        verbose_name = u'服务器资源历史表'
        verbose_name_plural = u'服务器资源历史表'


class AppResource(models.Model):
    s = models.ForeignKey(Server, on_delete=models.CASCADE, help_text='服务器')
    app = models.ForeignKey(App, on_delete=models.CASCADE, help_text='应用')
    xms = models.CharField('Xms', max_length=20, blank=True, null=True)
    xmx = models.CharField('Xmx', max_length=20, blank=True, null=True)
    date_last_checked = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cmdb_app_res'
        verbose_name = u'应用资源表'
        verbose_name_plural = u'应用资源表'

from django.db import models
from accounts.models import User
from cmdb.models.base import IDC
from cmdb.models.asset import Server, NetDevice


class CPU(models.Model):
    # Intel(R) Xeon(R) Gold 5118 CPU @ 2.30GHz
    version = models.CharField('型号版本', max_length=100, unique=True)
    speed = models.PositiveSmallIntegerField('频率MHz')
    process = models.PositiveSmallIntegerField('线程数')
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_cpu'
        verbose_name = u'配件CPU表'
        verbose_name_plural = u'配件CPU表'


class Memory(models.Model):
    ram_type = models.CharField('内存类型', max_length=4, choices=(('ddr3', 'DDR3'), ('ddr4', 'DDR4'), ('ddr5', 'DDR5')))
    ram_size = models.PositiveSmallIntegerField('内存容量（G）')
    speed = models.PositiveSmallIntegerField('速率（MT/s）')
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_memory'
        unique_together = ('ram_type', 'ram_size', 'speed')
        verbose_name = u'配件内存表'
        verbose_name_plural = u'配件内存表'


class Disk(models.Model):
    device_type = models.CharField('硬盘类型', max_length=4, choices=(('sata', 'SATA'), ('sas', 'SAS'), ('ssd', 'SSD')))
    capacity = models.PositiveSmallIntegerField('容量（G）')
    rpm = models.PositiveSmallIntegerField('转率')
    dimensions = models.CharField('尺寸（英寸）', max_length=3, choices=(('2.5', '2.5寸'), ('3.5', '3.5寸')))
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_disk'
        unique_together = ('device_type', 'capacity', 'rpm', 'dimensions')
        verbose_name = u'配件硬盘表'
        verbose_name_plural = u'配件硬盘表'


class Caddy(models.Model):
    caddy_dimensions = {
        '2.5s': '2.5寸 R740', '2.5': '2.5寸', '3.5': '3.5寸'
    }
    dimensions = models.CharField('尺寸（英寸）', max_length=4, choices=caddy_dimensions.items(), unique=True)
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_caddy'
        verbose_name = u'配件硬盘托架表'
        verbose_name_plural = u'配件硬盘托架表'


class NetworkAdapter(models.Model):
    speed = models.CharField('网卡速率', max_length=6, choices=(('100MbE', '百兆'), ('GbE', '千兆'), ('10GbE', '万兆')), unique=True)
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_network_adapter'
        verbose_name = u'配件网卡表'
        verbose_name_plural = u'配件网卡表'


class NetworkCable(models.Model):
    cat = models.CharField('网线类型', max_length=2, choices=(('5', '5类线'), ('5e', '超5类线'), ('6', '6类线'), ('6e', '超6类线')))
    length = models.PositiveSmallIntegerField('长度（米）')
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_network_cable'
        unique_together = ('cat', 'length')
        verbose_name = u'配件网线表'
        verbose_name_plural = u'配件网线表'


class OpticalTransceiver(models.Model):
    # Small form-factor pluggable transceiver 小型可插拔光模块
    """
    Mfg. Compatibility: Cisco
    Part Number: SFP-10G-LR-10pk
    Form Factor: SFP+
    TX Wavelength: 1310nm
    Reach: 10km
    Cable Type: SMF
    Rate Category: 10GBase
    Interface Type: LR
    DDM: Yes
    Connector Type: Dual-LC
    """
    information = models.CharField('综述介绍', max_length=20, blank=True, null=True)
    mode = models.CharField('模式', max_length=6, choices=(('single', '单模'), ('multi', '多模')))
    reach = models.FloatField('最大传输距离（km）')
    rate = models.CharField('传输速率', max_length=6, choices=(('100MbE', '百兆'), ('GbE', '千兆'), ('10GbE', '万兆')))
    image = models.ImageField(u'图片', upload_to='images/accessory/%Y%m%d', null=True, blank=True)
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_optical_transceiver'
        unique_together = ('mode', 'reach', 'rate')
        verbose_name = u'配件光模块表'
        verbose_name_plural = u'配件光模块表'


class JumpWire(models.Model):
    information = models.CharField('综述介绍', max_length=20, blank=True, null=True)
    mode = models.CharField('模式', max_length=6, choices=(('single', '单模'), ('multi', '多模')))
    interface = models.CharField('光纤接口', max_length=6, choices=(('lc', '小方头'), ('sc', '大方头'), ('fc', '圆头')))
    length = models.PositiveSmallIntegerField('长度（米）')
    image = models.ImageField(u'图片', upload_to='images/accessory/%Y%m%d', null=True, blank=True)
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_jump_wire'
        unique_together = ('mode', 'interface', 'length')
        verbose_name = u'配件跳线表'
        verbose_name_plural = u'配件跳线表'


accessory_item = {
    'cpu': 'CPU', 'memory': '内存', 'disk': '硬盘', 'caddy': '硬盘托架', 'network_adapter': '网卡', 'network_cable': '网线',
    'transceiver': '光模块', 'jump_wire': '跳线'
}


class Accessory(models.Model):
    storehouse = models.ForeignKey(IDC, on_delete=models.CASCADE, help_text='仓库')
    mode = models.CharField('配件类型', max_length=20, choices=accessory_item.items())
    mode_id = models.IntegerField('配件型号表主键ID')
    manufacturer = models.CharField('硬件制造商', max_length=20, blank=True, null=True)
    sn = models.CharField('Serial Number', max_length=50, blank=True, null=True)
    vendor = models.CharField('采购渠道（供应商）', max_length=20)
    trade_date = models.DateField('采购时间', blank=True, null=True)
    expired_date = models.DateField('过保时间', blank=True, null=True)
    comment = models.CharField('备注', max_length=50, blank=True, null=True)
    is_active = models.BooleanField('是否可用', default=True)
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_accessory'
        verbose_name = u'配件详细表'
        verbose_name_plural = u'配件详细表'


class UseRecord(models.Model):
    """
    CPU、内存、硬盘、网卡、光模块 配件，需要知道被哪个资产使用
    """
    accessory = models.ForeignKey(Accessory, on_delete=models.CASCADE, help_text='配件')
    server = models.ForeignKey(Server, on_delete=models.CASCADE, help_text='服务器', blank=True, null=True)
    net_device = models.ForeignKey(NetDevice, on_delete=models.CASCADE, help_text='网络设备', blank=True, null=True)
    operate = models.CharField('操作', max_length=7, choices=(('install', '安装'), ('remove', '取下')), default='install')
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_use_record'
        verbose_name = u'配件使用记录表'
        verbose_name_plural = u'配件使用记录表'


class InventoryRecord(models.Model):
    accessory = models.CharField('配件', max_length=20, choices=accessory_item.items())
    operate = models.CharField('操作', max_length=8, choices=(('purchase', '采购'), ('receive', '领用'), ('revert', '归还')))
    server = models.ForeignKey(Server, on_delete=models.CASCADE, help_text='服务器', blank=True, null=True)
    net_device = models.ForeignKey(NetDevice, on_delete=models.CASCADE, help_text='网络设备', blank=True, null=True)
    content = models.CharField('内容', max_length=250, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text='操作员')
    created_date = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'cmdb_acc_inventory_record'
        verbose_name = u'配件进货及消费记录表'
        verbose_name_plural = u'配件进货及消费记录表'

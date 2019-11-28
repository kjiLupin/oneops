# -*- coding: UTF-8 -*-
import simplejson as json
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from functools import singledispatch


@singledispatch
def convert(o):
    raise TypeError('Error: can not convert this type! -- %s' % type(o))


@convert.register(datetime)
def _(o):
    return o.strftime('%Y-%m-%d %H:%M:%S')


@convert.register(date)
def _(o):
    return o.strftime('%Y-%m-%d')


@convert.register(time)
def _(o):
    return o.strftime("%H:%M:%S %Z")


@convert.register(timedelta)
def _(o):
    return o.total_seconds()


@convert.register(Decimal)
def _(o):
    return str(o)


class DjangoOverRideJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # See "Date Time String Format" in the ECMA-262 specification.
        # http://www.ecma-international.org/ecma-262/5.1/#sec-15.9.1.15
        try:
            return convert(obj)
        except TypeError:
            return super(DjangoOverRideJSONEncoder, self).default(obj)


class MyClass:
    def __init__(self, value):
        self._value = value

    def get_value(self):
        return self._value


@convert.register(MyClass)
def _(o):
    return o.get_value()


# 创建非内置类型的实例
mc = MyClass('i am class MyClass ')
dm = Decimal('11.11')
dt = datetime.now()
dat = date.today()
data = {
    'mc': mc,
    'dm': dm,
    'dt': dt,
    'dat': dat,
    'tl': timedelta(minutes=30),
    'bigint': 988983860501598208
}

# print(json.dumps(data, cls=ExtendJSONEncoder, bigint_as_string=True))

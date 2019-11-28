
// 环境类型
env = {
    'dev': '开发环境',
    'test': '测试环境',
    'pre': '预发环境',
    'beta': 'Beta环境',
    'prod': '正式环境'
};

// 服务器状态
machine_status = {
    'running': '运行中',
    'down': '宕机',
    'pause': '暂停',
    'deleted': '已删除',
    'ots': '已下架',
    'loss': '未知',
    'error': '错误'
};

(function ($) {
    $.fn.serializeJson = function () {
        var serializeObj = {};
        $(this.serializeArray()).each(function () {
            serializeObj[this.name] = this.value;
        });
        return serializeObj;
    };
})(jQuery);

function getUrlParam(name) {
    var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)");
    var r = window.location.search.substr(1).match(reg);
    if (r != null) return unescape(r[2]);
    return null;
}

function substring(value, len) {
        value = value?value:'';
        if (value.length>len) {
            return "<span title ='"+value+"'>"+value.substring(0,len)+"...</span>"
        } else {
            return value
        }
}

function reShowForm(row, form) {
    $.each(row, function (key, value) {
        var input = $("#" + form).find("input[name='" + key + "']");
        if (input.length > 0) {
            $.each(input, function () {
                var type = $(this).attr('type');
                if ('checkbox' == type) {
                    if (1 == value) {
                        $(this).prop("checked", true);
                    } else {
                        $(this).prop("checked", false);
                    }
                } else if ('radio' == type) {
                    if ($(this).val() == value) {
                        $(this).prop('checked', true);
                    } else {
                        $(this).prop('checked', false);
                    }
                } else if (typeof(value) == "boolean") {
                    $(this).attr('value', value ? 1 : 0);
                } else {
                    $(this).attr('value', value);
                }
            });
        }
        var select = $("#" + form).find("select[name=" + key + "]");
        if (select.length > 0) {
            $.each(select, function () {
                $(this).val(value);
            });
        }
    });
}

function getVLan(props) {
    $.ajax({
        url: props.url,
        type: "get",
        data: {"idc_id": props.idc_id},
        success: function (data) {
            $('#' + props.select_id).empty();
            $.each(data["rows"], function (index, v) {
                if (v['id'] === props.vlan_id) {
                    var _html = "<option value='" + v['id'] + "' selected='selected'>" + v['vlan_num'] + "(" + v['comment'] + ")" + "</option>";
                } else {
                    var _html = "<option value='" + v['id'] + "' >" + v['vlan_num'] + "(" + v['comment'] + ")" + "</option>";
                }
                $('#' + props.select_id).append(_html);
            });
            if (props.vlan_id === null) {
                $('#' + props.select_id).prepend('<option value="is-empty" disabled="" selected="selected">VLan</option>');
            } else {
                $('#' + props.select_id).prepend('<option value="is-empty" disabled="">VLan</option>');
            }
            $('#' + props.select_id).selectpicker('render');
            $('#' + props.select_id).selectpicker('refresh');
        },
        error: function (res) {
            console.log(res);
            swal("操作失败", res, "error");
        }
    });
}

function getNetworkSegment(props) {
    $.ajax({
        url: props.url,
        type: "get",
        data: {"idc_id": props.idc_id, "vlan_id": props.vlan_id},
        success: function (data) {
            $('#' + props.select_id).empty();
            $.each(data["rows"], function (index, v) {
                if (v['id'] === props.segment_id) {
                    var _html = "<option value='" + v['id'] + "' selected='selected'>" + v['seg'] + "</option>";
                } else {
                    var _html = "<option value='" + v['id'] + "' >" + v['seg'] + "</option>";
                }
                $('#' + props.select_id).append(_html);
            });
            if (props.segment_id === null) {
                $('#' + props.select_id).prepend('<option value="is-empty" disabled="" selected="selected">网段</option>');
            } else {
                $('#' + props.select_id).prepend('<option value="is-empty" disabled="">网段</option>');
            }
            $('#' + props.select_id).selectpicker('render');
            $('#' + props.select_id).selectpicker('refresh');
        },
        error: function (res) {
            console.log(res);
            swal("操作失败", res, "error");
        }
    });
}
//
function getCabinet(props){
    $.ajax({
        url: props.url,
        type: "get",
        data: {"idc_id": props.idc_id},
        success: function (data) {
            $('#' + props.select_id + " option").remove();
            $.each(data, function (index, v) {
                if (v['id'] === props.cabinet_id) {
                    var _html = "<option value='" + v['id'] + "' selected='selected'>" + v['name'] + "</option>";
                } else {
                    var _html = "<option value='" + v['id'] + "' >" + v['name'] + "</option>";
                }
                $('#' + props.select_id).append(_html);
            });
            if (props.cabinet_id === null) {
                $('#' + props.select_id).prepend('<option value="is-empty" disabled="" selected="selected">机柜</option>');
            } else {
                $('#' + props.select_id).prepend('<option value="is-empty" disabled="">机柜</option>');
            }
            $('#' + props.select_id).selectpicker('render');
            $('#' + props.select_id).selectpicker('refresh');
        },
        error: function (res) {
            console.log(res);
            swal("操作失败", res, "error");
        }
    });
}

function getAvailableIp(props) {
    $.ajax({
        url: props.url,
        type: "get",
        data: {"available": "true", "segment_id": props.segment_id},
        success: function (data) {
            $('#addip option').remove();
            var length = data.length;
            for (var i = 0; i < length; i++) {
                var _html = "<option value='" + data[i] + "' >" + data[i] + "</option>";
                $('#addip').append(_html);
            }
            $('#addip').selectpicker('render');
            $('#addip').selectpicker('refresh');
        },
        error: function (res) {
            console.log(res);
            swal("操作失败", res, "error");
        }
    });
}

function getIp(props) {
    $.ajax({
        url: props.url,
        type: "get",
        data: {"available": "true", "segment_id": props.segment_id},
        success: function (data) {
            $('#' + props.select_id).empty();
            var length = data.length;
            for (var i = 0; i < length; i++) {
                var _html = "<option value='" + data[i] + "' >" + data[i] + "</option>";
                $('#' + props.select_id).append(_html);
            }
            if (props.ip == null) {
                $('#' + props.select_id).prepend('<option value="is-empty" disabled="">IP</option>');
            } else {
                $('#' + props.select_id).prepend('<option value="'+props.ip+'" selected="selected">'+props.ip+'</option>');
            }
            $('#' + props.select_id).selectpicker('render');
            $('#' + props.select_id).selectpicker('refresh');
        },
        error: function (res) {
            console.log(res);
            swal("操作失败", res, "error");
        }
    });
}

function getOaUser(props) {
    $.ajax({
        url: props.url,
        type: "get",
        success: function (data) {
            var email1 = props.email1 ? props.email1.split(","):[];
            $('#' + props.select_id1).empty();
            $.each(data['result'], function (index, v) {
                if (email1.indexOf(v['k']) != -1) {
                    var _html = "<option value='" + v['k'] + "' selected>" + v['v'] + "</option>";
                } else {
                    var _html = "<option value='" + v['k'] + "' >" + v['v'] + "</option>";
                }
                $('#' + props.select_id1).append(_html);
            });
            $('#' + props.select_id1).selectpicker('render');
            $('#' + props.select_id1).selectpicker('refresh');
            var email2 = props.email2 ? props.email2.split(","):[];
            $('#' + props.select_id2).empty();
            $.each(data['result'], function (index, v) {
                if (email2.indexOf(v['k']) != -1) {
                    var _html = "<option value='" + v['k'] + "' selected>" + v['v'] + "</option>";
                } else {
                    var _html = "<option value='" + v['k'] + "' >" + v['v'] + "</option>";
                }
                $('#' + props.select_id2).append(_html);
            });
            $('#' + props.select_id2).selectpicker('render');
            $('#' + props.select_id2).selectpicker('refresh');
        },
        error: function (res) {
            console.log(res);
            swal("操作失败", res, "error");
        }
    });
}

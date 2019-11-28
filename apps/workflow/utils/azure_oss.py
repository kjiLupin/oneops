# -*- coding: utf-8 -*-
import os
import time
from common.utils.base import BASE_DIR
from azure.storage.blob import BlockBlobService, PublicAccess


def upload_apk_to_azure_oss(oss, files):
    today = time.strftime("%Y-%m-%d", time.localtime())
    apk_temp_dir = os.path.join(BASE_DIR, "logs", today)
    if not os.path.exists(apk_temp_dir):
        os.mkdir(apk_temp_dir)
    success, fail = [], []
    block_blob_service = BlockBlobService(account_name=oss.account, account_key=oss.secret,
                                          endpoint_suffix=oss.end_point)
    for f in files:
        file_path = os.path.join(apk_temp_dir, f.name)

        with open(file_path, 'wb+') as info:
            for chunk in f.chunks():
                info.write(chunk)
        try:
            block_blob_service.create_blob_from_path(oss.container, f.name, file_path)
            success.append("%s Succeeded：https://kuailehua.blob.core.chinacloudapi.cn/kuailehua/%s" % (f.name, f.name))
        except Exception as e:
            fail.append("%s Failed：%s" % (f.name, str(e)))
    fail.extend(success)
    return fail

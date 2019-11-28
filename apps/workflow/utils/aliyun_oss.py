# -*- coding: utf-8 -*-
import os
import time
import oss2
from common.utils.base import BASE_DIR


def upload_apk_to_ali_oss(oss, files):
    auth = oss2.Auth(oss.account, oss.secret)
    bucket = oss2.Bucket(auth, oss.end_point, oss.container)

    today = time.strftime("%Y-%m-%d", time.localtime())
    apk_temp_dir = os.path.join(BASE_DIR, "logs", today)
    if not os.path.exists(apk_temp_dir):
        os.mkdir(apk_temp_dir)
    success, fail = [], []

    for f in files:
        file_path = os.path.join(apk_temp_dir, f.name)

        with open(file_path, 'wb+') as info:
            for chunk in f.chunks():
                info.write(chunk)

        if 'clapp_release.apk' == f.name:
            oss_path = 'clapp/%s' % f.name
        elif 'yunshandai.apk' == f.name:
            oss_path = 'clapp/%s' % f.name
        elif '.apk' in f.name:
            if 'weiyirong' in f.name:
                oss_path = 'weiyirong.apk'
            else:
                oss_path = f.name
        elif 'clapp_release.plist' == f.name:
            oss_path = 'clapp/ios/%s' % f.name
        elif 'clapp_release.ipa' == f.name:
            oss_path = 'clapp/ios/%s' % f.name
        elif 'Clerk.ipa' == f.name:
            oss_path = 'dwsoft/Clerk/%s' % f.name
        elif 'Clerk-cl.ipa' == f.name:
            oss_path = 'dwsoft/Clerk-cl/%s' % f.name
        elif 'HybridStandard-InHouse.ipa' == f.name:
            oss_path = 'wdb/prod/%s' % f.name
        elif 'HybridStandard-Dev.ipa' == f.name:
            oss_path = 'wdb/test/%s' % f.name
        else:
            fail.append("%s：找不到该软件包的上传规则！" % f.name)
            continue
        resp = bucket.put_object_from_file(oss_path, os.path.abspath(file_path))
        if resp.status == 200:
            success.append("%s Succeeded：https://oss.yadoom.com/%s" % (f.name, oss_path))
        else:
            fail.append("%s Failed：%s" % (f.name, resp.read()))
    fail.extend(success)
    return fail


class AliOSSManager(object):

    def __init__(self, oss):
        self.auth = oss2.Auth(oss.account, oss.secret)
        self.bucket = oss2.Bucket(self.auth, oss.end_point, oss.container)

    def search(self, prefix):
        m_list = []
        for obj in oss2.ObjectIterator(self.bucket, prefix=prefix):
            m_list.append(obj.key)
        return m_list

    def put_file(self, key, file_path):
        result = self.bucket.put_object_from_file(key, file_path)
        return result.status

    def del_file(self, key):
        result = self.bucket.delete_object(key)
        return result.status

    def del_mfile(self, key):
        result = self.bucket.batch_delete_objects(key)
        return '\n'.join(result.deleted_keys)

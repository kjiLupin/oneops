# -*- coding: utf-8 -*-
import jenkins
import traceback

jenkins_server_url = 'http://192.168.16.158:8085'
user_id = 'yunwei'
api_token = '4617815c9ea96b98b4061f5f850730ff'


def check_status(job_name):
    try:
        server = jenkins.Jenkins(jenkins_server_url, username=user_id, password=api_token)
        job_num = server.get_job_info(job_name)['lastBuild']['number']
        job_building = server.get_build_info(job_name, job_num)['building']
        job_result = server.get_build_info(job_name, job_num)['result']
        if not job_building and job_result == 'SUCCESS':
            return True
        else:
            return False
    except:
        print(traceback.print_exc())
        return False


def build_job_old(job_name, param):
    server = jenkins.Jenkins(jenkins_server_url, username=user_id, password=api_token)
    server.build_job(job_name, parameters=param)
    job_num = server.get_job_info(job_name)['lastBuild']['number']
    app_num = int(job_num) + 1
    return app_num


def build_job(job_name, param):
    server = jenkins.Jenkins(jenkins_server_url, username=user_id, password=api_token)
    queue_item = server.build_job(job_name, parameters=param)
    print(queue_item)

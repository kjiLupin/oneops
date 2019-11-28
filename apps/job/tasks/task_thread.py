# encoding:utf-8

import threading
import queue
import datetime
from .paramiko_runner import MyTaskRunner
from job.models.job import TaskLog


class WorkManager(object):
    def __init__(self, task, thread_num=8):
        self.work_queue = queue.Queue()
        self.threads = []
        self.task = task
        self.__init_work_queue()
        self.__init_thread_pool(thread_num)

    def __init_thread_pool(self, thread_num):
        """
        初始化任务队列
        :param thread_num:线程数量
        :return:
        """
        for i in range(thread_num):
            self.threads.append(Work(self.work_queue))

    def __init_work_queue(self):
        """
        按照类型执行分类操作
        :return:
        """
        task_log_list = TaskLog.objects.filter(task_id=self.task.id).exclude(status='failed')
        if self.task.task_type == "upload":
            for task_log in task_log_list:
                self.add_job(self.do_upload, task_log)
        elif self.task.task_type == "download":
            for task_log in task_log_list:
                self.add_job(self.do_download, task_log)
        else:
            for task_log in task_log_list:
                self.add_job(self.do_command, task_log)

    def add_job(self, func, task):
        """
        添加任务到queue中
        :param func:回调函数
        :param task:任务对象
        :return:
        """
        self.work_queue.put((func, task))

    def wait_all_complete(self):
        """
        等待所有任务结束
        :return:
        """
        for item in self.threads:
            if item.isAlive():
                item.join()

    @staticmethod
    def save_task_start_status(task_log):
        """
        将任务状态置为运行中
        :param task_log:任务
        :return:
        """
        task_log.start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_log.status = 'executing'
        task_log.save(update_fields=['start_time', 'status'])

    def do_upload(self, task_log):
        """
        执行上传操作
        :param task_log:任务
        :return:
        """
        self.save_task_start_status(task_log)
        try:
            runner = MyTaskRunner(task.host_id, task.hostuser_id, task.id)
            res = runner.get_connect()
            des_file = ''
            for file_name in task.task.source_file.split("|"):
                des_file += task.task.des_file + '/' + file_name + ' '
            if res == "":
                r, s = runner.exec_command("echo $LANG")
                if "." in r:
                    _code = str(r.split(".")[1])
                else:
                    _code = "UTF-8"
                cmd = "/bin/cp %s /tmp/ 2>/dev/null" % des_file
                r, s = runner.exec_command(cmd.encode(_code))
                connect_result = runner.get_sftp()
                if connect_result == '':
                    cmd_result, res_status = runner.exec_upload(self.task.source_file, self.task.des_file, _code)
                    runner.save_batch_task(cmd_result, res_status)
                else:
                    runner.save_batch_task(connect_result, 'failed')
            else:
                runner.save_batch_task(res, 'failed')
        except Exception as e:
            runner.save_batch_task(e, 'failed')

    def do_download(self, task_log):
        """
        执行下载操作
        :param task_log:任务
        :return:
        """
        self.save_task_start_status(task_log)
        runner = MyTaskRunner(task.host_id, task.hostuser_id, task.id)
        try:
            res = runner.get_connect()
            if res == "":
                r, s = runner.exec_command("echo $LANG")
                if "." in r:
                    _code = str(r.split(".")[1])
                else:
                    _code = "UTF-8"
                connect_result = runner.get_sftp()
                if connect_result == '':
                    cmd_result, res_status = runner.exec_download(self.task.source_file, self.task.des_file, _code)
                    runner.save_batch_task(cmd_result, res_status)
                else:
                    runner.save_batch_task(connect_result, 'failed')
            else:
                runner.save_batch_task(res, 'failed')
        except Exception as e:
            runner.save_batch_task(e, 'failed')

    def do_command(self, task_log):
        """
        执行命令
        :param task:任务
        :return:
        """
        self.save_task_start_status(task)
        runner = MyTaskRunner(task.host_id, task.hostuser_id, task.id)
        try:
            connect_result = runner.get_connect()
            if connect_result == '':
                r, s = runner.exec_command("echo $LANG")
                if "." in r:
                    _code = str(r.split(".")[1])
                else:
                    _code = "UTF-8"
                cmd_result, res_status = runner.exec_command(task.cmd.encode(_code), _code)
                runner.save_batch_task(cmd_result, res_status)
            else:
                runner.save_batch_task(connect_result, 'failed')
        except Exception as e:
            runner.save_batch_task(e, 'failed')


class Work(threading.Thread):
    def __init__(self, work_queue):
        threading.Thread.__init__(self)
        self.work_queue = work_queue
        self.start()

    def run(self):
        while True:
            try:
                do, args = self.work_queue.get(block=False)
                do(args)
                self.work_queue.task_done()
            except:
                break


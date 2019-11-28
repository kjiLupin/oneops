import os
import multiprocessing
import configparser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

cfg = configparser.ConfigParser()
cfg.read(os.path.join(BASE_DIR, 'wdoneops.conf'))

bind = "{}:{}".format(cfg.get('base', 'ip'), cfg.get('base', 'port'))
workers = multiprocessing.cpu_count() * 2 + 1
errorlog = 'logs/gunicorn.error.log'
accesslog = 'logs/gunicorn.access.log'
loglevel = 'debug'
proc_name = 'wd-oneops'
limit_request_line = 8190
reload = True
daemon = True

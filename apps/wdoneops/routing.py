# https://mp.weixin.qq.com/s/hqaPrPS7w3D-9SeegQAB2Q
# https://github.com/ops-coffee/demo/tree/master/websocket

from django.urls import path, re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from job.ws.consumer import AdHocConsumer, PlaybookConsumer, JobConsumer, AppConsumer

application = ProtocolTypeRouter({

    "websocket": AuthMiddlewareStack(
        URLRouter([
            # URLRouter just takes standard Django path() or url() entries.
            path(r'ws/ansible/ad_hoc/', AdHocConsumer),
            path(r'ws/ansible/playbook/', PlaybookConsumer),
            path(r'ws/ansible/job/', JobConsumer, name='job_consumer'),
            path(r'ws/ansible/app/', AppConsumer, name='app_consumer'),
        ]),
    ),
})

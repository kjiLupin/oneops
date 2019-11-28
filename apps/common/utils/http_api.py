import requests


class HttpRequests(object):
    def __init__(self, timeout=None):
        self.timeout = 3 if timeout is None else timeout

    def get(self, url, headers=None):
        try:
            if headers is None:
                resp = requests.get(url, timeout=self.timeout)
            else:
                resp = requests.get(url, headers=headers, timeout=self.timeout)

            status = True if resp.status_code < 400 else False

            return status, str(resp.content, encoding="utf8")
        except Exception as e:
            return False, str(e)

    def post(self, url, params, headers=None):
        try:
            if headers is None:
                resp = requests.post(url, data=params, timeout=self.timeout)
            else:
                resp = requests.post(url, headers=headers, data=params, timeout=self.timeout)
            status = True if resp.status_code < 400 else False

            return status, str(resp.content, encoding="utf8")
        except Exception as e:
            return False, str(e)

    def put(self, url, params, headers=None):
        try:
            if headers is None:
                resp = requests.put(url, data=params, timeout=self.timeout)
            else:
                resp = requests.put(url, headers=headers, data=params, timeout=self.timeout)
            status = True if resp.status_code < 400 else False

            return status, str(resp.content, encoding="utf8")
        except Exception as e:
            return False, str(e)

http_request = HttpRequests(timeout=30)

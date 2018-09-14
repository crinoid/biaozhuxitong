# coding=utf8

import json
import requests

url = 'http://127.0.0.1:8001/service'

def post(data):
    headers = {'content-type': 'application/json'}
    r = requests.post(url, data=data, headers=headers).text
    return r

print post(json.dumps({"diag":["头部血管治疗性超声"]}))


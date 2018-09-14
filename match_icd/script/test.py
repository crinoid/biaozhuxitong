# coding=utf8

import requests
import json
import utils

SERVICE_URL = "http://127.0.0.1:8003/match_icd"
SERVICE_URL_WITH_CODE = "http://127.0.0.1:8003/match_icd_with_code"
HEADERS = {'content-type': 'application/json'}

res = requests.post(SERVICE_URL, data=json.dumps(
    {"diag":["肋骨骨折"],"source":["LC"],"dbname":"zhenduan"}),
                    headers=HEADERS).content.decode('utf8')

print res

res = requests.post(SERVICE_URL_WITH_CODE, data=json.dumps(
    {"diag":["55.0100"],"source":["LC","BJ"],"dbname":"shoushu"}),
                    headers=HEADERS).content.decode('utf8')

print res
# coding=utf8

import requests
import json

import time
SERVICE_URL1 = "http://127.0.0.1:8003/match_icd"
SERVICE_URL2 = "http://127.0.0.1:8003/match_icd_with_code"
HEADERS = {'content-type': 'application/json'}

res = requests.post(SERVICE_URL1, data=json.dumps(
    {"diag": ["小阴唇囊肿剥除术后"], "source": ["LC"], "dbname": "zhenduan", "size": 5}),
                    headers=HEADERS).text

print res
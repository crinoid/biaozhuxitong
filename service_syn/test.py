# coding=utf8

import json
import requests
import pandas as pd

IP = 'http://127.0.0.1:8007'
url = IP + '/match_syn'


def post(data, url):
    headers = {'content-type': 'application/json'}
    r = requests.post(url, data=data, headers=headers).text
    return r


print post(json.dumps({"term": ["鼻出血","牙龈肿","鼻出血"]}), url=url)

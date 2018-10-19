# coding=utf8

import json
import requests
import pandas as pd

# IP = 'http://127.0.0.1:8002'
IP = 'http://172.19.19.91:8002'
url = IP + '/service' # 分词标注一体
seg_url_return_array = IP + '/seg'  # 分词，返回数组，用于文件分词
seg_url = IP + '/seg_service'  # 分词，返回dict，用于标注系统
sug_url = IP + '/sug_service'  # 标注，返回dict


def post(data, url):
    headers = {'content-type': 'application/json'}
    r = requests.post(url, data=data, headers=headers).text
    return r


def seg(d):
    return " ".join(eval(post(json.dumps({"diag": [d]}), url))["diag"][d])


def remove_space(data):
    return data.strip()


def load_file(path):
    return map(remove_space, open(path).readlines())


def load_csv(path, sep, col):
    df = pd.read_csv(path, sep=sep)
    # df = df[col].apply(seg)
    return df[col]


def write(data, outfile):
    f = open(outfile, "w")
    for d in data:
        f.write(d + "\n")

# print requests.post(IP + '/update_seg',data="", headers={'content-type': 'application/json'})
# print requests.post(IP + '/update_sug',data="", headers={'content-type': 'application/json'})
# print post(json.dumps({"diag": ["高血压2级","患有糖尿病"]}), url=seg_url)
# print post(json.dumps({"高血压2级": "高血压/2级"}), url=sug_url)
# print post(json.dumps({"diag": ["高血压2级"]}), url=seg_url_return_array)

import base64
print base64.b64decode(post(json.dumps({"diag": ["高血压2级"],"encode":True}), url=url))


# result_sug={u"高血压":[u"2级"]}
# r = json.dumps(result_sug, ensure_ascii=True)
# print r,type(r)
# r1 = {"高血压":["2级"]}
# r1 = json.dumps(r1, ensure_ascii=False)
# print str(r1),type(str(r1))
# s = base64.b64encode(r1)
# print base64.b64decode(s)
# print base64.b64encode(u"个")

# def post_xml(data,headers):
#     r = requests.post('http://172.19.19.91:8002/service_xml', data=data, headers=headers).text
#     return r
#
# print post_xml(json.dumps({"diag":["高血压2级"]}),headers_json)


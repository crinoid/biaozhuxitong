# coding=utf8

import json
import requests
import pandas as pd
import xlrd

# IP = 'http://111.205.6.237:8006'
# IP = 'http://172.19.19.91:8006'
IP = 'http://127.0.0.1:8006'
url = IP + '/service' # 分词标注一体
seg_url_return_array = IP + '/seg'  # 分词，返回数组，用于文件分词
seg_url = IP + '/seg_service'  # 分词，返回dict，用于标注系统
sug_url = IP + '/sug_service'  # 标注，返回dict


def post(data, url):
    headers = {'content-type': 'application/json'}
    r = requests.post(url, data=data, headers=headers).text
    return r


def seg_sug(d):
    return eval(post(json.dumps({"diag": d}), url))


def remove_space(data):
    return data.strip()


def load_file(path):
    return map(remove_space, open(path).readlines())


def load_csv(path, sep, col):
    df = pd.read_csv(path, sep=sep)
    # df = df[col].apply(seg)
    return df[col]

def load_excel(path,col):
    wb = xlrd.open_workbook(path)
    ws = wb.sheets()[0]
    return ws.col_values(col)


def write(data, outfile):
    f = open(outfile, "w")
    for d in data:
        f.write(d + "\n")

# print requests.post(IP + '/update_seg',data="", headers={'content-type': 'application/json'})
# print requests.post(IP + '/update_sug',data="", headers={'content-type': 'application/json'})
# print post(json.dumps({"diag": ["高血压2级","患有糖尿病"]}), url=seg_url)
# print post(json.dumps({"高血压2级": "高血压/2级"}), url=sug_url)
print post(json.dumps({"diag": ["泪囊"]}), url=url)

# import base64
# print base64.b64decode(post(json.dumps({"diag": ["高血压2级"],"encode":True}), url=url))

# lines = load_file("uploads/11字符.txt")
# lines = load_excel("uploads/11字符.xls",0)
# print len(lines)
#
# types = ["部位","中心词","特征词","病因","病理","判断词","连接词","药品","其他","未知"]
# f = open("测试数据.csv","aw")
# f.write("原文\t")
# f.write("\t".join(types)+"\n")
# for i in seg_sug(lines[5000:]):
#     f.write(i["原文"]+"\t")
#     r = []
#     for t in types:
#         if t in i.keys():
#             r.append(" ".join(i[t]))
#         else:
#             r.append(" ")
#     f.write("\t".join(r)+"\n")
#

# import pandas as pd
# df=pd.read_csv('/Users/zhang/Desktop/临床诊断分词结果/20字符及以上.csv',sep="\t",encoding='utf8')
# df.to_excel("/Users/zhang/Desktop/临床诊断分词结果/20字符及以上.xls")
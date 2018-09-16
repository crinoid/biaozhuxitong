# coding=utf8

from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
import requests
import json
import os

from utils import utils
from utils import dbinfo
from database.base import MongoDatabase

from elasticsearch2 import Elasticsearch
from elasticsearch2 import helpers

# ICD_SOURCE = "icd_source.txt"

es = Elasticsearch()
ES_SERVERS = [{
    'host': 'localhost',
    'port': 9200
}]
es_client = Elasticsearch(
    hosts=ES_SERVERS
)

mongod = MongoDatabase()

icds = {}  # icds:{zd_lc:[],zd_gb:[]...}


def icd_page(request):
    return render_to_response("match_icd.html", "")


def icd_code_page(request):
    return render_to_response("match_icd_with_code.html", "")


def upload_diag(request):
    '''
    上传诊断文件
    :param request:
    :return: 文件内容
    '''
    if request.method == "POST":  # 请求方法为POST时，进行处理
        myFile = request.FILES.get("myfile", None)  # 获取上传的文件，如果没有文件，则默认为None
        upload_filename = utils.random_string() + "." + myFile.name.split(".")[-1]
        if not myFile:
            return "请上传文件!"
        ext = upload_filename.split(".")[-1]

        utils.write_to_file(myFile, os.path.join(utils.DIR_UPLOADS, upload_filename), ext)

        mongod.insert_diag_file({"code": upload_filename, "file": myFile.name})
        files = load_files()

        return HttpResponse(json.dumps({"diag_files": files, "diag": load_diag(upload_filename)}),
                            content_type='application/json')


def get_diag_files():
    '''
    所有诊断文件
    :return:
    '''
    return mongod.get_diag_file()


def show_diag_file(request):
    if request.method == "POST":
        code = request.POST.get("code", "")

        return HttpResponse(json.dumps({"diag": load_diag(code)}), content_type='application/json')


def delete_diag_file(request):
    if request.method == "POST":
        code = request.POST.get("code", "")
        mongod.delete_diag_file(code)
        files = load_files()

        return HttpResponse(json.dumps({"diag_files": files}), content_type='application/json')


def load_diag(filename):
    if filename:
        lines = []
        # 去掉空行
        for line in open(os.path.join("uploads/", filename)).readlines():
            if line.strip():
                lines.append(line)
        return lines
    return ""


def submit_icd(request):
    '''
    更新诊断-icd
    :param request:
    :return:
    '''
    if request.method == "POST":
        match = eval(request.POST.get("match", ""))  # {高血压:{gb:{icd:高血压,code:I00}}

        mongod = MongoDatabase()
        for k, v in match.iteritems():
            new_match = {}  # {diag:高血压,match:{gb:{高血压：I00}}}}
            new_match[dbinfo.DIAG] = k
            new_match[dbinfo.MATCH] = {}
            for k1, v1 in v.iteritems():
                if v1["icd"] and v1["code"]:
                    new_match[dbinfo.MATCH][k1] = {v1["icd"]: v1["code"]}
            mongod.insert_icd_match(new_match)
        return HttpResponse("", content_type='application/text')


def load_source(request):
    '''
    在诊断-icd匹配和匹配管理中，从icd_source.txt加载icd来源
    诊断-icd匹配，默认所有来源全选
    匹配管理，默认选中第一个来源（单选）
    :param request:
    :return:
    '''
    if request.method == "POST":
        is_radio = request.POST.get("radio", "")
        db = request.POST.get("db", "")
        source_dic = {}

        ischeck = {}
        config = json.load(open("config.json"))
        for abbr, name in config['icd'][db].iteritems():
            source_dic[name] = abbr
            ischeck[abbr] = "" if is_radio else "checked"
        # for line in open(ICD_SOURCE).readlines():
        #     if db in line:
        #         t, k, v = line.strip().split(" ")
        #         if t == db:
        #             source_dic[v] = k
        #             ischeck[k] = "false" if is_radio else "true"

        if is_radio and ischeck:
            ischeck[ischeck.keys()[0]] = "checked"

        files = load_files()

        return HttpResponse(json.dumps({"source": source_dic, "ischeck": ischeck, "diag_files": files}),
                            content_type='application/json')


def load_files():
    '''
    获取所有诊断匹配文件
    :return:
    '''
    files = []
    for f in get_diag_files():
        files.append({"file": f["file"], "code": f["code"]})
    return files


def match_icd(request):
    if request.method == "POST":
        dis = request.POST.get("dis", "")
        source_list = eval(request.POST.get("source_list", ""))
        dbname = request.POST.get("db", "")

        res = requests.post(utils.match_icd_url,
                            data=json.dumps({"diag": [dis], "source": source_list, "dbname": dbname}),
                            headers=utils.headers).content.decode('utf8')
        res = eval(res)  # [icd,icd_code,score]

        for k, v in res.iteritems():
            for i in range(len(v)):
                v[i].append(get_match_characters(v[i][0], dis))
                res[k][i] = v[i]

        return HttpResponse(json.dumps(res), content_type='application/json')


def match_icd_with_code(request):
    if request.method == "POST":
        icd = request.POST.get("icd", "")
        code = request.POST.get("code", "")
        code = code.upper()  # 首字母大写
        source_list = eval(request.POST.get("source_list", ""))
        dbname = request.POST.get("db", "")

        post_data = json.dumps({"diag": {icd: code}, "source": source_list, "dbname": dbname})
        if icd == "":  # 只输入了code
            post_data = json.dumps({"diag": [code], "source": source_list, "dbname": dbname})

        res = requests.post(utils.match_icd_code_url, data=post_data, headers=utils.headers).content.decode('utf8')
        res = eval(res)  # [icd,icd_code,score]

        if icd:
            for k, v in res.iteritems():
                for i in range(len(v)):
                    v[i].append(get_match_characters(v[i][0], icd))
                    res[k][i] = v[i]
        else:
            res = res[code]

        return HttpResponse(json.dumps(res), content_type='application/json')


def get_match_characters(a, b):
    a = a.decode('utf8')  # str->unicode
    list1 = [x for x in a]
    list2 = [x for x in b]

    c = set(list1) & set(list2)

    return list(c)


def show_hint(request):
    '''
    在搜索框输入，调用此方法，智能提示
    :param request:
    :return: {霍乱:A00.900，霍乱轻型:A00.900x002}
    '''

    if request.method == "POST":
        prefix = request.POST.get("prefix")  # 诊断/手术
        prefix = "zd" if prefix == "zhenduan" else "ss"
        index = request.POST.get("index")  # 选择的分类
        source = prefix + "-" + index
        keyword = request.POST.get("keyword")

        res = search_items(keyword, icds, source)

        res = res[:utils.ICD_MATCH_COUNT] if len(res) > utils.ICD_MATCH_COUNT else res

        data = {}
        for r in res:
            icd, code = r.split("(")
            data[icd] = code
        # 取前n个匹配值
        return HttpResponse(json.dumps({"res": data}), content_type='application/json')


def search_items(keyword, icds, source):
    '''
    返回匹配的条目，开头匹配
    :param keyword:
    :param icds:
    :return:
    '''

    def match(icd):
        return icd.find(keyword) == 0

    return filter(match, icds[source])


def search_from_keyword(request):
    '''
    根据搜索内容显示匹配的icd条目
    :param request:
    :return:
    '''
    if request.method == "POST":
        prefix = request.POST.get("prefix")  # 诊断/手术
        prefix = "zd" if prefix == "zhenduan" else "ss"
        index = request.POST.get("index")  # 选择的分类
        keyword = request.POST.get("keyword")

        res = {}
        i = 0
        for s in search(prefix + "-" + index, keyword, utils.ICD_MATCH_COUNT):
            icd, code = s["_source"]["icd"], s["_source"]["code"]
            res[i] = [icd, code]
            i += 1

        return HttpResponse(json.dumps({"res": res}), content_type='application/json')


def search_all(index):
    res = helpers.scan(
        client=es_client,
        query={"query": {"match_all": {}}},
        scroll="5m",
        index=index
    )
    return res


def search(index, keyword, size=utils.ICD_MATCH_COUNT):
    '''
    按icd,code搜索
    :param index: 数据库名
    :param keyword: 查找关键词
    :param size: 返回结果数（config.txt里定义）
    :return:
    '''
    # res = es.search(index=index, body={"query": {"match": {"icd":keyword}},"size":size})
    res = es.search(index=index, body={
        # "query": {"multi_match": {
        #     "query": keyword,
        #     "fields": ["icd"]
        # }},

        # 优先匹配内容
        "query": {
            "bool": {
                "should": [
                    {
                        "match": {
                            "icd": {
                                "query": keyword,
                                "boost": 5
                            }
                        }
                    },
                    {
                        "match": {
                            "code": {
                                "query": keyword,
                                "boost": 1
                            }
                        }
                    }
                ]
            }
        },
        "size": size,
    })
    return res["hits"]["hits"]


# def search(index,keyword,size=10):
#     # 添加highlight,高亮部分在<em></em>标签中
#     # return res[_source][icd]匹配结果 res[highlight][icd][0]为高亮匹配结果
#     res = es.search(index=index, body={
#         "query": {"match_phrase": {"icd":keyword}},
#         "size":size,
#         "highlight": {
#             "fields": {
#                 "icd": {}
#             }
#         }
#     })
#     return res["hits"]["hits"]

# 用于智能提示，一次全加载还是？

def compile_config_source(item):
    if item == "zhenduan":
        return "zd"
    if item == "shoushu":
        return "ss"
    else:
        return item.lower()


source_list = []

ischeck = {}
config = json.load(open("config.json"))
for db, v in config['icd'].iteritems():
    for abbr,name in v.iteritems():
        source_list.append(compile_config_source(db) + "-icd-" + compile_config_source(abbr))

# for line in open(ICD_SOURCE).readlines():
#     t, k, v = line.strip().split(" ")
#     source_list.append(compile_config_source(t) + "-icd-" + compile_config_source(k))

for source in source_list:
    icds_all = search_all(source)
    icd_list = []
    for s in icds_all:
        icd, code = s["_source"]["icd"], s["_source"]["code"]
        icd_list.append(icd + "(" + code)
    icds[source] = icd_list

# coding=utf8
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect

from utils import utils
from utils import dbinfo

import os
import time
import xlrd, xlwt
import logging
import json
from users.views import log_authority, new_data_authority, origin_data_authority
import requests
import sys


# import gensim

# bcjl_model = gensim.models.Word2Vec.load("bcjl_size200.model")

def main_page(request):
    '''
    起始页
    :param request:
    :return:
    '''
    if not utils.check_user_session(request):
        return HttpResponseRedirect("/login/")
    else:
        # 所选术语集类型
        if utils.SESSION_ORIGIN_FILE in request.session.keys():
            del request.session[utils.SESSION_ORIGIN_FILE]
        if utils.SESSION_DB not in request.session.keys():
            request.session[utils.SESSION_DB] = "zhenduan"

        request.session[utils.SESSION_TERMTYPE] = "diagnose_page"
        return render_to_response("index.html", "")


def get_session(request):
    '''
    登录后，更新用户名session，获得用户权限
    :param request:
    :return:
    '''
    if request.method == "POST":
        utils.update_db(request)
        dic = {}
        dic['username'] = request.session.get(utils.SESSION_USER, "")
        dic['auth_log'] = log_authority(request.session.get(utils.SESSION_USER, ""))
        dic['auth_new_data'] = new_data_authority(request.session.get(utils.SESSION_USER, ""))
        dic['auth_origin_data'] = origin_data_authority(request.session.get(utils.SESSION_USER, ""))
        dic = utils.update_nav_style(dic, request.session.get(utils.SESSION_DB, ""))

        return HttpResponse(json.dumps(dic), content_type='application/json')


def clearSession(request):
    '''
    手动输入分词后清除filename session
    :param request:
    :return:
    '''
    if utils.SESSION_FILE in request.session.keys():
        del request.session[utils.SESSION_FILE]
    return HttpResponse("", content_type='text')


def remove_special_words(request):
    '''
    去掉输入文本的特殊字符

    :param request:
    :return: new input
    '''
    if request.method == "POST":
        msg = request.POST.get("msg", "").replace(",", u"，").replace(".", u"。")  # 避免逗号当做数组的分隔符
        msg_list = utils.remove_special_word(msg)
        # msg_list = []
        # for m in msg.split(u"，"):
        #     msg_list.append(utils.remove_special_word(m)[:30]) #每条诊断最多30个字
        return HttpResponse(msg_list, content_type='text')


def all_files(request):
    return render_to_response("all_files.html", "")


def datafile(request):
    if not utils.check_user_session(request):
        return HttpResponseRedirect("/login/")
    return render_to_response("datafile.html", "")


def upload_file(request):
    '''
    上传文件，分词标注

    :param request:
    :return:
    '''
    if request.method == "POST":  # 请求方法为POST时，进行处理
        myFile = request.FILES.get("myfile", None)  # 获取上传的文件，如果没有文件，则默认为None
        upload_filename = utils.random_string() + "." + myFile.name.split(".")[-1]
        if not myFile:
            return "请上传文件!"
        ext = upload_filename.split(".")[-1]

        utils.write_to_file(myFile, os.path.join(utils.DIR_UPLOADS, upload_filename), ext)

        if ext == "txt" or ext == "csv":
            total = len(open(os.path.join(utils.DIR_UPLOADS, upload_filename)).readlines())
        elif ext == "xls" or ext == "xlsx":
            total = 0
            wb = xlrd.open_workbook(os.path.join(utils.DIR_UPLOADS, upload_filename))
            for k in range(len(wb.sheets())):
                ws = wb.sheet_by_index(k)
                total += ws.nrows

        request.session[utils.SESSION_FILE] = upload_filename

        date = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        # 将文件信息插入数据库
        file_dict = {dbinfo.FILE_FILE: myFile.name, dbinfo.FILE_CODE: upload_filename, dbinfo.FILE_TOTAL: total,
                     dbinfo.FILE_DATE: date, dbinfo.FILE_CHECKED: 0}
        utils.get_database(request.session.get(utils.SESSION_DB, "")).insert_file(file_dict)

        # 上传文件信息写入log
        utils.logger_file_info(request.session.get(utils.SESSION_USER, ""), "上传分词标注文件",
                               request.session.get(utils.SESSION_DB, ""), myFile.name)

        request.session[utils.SESSION_ORIGIN_FILE] = myFile.name

        return HttpResponse("")


def update_category(request):
    utils.update_db(request)

    dic = utils.update_nav_style({}, requests.session.get(utils.SESSION_DB, ""))
    dic["username"] = request.session.get(utils.SESSION_USER, "")

    return HttpResponse(json.dumps(dic), content_type='application/json')


def help(request):
    return render_to_response("help.html", "")

##########
# def test(request):
#     return render_to_response("1.html", "")

# def test_ajax(request):
#
#     '''
#     :param request:
#     :return:
#     '''
#     try:
#         term = request.POST.get("term","")
#
#         dic = {u"部位": 0, u"中心词": 0, u"病因": 0, u"病理": 0, u"特征词": 0, u"连接词": 0, u"判断词": 0, u"其他": 0,u"未知":0}
#         similarity={}
#         weight = 2
#         i=0
#         for m in bcjl_model.most_similar([str(term)]):
#             weight -= 0.2
#             try:
#                 a = utils.get_database("zhenduan").get_suggest_from_seg(m[0])[0]
#                 dic[a["sug"]] += m[1] + weight
#                 similarity[str(i)] = [m[0],a["sug"],round(m[1],4)]
#                 i+=1
#             except:
#                 # dic[u"未知"]+= m[1] + weight
#                 similarity[str(i)] = [m[0], u"未知", round(m[1], 4)]
#                 i+=1
#
#         sug = sorted(dic.items(), key=lambda x: x[1], reverse=True)[0]
#     except Exception,e:
#         exc_type, exc_obj, exc_tb = sys.exc_info()
#         f = open("test_error.txt","aw")
#         f.write(e.message)
#         f.write(str(exc_tb.tb_lineno))
#
#     # sum = 0
#     # for k, v in dic.iteritems():
#     #     sum += v
#     # rate = dic[sug[0]] / sum * 100
#
#     # similarity=bcjl_model.most_similar([str(term)])
#
#     '''
#     测试
#     肝功能损害，心肌梗塞，子宫
#     '''
#
#     return HttpResponse(json.dumps({"res":sug,"predict":similarity}), content_type='application/json')

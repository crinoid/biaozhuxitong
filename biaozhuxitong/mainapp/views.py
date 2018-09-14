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
        # db = request.POST.get("db", "")
        # if db:
        #     request.session[utils.SESSION_DB] = db
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

        # destination = open(os.path.join("uploads/", upload_filename), 'wb+')  # 打开特定的文件进行二进制的写操作
        # for chunk in myFile.chunks():  # 分块写入文件
        #     if ext == "txt" or ext == "csv":  # 只有文本文档涉及编码
        #         chunk = utils.convert_unicode(chunk)
        #     destination.write(chunk)
        # destination.close()

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

        request.session[utils.SESSION_ORIGIN_FILE] = myFile.name

        return HttpResponse("")


def update_category(request):
    utils.update_db(request)

    dic = utils.update_nav_style({}, requests.session.get(utils.SESSION_DB, ""))
    dic["username"] = request.session.get(utils.SESSION_USER, "")

    return HttpResponse(json.dumps(dic), content_type='application/json')

def help(request):
    return render_to_response("help.html", "")


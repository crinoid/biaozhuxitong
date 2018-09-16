# coding=utf8
from django.shortcuts import render, render_to_response
from django.http import HttpResponse

from utils import utils


import json

def log_management(request):
    return render_to_response("log_management.html")


def get_log_info(request):
    '''
    获得所有日志数据
    :param request:
    :return:
    '''
    if request.method == "POST":
        utils.update_db(request)
        log_dic = {}
        log_dic["denglu"] = get_login_loginfo()
        log_dic["shuju"] = get_data_loginfo()
        log_dic["biaozhu"] = get_sug_loginfo()
        log_dic["wenjian"] = get_files_loginfo()
        # log_dic["error"] = get_error_loginfo()

        config = json.load(open("config.json"))
        log_dic["page_count"] = config['basic']['ITEM_PER_PAGE_LOG']

        return HttpResponse(json.dumps(log_dic), content_type='application/json')


def get_login_loginfo():
    '''
    获得登录日志数据
    :return:
    '''
    login_dic = {}
    i = 0
    lines = open(utils.FILE_LOGIN_LOG).readlines()
    lines.reverse()
    for line in lines:
        items = line.strip()[1:-1].split("- ")
        dic = {}
        dic["username"] = items[-1].split(" ")[1]
        dic["date"] = items[0]
        login_dic[i] = dic
        i += 1

    return login_dic

def get_data_loginfo():
    '''
    获得数据操作日志数据
    :return:
    '''
    sug_dic = {}
    i = 0
    lines = open(utils.FILE_SUGGEST_LOG).readlines()
    lines.reverse()
    for line in lines:
        if "-" in line:
            items = line.strip()[1:-1].split("- ")
            dic = {}
            dic["date"] = items[0]
            dic["username"] = items[3].split(" ")[1]
            dic["source"] = items[4]
            dic["terms"] = items[5]
            dic["operation"] = items[6]
            dic["data"] = items[7]
            sug_dic[i] = dic
            i += 1

    return sug_dic

def get_sug_loginfo():
    '''
    获得编辑标注日志数据
    :return:
    '''
    sug_dic = {}
    i = 0
    lines = open(utils.FILE_CATEGORY_LOG).readlines()
    lines.reverse()
    for line in lines:
        if "-" in line:
            items = line.strip()[1:-1].split("- ")
            dic = {}
            dic["date"] = items[0]
            dic["username"] = items[3].split(" ")[1]
            dic["operation"] = items[4]
            dic["terms"] = items[5]
            dic["data"] = items[6]
            sug_dic[i] = dic
            i += 1

    return sug_dic

def get_files_loginfo():
    '''
    获得文件上传/删除数据
    :return:
    '''
    files_dic = {}
    i = 0
    lines = open(utils.FILE_FILES_LOG).readlines()
    lines.reverse()
    for line in lines:
        if "-" in line:
            items = line.strip()[1:-1].split("- ")
            dic = {}
            dic["date"] = items[0]
            dic["username"] = items[4]
            dic["type"] = items[5]
            dic["terms"] = items[6]
            dic["filename"] = items[7]
            files_dic[i] = dic
            i += 1

    return files_dic


def get_error_loginfo():
    '''
    获得错误日志数据
    :return:
    '''
    error_dic = {}
    i = 0
    lines = open(utils.FILE_ERROR_LOG).readlines()
    lines.reverse()
    for line in lines:
        if "-" in line:
            items = line.strip()[1:-1].split("- ")
            dic = {}
            dic["date"] = items[0]
            dic["username"] = items[3]
            dic["type"] = items[4]
            dic["desc"] = items[5]
            error_dic[i] = dic
            i += 1

    return error_dic


def log_info(logger, username, type, dbname, add, data):
    '''
    写入日志
    :param logger:
    :param username: session.get.username
    :param type: 手动/从文件
    :param dbname: utils.get_database(request.session.get("dbname", "")
    :param add: 添加分词/添加标注等信息
    :param new_seg: 新的分词/标注 A/B/C A||category1
    :return:
    '''
    dbname1 = "疾病诊断" if dbname == "zhenduan" else "手术操作"
    logger.info("用户 " + username + " - " + type + " - " + dbname1 + " - " + add + " - " + data)

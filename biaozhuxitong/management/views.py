# coding=utf8
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect

from users.views import log_authority, new_data_authority, origin_data_authority
from utils import utils, dbinfo

from fuzzywuzzy import fuzz

import json
import os
import commands
import requests
import logging


def get_files(request):
    '''
    获得所有上传文件
    :param request:
    :return:
    '''
    if request.method == "POST":
        utils.update_db(request)

        files = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_files()
        dic = get_file(files)

        return HttpResponse(json.dumps(dic), content_type='application/json')


def get_file(files):
    '''
    获得所有上传文件
    :param files:
    :return:
    '''
    dic = {}

    files_dic = {}
    i = 0
    for f in files:
        tmp = {}
        for k, v in f.iteritems():
            if k == u'_id':
                continue  # id的格式不能解析成json,也不需要id
            else:
                tmp[k] = v
        files_dic[i] = tmp
        i += 1
    dic["files"] = files_dic
    return dic


def select_file(request):
    '''
    上传文件-选择文件
    :param request:
    :return:
    '''
    if request.method == "POST":
        upload_filename = request.POST.get("file", "")
        # 随机码文件名
        request.session[utils.SESSION_FILE] = upload_filename
        cur_file = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_file_by_filecode(upload_filename)
        # 原始文件名
        origin_file = ""
        for c in cur_file:
            origin_file = c["file"]
        request.session[utils.SESSION_ORIGIN_FILE] = origin_file

        request.session["segfile"] = 1

        return HttpResponse("", content_type='text')


def search_item(request):
    '''
    分词标注搜索
    :param request:
    :return: 模糊匹配的结果
    '''
    if request.method == "POST":
        result = {}
        search = request.POST.get("msg", "")
        type = request.POST.get("type", "")  # 搜索范围，即标注

        all_data = request.session.get(utils.SESSION_ALLDATA, "")
        if type != u"所有":
            all_data = get_segs_by_sug(all_data, type)
        i = 0
        for data in sorted(all_data, key=lambda x: len(x)):
            # search:一个字一个字符,data:一个unicode汉字3个字符?==>转换成str
            # DICT_DATA是排好序的?,result不用排序,自动由短到长
            if fuzz.partial_ratio(search, data) == 100 and (len(str(search)) <= len(str(data))):
                result[i] = data
                i += 1

        return HttpResponse(json.dumps(result), content_type='application/json')


def get_segs_by_sug(data, target_sug):
    flag = False
    dic = {}
    for seg, sug in data.iteritems():
        if sug == target_sug:
            # flag = True
            dic[seg] = sug
            # if flag and sug != target_sug:
            #     return dic
    return dic


def build_sug_dict(data):
    '''
    将data["items"]转成seg:sug的形式,赋值给ALL_DATA--session["all_data"]
    :param data:
    :return: key:seg,value:sug
    '''
    dic = {}
    for k, v in data.iteritems():
        dic[v["seg"]] = v["sug"]
    return dic


def delete_file(request):
    '''
    删除上传的文件
    :param request:
    :return:
    '''
    if request.method == "POST":
        filename = request.POST.get("file", "")
        utils.get_database(request.session.get(utils.SESSION_DB, "")).delete_file(filename)
        if os.path.exists(os.path.join(utils.DIR_UPLOADS, filename)):
            os.remove(os.path.join(utils.DIR_UPLOADS, filename))

        files = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_files()
        dic = get_file(files)
        return HttpResponse(json.dumps(dic), content_type='application/json')


'''
datafile
'''

def refresh_datafile_sug(data, db):
    '''
    获得新增的标注数据，id除外
    :param d: 返回数据，字典
    :param db: 数据库表名
    :return:
    '''
    sugs = utils.get_database(db).get_new_suggests()
    sug_dic = {}
    i = 0
    for f in sugs:
        tmp = {}
        for k, v in f.iteritems():
            if k == u'_id':
                continue  # id的格式不能解析成json
            else:
                tmp[k] = v
            i += 1
        sug_dic[i] = tmp

    data["sugs"] = sug_dic
    return data


def get_data(request):
    '''
    获得新增的标注数据
    :param request:
    :return:
    '''
    if request.method == "POST":
        utils.update_db(request)
        d = {}
        d = refresh_datafile_sug(d, request.session.get(utils.SESSION_DB, ""))

        return HttpResponse(json.dumps(d), content_type='application/json')


def update_segs_sugs(request):
    '''
    修改原始数据
    :param request: source:origin/new
                    msgs:dict,[seg:sug]
    :return:
    '''
    if request.method == "POST":
        msgs = eval(request.POST.get("msg", ""))  # {"高血压":"中心词"}

        utils.get_database(request.session.get(utils.SESSION_DB, "")).update_single_sug_category(msgs)

        requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")), data=request.session.get(utils.SESSION_DB, ""), headers=utils.headers)
        requests.post(utils.update_seg_url(request.session.get(utils.SESSION_DB, "")), data="", headers=utils.headers)

        data = init_origin_data({}, request.session.get(utils.SESSION_DB, ""))

        # logger = logging.getLogger(utils.SEGMENT_LOG)
        # for seg, items in items_update.iteritems():
        #     if items[0] == "":
        #         action = "添加"
        #         out = seg + ":" + items[1]
        #     elif items[1] == "":
        #         action == "删除"
        #         out = seg + ":" + items[0]
        #     else:
        #         action == "修改"
        #         out = seg + ":" + items[0] + "=>" + seg + ":" + items[1]
        #     logger.info("用户 " + request.session.get("username", "") + " - " + "原始文本" + " - " + action + " - " + out)

        # update_dict_data(msgs)

        return HttpResponse(json.dumps(data), content_type='application/json')


def delete_segs_sugs(request):
    '''
    新增数据的删除
    :param request: msg:{sug:"多根-其他,双坐骨-部位,..."} {0:{seg:,sug:},1:{seg:,sug:}}
    :return:
    '''
    if request.method == "POST":
        msgs = eval(request.POST.get("msg", ""))
        dic = {}
        if "sug" in msgs.keys():
            sugs = msgs["sug"]
            for s in sugs.split(","):
                if s:
                    idx = s.rfind("-")  # 最后一个"-"是分隔分词与标注，分词有可能带有"-"
                    dic['seg'], dic['sug'] = s[:idx], s[idx + 1:len(s)]

                    utils.get_database(request.session.get(utils.SESSION_DB, "")).delete_suggests(dic)
        else:
            for k, v in msgs.iteritems():
                utils.get_database(request.session.get(utils.SESSION_DB, "")).delete_suggests(v)

        data = init_origin_data({}, request.session.get(utils.SESSION_DB, ""))
        data = refresh_datafile_sug(data, request.session.get(utils.SESSION_DB, ""))
        # 这里按sug排序
        request.session[utils.SESSION_ALLDATA] = build_sug_dict(data["items"])

        # 更新服务

        if request.session.get(utils.SESSION_DB, "") == "zhenduan":
            url = utils.seg_service_url_zd
        elif request.session.get(utils.SESSION_DB, "") == "shoushu":
            url = utils.seg_service_url_ss

        requests.post(url, data=request.session.get(utils.SESSION_DB, ""), headers=utils.headers)

        if request.session.get(utils.SESSION_DB, "") == "zhenduan":
            url = utils.sug_service_url_zd
        elif request.session.get(utils.SESSION_DB, "") == "shoushu":
            url = utils.sug_service_url_ss

        requests.post(url, data=request.session.get(utils.SESSION_DB, ""), headers=utils.headers)

        return HttpResponse(json.dumps(data), content_type='application/json')


# def delete_segs(request):
#     if request.method == "POST":
#         # 删除所选分词
#         segs = request.POST.get("msg", "")
#         delete_selected_segs(segs)
#
#         d = refresh_datafile_seg({})
#
#         return HttpResponse(json.dumps(d), content_type='application/json')


# def delete_selected_segs(segs, db):  # segs:array
#     utils.get_database(db).delete_segments(segs)
#     requests.post(utils.update_seg_url, data=json.dumps({"data": utils.get_database(db).get_segments()}),
#                   headers=utils.headers)


def delete_sugs(request):
    if request.method == "POST":
        sugs = request.POST.get("msg", "")
        delete_selected_sugs(sugs)

        d = refresh_datafile_sug({})

        return HttpResponse(json.dumps(d), content_type='application/json')


def delete_selected_sugs(sugs, db):
    '''
    数据库删除分词标注，更新服务数据
    :param sugs:
    :param db: 术语集名称
    :return:
    '''
    utils.get_database(db).delete_suggests(sugs)
    requests.post(utils.update_sug_url(db), data=db, headers=utils.headers)


def add_segs_sugs(request):
    '''
    从新增数据添加分词标注
    :param request: msgs:sug:"人工-中心词,髋关节-部位"
    :return:
    '''
    if request.method == "POST":
        data = eval(request.POST.get("msg", ""))

        add_sugs(data["sug"], request.session.get(utils.SESSION_DB, ""))
        add_segs(request.session.get(utils.SESSION_DB, ""))

        d = refresh_datafile_sug({}, request.session.get(utils.SESSION_DB, ""))

        return HttpResponse(json.dumps(d), content_type='application/json')


# 添加分词,修改state=已存
def add_segs(db):
    '''
    更新分词服务
    :param db:
    :return:
    '''
    if db == "zhenduan":
        url = utils.seg_service_url_zd
    elif db == "shoushu":
        url = utils.seg_service_url_ss
    requests.post(url, data=db, headers=utils.headers)

    return HttpResponse("", content_type='application/text')


def add_sugs(sugs, db):
    '''
    更新标注数据库，state=已存，更新标注服务
    :param sugs:
    :param db:
    :return:
    '''
    utils.get_database(db).update_sug_state(sugs)
    if db == "zhenduan":
        url = utils.sug_service_url_zd
    elif db == "shoushu":
        url = utils.sug_service_url_ss
    requests.post(url, data=db, headers=utils.headers)

    return HttpResponse("", content_type='application/text')


# def download_seg(request):
#     if request.method == "POST":
#         segs = utils.get_database(request.session.get("dbname", "")).get_new_segments()
#         data = ""
#         for f in segs:
#             s = f['seg'] + "\n"
#             data += s
#
#         return HttpResponse(data, content_type='text')


def download_sug(request):
    if request.method == "POST":
        segs = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_new_suggests()
        data = ""
        for f in segs:
            s = f["seg"] + "-" + f["sug"]
            data += s + "\n"

        return HttpResponse(data, content_type='text')


'''
查看原始数据
'''


def origin_data(request):
    # if not utils.check_user_session(request):
    #     return HttpResponseRedirect("/login/")
    # if origin_data_authority(request.session["username"]) == '0':
    #     return HttpResponseRedirect("/")

    return render_to_response("origin_data.html")


def init_origin_data(data, db):
    '''
    获得所有数据（分词-标注）
    :param data:返回数据
    :param db: 当前的术语集（数据库）
    :return: items:所有数据，sugs：所有标注
    '''
    data["items"] = {}
    i = 0

    all_sugs = utils.get_database(db).get_suggests()
    segs_with_sugs = set()

    for line in all_sugs:
        tmp = line
        del tmp[u"_id"]
        # tmp["seg"] = line["seg"]
        # tmp["sug"] = line["sug"]
        # tmp["sug_source"] = line["sug_source"]
        segs_with_sugs.add(tmp["seg"])

        data["items"][i] = tmp
        i += 1

    data["all_sug"] = utils.get_suggestions(db)

    return data


def get_origin_data(request):
    '''
    获得所有数据库中已存的数据
    :param request:
    :return:
    '''
    if request.method == "POST":
        utils.update_db(request)
        data = init_origin_data({}, request.session.get(utils.SESSION_DB, ""))
        # 这里按sug排序
        request.session[utils.SESSION_ALLDATA] = build_sug_dict(data["items"])

        return HttpResponse(json.dumps(data), content_type='application/json')


def file_check(filename):
    '''
    上传标注文件,检查每行是否按\t分成两项
    :param filename:
    :return:
    '''
    for line in open(filename):
        if len(line.split("\t") != 2):
            return HttpResponse("0", content_type="application/text")
    return HttpResponse("1", content_type="application/text")


def upload_data_file(request):
    '''
    上传分词/标注数据,txt/csv格式
    分词-标注数据库已有，跳过
    分词-标注数据库没有，写入
    分词-标注和数据库的不一样，提示是否覆盖
    错误数据（格式不对，标注类型不对），不能写入
    :param request:
    :return:
    '''
    # if not utils.check_user_session(request):
    #     return HttpResponseRedirect("/login/")

    upload_filename = request.FILES.get("myfile", None)
    name = upload_filename.name
    ext = name.split(".")[-1]
    utils.write_to_file(upload_filename, "tmp.csv", ext)

    all_categories = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_categories()

    error_data, error_type, duplicate_data = [], [], {}
    i = 0
    # 上传标注
    for line in open("tmp.csv").readlines():
        line = line.strip()
        if len(line) > 1:
            if len(line.split("\t")) != 2:
                error_data.append(line)  # 数据格式错误
            else:
                seg, sug = line.split("\t")
                if sug in all_categories:  # 添加的标注需属于已有标注
                    res = utils.get_database(request.session.get(utils.SESSION_DB, "")).insert_suggests(
                        {dbinfo.SUG_SEG: seg, dbinfo.SUG_SUG: sug, dbinfo.SEG_SOURCE: "", dbinfo.SUG_SOURCE: "",
                         dbinfo.SUG_STATE: "已存", dbinfo.SUG_COUNT: 1})
                    if res:
                        duplicate_data[res['seg']] = [res['sug'], sug]  # 添加的标注需属于已有标注
                    i += 1
                else:
                    error_type.append(line)  # 标注类型不存在
        else:
            error_data.append(line)

    requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")), data=request.session.get(utils.SESSION_DB, ""), headers=utils.headers)

    data = {'error': error_data, 'type': error_type, 'duplicate': duplicate_data}

    # 更新数据
    data = init_origin_data(data, request.session.get(utils.SESSION_DB, ""))
    # 这里按sug排序
    request.session[utils.SESSION_ALLDATA] = build_sug_dict(data["items"])

    return HttpResponse(json.dumps(data), content_type='application/json')


def update_duplicate_data(request):
    '''
    上传分词标注数据时，对于已有分词，覆盖标注
    :param request: msg: [["植入"，"术式"],["盆腔","部位"]]
    :return:
    '''
    if request.method == "POST":
        seglist = eval(request.POST.get("msg", ""))
        for item in seglist:
            seg, sug = item[0], item[1]
            utils.get_database(request.session.get(utils.SESSION_DB, "")).insert_suggests(
                {dbinfo.SUG_SEG: seg, dbinfo.SUG_SUG: sug, dbinfo.SEG_SOURCE: "", dbinfo.SUG_SOURCE: "",
                 dbinfo.SUG_STATE: "已存", dbinfo.SUG_COUNT: 1}, cover=True)
    return HttpResponse("", content_type='application/text')  # 新的数据(tmp)写入原始文档(target),并重新排序


# def rewrite_file(target_file, tmp_file, is_modify=False):
#     '''
#
#     :param target_file:
#     :param tmp_file:
#     :param is_modify:
#     :return:
#     '''
#     f_target = open(target_file, "aw")
#     for line in open(tmp_file).readlines():
#         line = line.strip()
#         if is_modify:  # 从标注中提取分词
#             line = modify_line(line)
#         f_target.write(line + "\n")
#     f_target.close()
#
#     commands.getstatusoutput("cat " + target_file + " | sort | uniq > o1.csv")
#     commands.getstatusoutput("mv o1.csv " + target_file)


# def modify_line(line):
#     return line.split("\t")[0]


'''
日志添加,查看

'''


def log_management(request):
    # if not utils.check_user_session(request):
    #     return HttpResponseRedirect("/login/")
    # if log_authority(request.session["username"]) == '0':
    #     return HttpResponseRedirect("/")
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
        log_dic["login"] = get_login_loginfo()
        log_dic["seg"] = get_seg_loginfo()
        log_dic["sug"] = get_sug_loginfo()
        log_dic["error"] = get_error_loginfo()

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


def get_seg_loginfo():
    '''
    获得分词日志数据
    :return:
    '''
    seg_dic = {}
    i = 0
    lines = open(utils.FILE_SEGMENT_LOG).readlines()
    lines.reverse()
    for line in lines:
        # 去掉回车和两头的引号
        items = line.strip()[1:-1].split("- ")
        if len(items) == 8:
            dic = {}
            dic["date"] = items[0]
            dic["username"] = items[3].split(" ")[1]
            dic["source"] = items[4]
            dic["terms"] = items[5]
            dic["operation"] = items[6]
            dic["item"] = items[7]
            dic["diagnose"] = dic["item"].replace("/", "")
            seg_dic[i] = dic
            i += 1

    return seg_dic


def get_sug_loginfo():
    '''
    获得标注日志数据
    :return:
    '''
    sug_dic = {}
    i = 0
    lines = open(utils.FILE_SUGGEST_LOG).readlines()
    lines.reverse()
    for line in lines:
        if "-" in line:
            items = line.strip()[1:-1].split("- ")
            if len(items) == 9:
                dic = {}
                dic["date"] = items[0]
                dic["username"] = items[3].split(" ")[1]
                dic["source"] = items[4]
                dic["terms"] = items[5]
                dic["operation"] = items[6]
                dic["diagnose"] = items[7]
                dic["item"] = items[8]
                sug_dic[i] = dic
                i += 1

    return sug_dic


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

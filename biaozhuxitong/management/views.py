# coding=utf8
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect

from utils import utils, dbinfo

from fuzzywuzzy import fuzz

import json
import os
import requests
import logging
import sys


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

        config = json.load(open("config.json"))
        dic["page_count"] = config['basic']['ITEM_PER_PAGE_FILE']

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
    dic = {}
    for seg, sug in data.iteritems():
        if sug == target_sug:
            dic[seg] = sug
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
    删除上传的文件(分词标注)
    :param request:
    :return:
    '''
    if request.method == "POST":
        filename = request.POST.get("file", "")

        cur_file = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_file_by_filecode(filename)
        # 原始文件名
        origin_file = ""
        for c in cur_file:
            origin_file = c["file"]
        utils.logger_file_info(request.session.get(utils.SESSION_USER, ""), "删除分词标注文件",
                               request.session.get(utils.SESSION_DB, ""), origin_file)

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
        logger = logging.getLogger(utils.SUGGEST_LOG)
        for seg, sug in msgs.iteritems():
            old_sug = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_suggest_from_seg(seg)[0]["sug"]

            utils.log_data_info(logger, request.session.get(utils.SESSION_USER, ""), "手动",
                                request.session.get(utils.SESSION_DB, ""), "更新原始数据",
                                seg + ":" + old_sug + "=>" + seg + ":" + sug)

        # 先获得更新的词原先的标注，用于写入日志，再更新数据库
        utils.get_database(request.session.get(utils.SESSION_DB, "")).update_single_sug_category(msgs)

        requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")),
                      data="", headers=utils.headers)
        requests.post(utils.update_seg_url(request.session.get(utils.SESSION_DB, "")), data="", headers=utils.headers)

        data = init_origin_data({}, request.session.get(utils.SESSION_DB, ""))

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
        # 删除新增数据
        if "sug" in msgs.keys():
            sugs = msgs["sug"]
            for s in sugs.split(","):
                if s:
                    idx = s.rfind("-")  # 最后一个"-"是分隔分词与标注，分词有可能带有"-"
                    dic['seg'], dic['sug'] = s[:idx], s[idx + 1:len(s)]

                    utils.get_database(request.session.get(utils.SESSION_DB, "")).delete_suggests(dic)

                    logger = logging.getLogger(utils.SUGGEST_LOG)
                    utils.log_data_info(logger, request.session.get(utils.SESSION_USER, ""), "手动",
                                        request.session.get(utils.SESSION_DB, ""), "删除新增数据",
                                        dic['seg'] + ":" + dic['sug'])
        # 删除原始数据
        else:
            for k, v in msgs.iteritems():
                utils.get_database(request.session.get(utils.SESSION_DB, "")).delete_suggests(v)

                logger = logging.getLogger(utils.SUGGEST_LOG)
                utils.log_data_info(logger, request.session.get(utils.SESSION_USER, ""), "手动",
                                    request.session.get(utils.SESSION_DB, ""), "删除原始数据", v["seg"] + ":" + v["sug"])

        data = init_origin_data({}, request.session.get(utils.SESSION_DB, ""))
        data = refresh_datafile_sug(data, request.session.get(utils.SESSION_DB, ""))
        # 这里按sug排序
        request.session[utils.SESSION_ALLDATA] = build_sug_dict(data["items"])

        # 更新服务
        requests.post(utils.update_seg_url(request.session.get(utils.SESSION_DB, "")), data="", headers=utils.headers)
        requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")),
                      data="", headers=utils.headers)

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
    :param request: msgs:{sug:"人工-中心词,髋关节-部位"}
    :return:
    '''
    if request.method == "POST":
        data = eval(request.POST.get("msg", ""))

        res = add_sugs(data["sug"], request.session.get(utils.SESSION_DB, ""))
        add_segs(request.session.get(utils.SESSION_DB, ""))

        logger = logging.getLogger(utils.SUGGEST_LOG)

        for sug, old_sug in res.iteritems():
            if old_sug == "":
                op = "确认标注"
            else:
                op = "更新标注"
                old_sug += "=>"
            utils.log_data_info(logger, request.session.get(utils.SESSION_USER, ""), "手动",
                                request.session.get(utils.SESSION_DB, ""), op,
                                old_sug + sug)

        d = refresh_datafile_sug({}, request.session.get(utils.SESSION_DB, ""))

        # 更新服务
        requests.post(utils.update_seg_url(request.session.get(utils.SESSION_DB, "")),
                      data="", headers=utils.headers)
        requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")),
                      data="", headers=utils.headers)

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
    :return:新增标注是否覆盖之前的标注，用于写日志
    '''
    res = utils.get_database(db).update_sug_state(sugs)
    if db == "zhenduan":
        url = utils.sug_service_url_zd
    elif db == "shoushu":
        url = utils.sug_service_url_ss
    requests.post(url, data=db, headers=utils.headers)

    return res


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

        config = json.load(open("config.json"))
        data["page_count"] = config['basic']['ITEM_PER_PAGE_ORIGIN_DATA']

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


def check_file(request):
    '''
    检查上传的数据是否符合规范
    :param request:
    :return:
    '''
    try:
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

                        res, old_sug = utils.get_database(request.session.get(utils.SESSION_DB, "")).is_sug_exist(seg,
                                                                                                                  sug)
                        if res:
                            duplicate_data[seg] = [sug, old_sug]  # 添加的标注需属于已有标注
                        i += 1
                    else:
                        error_type.append(line)  # 标注类型不存在
            else:
                error_data.append(line)

        data = {'error': error_data, 'types': error_type, 'duplicate': duplicate_data}
    except Exception, e:
        f = open("exp.txt", "w")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        output = ",".join([str(e), fname, str(exc_tb.tb_lineno)])
        f.write(output)

    return HttpResponse(json.dumps(data), content_type='application/json')


def upload_data_file(request):
    '''
    上传分词/标注数据,txt/csv格式
    分词-标注数据库已有，跳过
    分词-标注数据库没有，写入
    分词-标注和数据库的不一样，提示是否覆盖
    ？只有分词，没有标注：未知
    错误数据（格式不对，标注类型不对），不能写入
    :param request:
    :return:
    '''
    # 上传文件信息写入log
    # upload_filename = request.FILES.get("myfile", None)
    # name = upload_filename.name
    # utils.logger_file_info(request.session.get(utils.SESSION_USER, ""), "上传分词标注数据",
    #                        request.session.get(utils.SESSION_DB, ""), name)

    checked = request.POST.get("checked", "")  # 同一分词，不同标注，是否覆盖原始数据
    if checked == '0':
        checked = False
    else:
        checked = True

    all_categories = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_categories()

    i = 0
    # 上传标注
    for line in open("tmp.csv").readlines():
        line = line.strip()
        if len(line) > 1:
            if len(line.split("\t")) != 2:
                pass
            else:
                seg, sug = line.split("\t")
                if sug in all_categories:  # 添加的标注需属于已有标注
                    # 添加数据

                    utils.get_database(request.session.get(utils.SESSION_DB, "")).insert_suggests(
                        {dbinfo.SUG_SEG: seg, dbinfo.SUG_SUG: sug, dbinfo.SEG_SOURCE: "", dbinfo.SUG_SOURCE: "",
                         dbinfo.SUG_STATE: "已存", dbinfo.SUG_COUNT: 1}, cover=checked)

                    utils.log_sug_info(request.session.get(utils.SESSION_USER, ""), "从数据文件", request.session.get(
                        utils.SESSION_DB, ""), "添加标注", seg + ":" + sug)

                    i += 1

    requests.post(utils.update_seg_url(request.session.get(utils.SESSION_DB, "")),
                  data="", headers=utils.headers)
    requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")),
                  data="", headers=utils.headers)

    # 更新数据
    data = init_origin_data({}, request.session.get(utils.SESSION_DB, ""))
    # 这里按sug排序
    request.session[utils.SESSION_ALLDATA] = build_sug_dict(data["items"])

    return HttpResponse(json.dumps(data), content_type='application/json')


def update_duplicate_data(seg, sug, dbname):
    '''
    上传分词标注数据时，对于已有分词，覆盖标注
    :param request: msg: [["植入"，"术式"],["盆腔","部位"]]
    :return:
    '''
    utils.get_database(dbname).insert_suggests(
        {dbinfo.SUG_SEG: seg, dbinfo.SUG_SUG: sug, dbinfo.SEG_SOURCE: "", dbinfo.SUG_SOURCE: "",
         dbinfo.SUG_STATE: "已存", dbinfo.SUG_COUNT: 1}, cover=True)




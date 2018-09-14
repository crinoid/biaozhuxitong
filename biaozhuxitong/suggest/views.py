# coding=utf8
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect

from utils import utils
import xlrd, xlwt
import json
import os
import logging
import requests
import sys

from pyfasttext import FastText

error_logger = logging.getLogger('error')


def suggest(request):
    if not utils.check_user_session(request):
        return HttpResponseRedirect("/login/")
    # 进入标注界面,更新服务,按所选类型切换标注术语集
    requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")), data=request.session.get(utils.SESSION_DB, ""), headers=utils.headers)
    return render_to_response("suggest.html")


# 新增分词写入数据库
# def update_new_seg_data(data, dbname):
#     for value in data.split(";"):
#         for v in value[:-1].split(","):
#             origin_msg = utils.seperate_term(v, value[:-1].split(","))
#             # 只记录未出现过的词
#             utils.get_database(dbname).update_seg_source(v, origin_msg)


def send_suggest(request):
    '''
    进入标注界面，获得分词，调用标注服务
    :param request:
    :return:
    '''
    if request.method == "POST":
        try:
            utils.update_db(request)
            new_sugs = request.POST.get("new_segs", "")[:-1]  # 去掉末尾的;
            # update_new_seg_data(new_sugs, request.session.get(utils.SESSION_DB, ""))

            logger = logging.getLogger(utils.FILE_SEGMENT_LOG)

            filename = request.session.get(utils.SESSION_FILE, "")

            info = dict()

            # 手动输入
            if filename == "":
                # 诊断的分词对应标注和来源
                info['sug'], info['source'] = get_sug_from_disk(logger, new_sugs,
                                                                 request.session.get(utils.SESSION_USER, ""),
                                                                 request.session.get(utils.SESSION_DB, ""))
            # 从文件读取
            else:
                edit_index = request.POST.get("edit_index", "")  # 已编辑的index
                # seg_index_list = edit_index.split(",")[:-1]  # 保存过的诊断index,从0开始

                # edit_count = get_sug_from_file(filename, seg_index_list)  # 返回编辑的分词个数
                edit_count = 0

                utils.get_database(request.session.get(utils.SESSION_DB, "")).update_file_checked_seg(filename,
                                                                                                      edit_count)
                # 诊断的分词对应标注
                info['sug'], info['source'] = sort_sugs_by_category(
                    "从文件 " + request.session.get(utils.SESSION_ORIGIN_FILE, ""),
                    new_sugs, logger,
                    request.session.get(utils.SESSION_USER, ""),
                    request.session.get(utils.SESSION_DB, ""))

            # 所有的标注对应颜色
            info['all'] = {}
            all_sugs = utils.get_suggests_dic(request.session.get(utils.SESSION_DB, ""))
            for k, v in all_sugs.iteritems():
                info['all'][k] = v

        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            output = ",".join([str(e), fname, str(exc_tb.tb_lineno)])
            error_logger.info(request.session.get(utils.SESSION_DB, "") + " - 标注服务错误 - " + output)

        return HttpResponse(json.dumps(info), content_type='application/json')


def get_sug_from_disk(logger, new_sugs, username, dbname):
    '''
    手动输入分词，获得标注
    :param logger:
    :param new_sugs:一组分词[高血压，2级; 糖尿病]
    :param username:
    :param dbname:
    :return:
    '''

    num = 1
    info_sug,res_source = [],[]
    new_sugs=new_sugs.split(";")
    for origin_cut in new_sugs:
        # 插入日志
        log_info(logger, username, "手动", dbname, "添加分词", origin_cut[:-1].replace(",", "/"))

        sug_dic = {num: "/".join(origin_cut[:-1].split(","))}
        num += 1

        sug_list = call_sug_api(json.dumps(sug_dic),dbname)

        terms = {}
        # info_sug = []
        # for msg in new_sugs:
        #     sug_list=sugs_list[msg].iteritems()
        for msg, sug_list1 in sug_list.iteritems():
            for k, sugs in sug_list1.iteritems():  # sug1["高血压","中心词"]
                tmp = []
                for sug1 in sugs:
                    if sug1[1] == "":
                        # sug1[1]=utils.auto_match(sug1[0],dbname)
                        sug1[1] = u"未知"
                    tmp.append([sug1[0], sug1[1]])
                    terms[sug1[0]] = sug1[1]
                if tmp:
                    info_sug.append(tmp)
        res_source.append(utils.get_database(dbname).get_sug_source([terms], utils.MAX_TERMS))
    return info_sug,res_source


def get_sug_from_file(filename, seg_index_list):
    '''
    上传文件，获得标注
    :param filename:
    :param seg_index_list:
    :return:
    '''
    filepath = utils.DIR_UPLOADS + filename

    edit_count = 0

    ext = filename.split(".")[1]
    if ext == "csv" or ext == "txt":
        f = open(filepath)
        lines = f.readlines()
        new_file = open("uploads/tmp." + ext, "w")
        for i in range(len(lines)):
            lines[i] = lines[i].strip()
            new_line = lines[i]
            if str(i) in seg_index_list:
                # 做保存的诊断,在后面加上一列,值=1
                if "\t" not in lines[i]:
                    new_line = lines[i] + "\t" + "1"
            if "\t" in new_line:
                edit_count += 1
            new_file.write(new_line + "\n")

        f.close()
        os.rename("uploads/tmp." + ext, filepath)

    elif ext == "xls" or ext == "xlsx":
        wb = xlrd.open_workbook(os.path.join(utils.DIR_UPLOADS, filename))
        new_file = xlwt.Workbook(encoding='utf8')
        i = 0  # 总共的index
        for k in range(len(wb.sheets())):
            ws = wb.sheet_by_index(k)
            ws_new = new_file.add_sheet("sheet" + str(k))
            for j in range(ws.nrows):
                line = ws.cell(j, 0).value.strip()
                # 添加原文件的诊断
                ws_new.write(j, 0, line)
                # 原始文件第2列有值,或者当前诊断新保存过,第2列为1
                item = ws.row_values(j)
                if len(item) > 1 or str(i) in seg_index_list:
                    ws_new.write(j, 1, 1)
                    edit_count += 1
                i += 1
        new_file.save("uploads/tmp.xls")

    return edit_count


def sort_sugs_by_category(origin_file, new_cuts, logger, username, dbname):
    '''
    从文件读取，将标注按标注类型排序，带有"未知"和"其他"的优先
    :param origin_file:
    :param new_cuts:
    :param logger:
    :param username:
    :param dbname:
    :return:
    '''
    unknown, others, rest = [], [], []
    unknown_source, others_source, rest_source = [], [], []

    num = 1

    new_cuts=new_cuts.split(";")
    for origin_cut in new_cuts:
        log_info(logger, username, origin_file, dbname, "添加分词", origin_cut[:-1].replace(",", "/"))

        sug_dic = {num: "/".join(origin_cut[:-1].split(","))}
        num += 1

        sug_list = call_sug_api(json.dumps(sug_dic),dbname)

        # for msg in new_cuts:
        #     sug_list1=sug_list[msg]
        # for msg, sug_list1 in sug_list.iteritems():  # suglist:一句话
        sug_list1 = sug_list["sug"]
        is_unknown, is_others = False, False
        tmp = []
        terms = {}  # 当前文本的分词:标注
        for k, sugs in sug_list1.iteritems():  # sug1["高血压","中心词"]
            for sug1 in sugs:
                if sug1[1] == "":
                    sug1[1] = u"未知"
                    is_unknown = True
                elif sug1[1] == u"其他" or sug1[1] == '其他':
                    is_others = True
                tmp.append([sug1[0], sug1[1]])
                terms[sug1[0]] = sug1[1]

        if is_unknown:
            unknown.append(tmp)
            unknown_source.append(terms)
        elif is_others:
            others.append(tmp)
            others_source.append(terms)
        else:
            rest.append(tmp)
            rest_source.append(terms)

    unknown.extend(others)
    unknown.extend(rest)

    unknown_source.extend(others_source)
    unknown_source.extend(rest_source)

    #unknown_source:list[{'高血压':中心词，'2型':分型}，{'糖尿病'：}] type:str
    source = utils.get_database(dbname).get_sug_source(unknown_source, utils.MAX_TERMS)
    return unknown, [source]


def call_sug_api(data,dbname):
    # 调用标注服务
    if dbname == "zhenduan":
        url = utils.sug_service_url_zd
    if dbname == "shoushu":
        url = utils.sug_service_url_ss
    res = requests.post(url, data=data, headers=utils.headers).content.decode('utf8')
    return eval(res)


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
    logger.info("用户 " + username + " - " + type + " - " + dbname + "-" + add + "-" + data)


def update_suggests(request):
    '''
    在标注界面,切换术语集,更新标注和颜色
    :param request:
    :return:
    '''
    if request.method == "POST":
        # db = request.POST.get("db", "")
        # if db:
        #     request.session[utils.SESSION_DB] = db
        utils.update_db(request)
        dic = get_all_suggest_color({}, request.session.get(utils.SESSION_DB, ""))
        dic = utils.update_nav_style(dic, request.session.get(utils.SESSION_DB, ""))

        return HttpResponse(json.dumps(dic), content_type='application/json')


def update_sug_source(request):
    '''
    加载标注来源
    :param request:
    :return:
    '''
    if request.method == "POST":
        items = request.POST.get("msg", "")
        items = eval(items)

        terms = []
        for k in range(min(len(items), utils.SUGS_PER_PAGE)):
            tmp = []
            for s in items[str(k)]["sug"]:
                tmp.append(merge_segs(s))
            terms.append(tmp)

        res = get_sug_source(request.session.get(utils.SESSION_DB, ""), terms)

        return HttpResponse(json.dumps(res), content_type='application/json')


def get_sug_source(dbname, terms):
    '''
    每次分页，加载标注来源
    :param dbname: session中的数据库名称
    :param terms: 一组分词[[高血压,3级],[右眼,外伤]...]，length=每页分词个数
    :return:
    '''
    res = utils.get_database(dbname).get_sug_source(terms, utils.MAX_TERMS)
    return res


def merge_segs(segs):
    res = ""
    for seg in segs:
        res += seg
    return res


def get_all_suggest_color(dic, db):
    sugs = utils.get_suggests_dic(db)
    dic['all'] = {}
    for k, v in sugs.iteritems():
        dic['all'][k] = v

    return dic


# 这里前台做成window.location.href,问号传参数?
def save_suggest(request):
    """
    保存标注，写入数据库
    :param request:
    :return:
    """
    if request.method == "POST":

        # 将json传来的字符串转成字典
        utility = eval(request.POST.get("sugs", ""))  # 寻常型/天疱疮:{寻常型:分型,天疱疮:中心词}

        logger = logging.getLogger(utils.SUGGEST_LOG)

        method = "手动" if utils.SESSION_ORIGIN_FILE in request.session else "从文件 " + request.session.get(
            utils.SESSION_ORIGIN_FILE, "")

        i = 0
        # k:原文,v:分词+标注
        for k, v in utility.iteritems():
            msg = ""
            for seg, sug in v.iteritems():
                if not sug == utils.UNKNOWN:  # 未知不写入数据库
                    source = utils.seperate_term(seg, k.split("/"))
                    utils.get_database(request.session.get(utils.SESSION_DB, "")).update_sug_source(seg, sug, source)
                msg += seg + ":" + sug + " || "
            i += 1
            log_info(logger, request.session.get(utils.SESSION_USER, ""), method,
                     request.session.get(utils.SESSION_DB, ""), "添加标注", k + " - " + msg)

        return HttpResponse("", content_type="text")


def suggest_edit(request):
    return render_to_response("suggest_edit.html")


def get_all_suggests(request):
    '''
    所有标注传到标注编辑界面
    :param request:
    :return:
    '''
    # db = request.POST.get("db", "")
    # if db:
    #     request.session["dbname"] = db
    utils.update_db(request)

    sug_category = {}
    sug_category["category"] = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_categories()

    count = {}
    for s in sug_category["category"]:
        count[s] = 0

    sug_data = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_suggests()

    for line in sug_data:
        try:
            count[line["sug"]] += 1
        except Exception,e:
            print line["sug"]

    sug_category["counts"] = count
    # sug_category = utils.update_nav_style(sug_category, request.session.get("dbname", ""))

    return HttpResponse(json.dumps(sug_category), content_type='application/json')


def add_category(request):
    '''
    添加标注类型
    :param request:
    :return:
    '''
    if request.method == "POST":
        new_ctg = request.POST.get("newctg", "")
        utils.get_database(request.session.get(utils.SESSION_DB, "")).update_categories(new_ctg)

        sug_category = {}
        sug_category["category"] = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_categories()

        count = {}
        for s in sug_category["category"]:
            count[s] = 0

        sug_data = utils.get_database(request.session.get(utils.SESSION_DB, "")).get_suggests()

        for line in sug_data:
            count[line["sug"]] += 1

        sug_category["counts"] = count

        # 更新服务
        requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")), data=request.session.get(utils.SESSION_DB, ""), headers=utils.headers)

        return HttpResponse(json.dumps(sug_category), content_type='application/json')

# def get_url(dbname):
#     if dbname == "zhenduan":
#         url = utils.update_sug_url_zd
#     elif dbname == "shoushu":
#         url = utils.update_sug_url_ss
#     return url

def update_sug_category(request):
    '''
    更新标注,同时更新数据库的新增分词-标注
    :param request:
    :return:
    '''
    if request.method == "POST":
        origin_ctg = eval(request.POST.get("origin_ctg", ""))
        new_ctg = eval(request.POST.get("new_ctg", ""))

        updates = {}

        for i in range(len(origin_ctg)):
            if origin_ctg[i] != new_ctg[i]:
                if new_ctg[i] not in origin_ctg:

                    # utils.get_database(request.session.get(utils.SESSION_DB, "")).update_sug_category(updates)
                    utils.get_database(request.session.get(utils.SESSION_DB, "")).update_categories(new_ctg[i])
                updates[origin_ctg[i].decode('utf8')] = new_ctg[i].decode('utf8')
                utils.get_database(request.session.get(utils.SESSION_DB, "")).update_sug_category(updates)
                utils.get_database(request.session.get(utils.SESSION_DB, "")).delete_category(origin_ctg[i])

        # new_dic = {}
        # for k, v in updates.iteritems():
        #     new_dic[k.decode('utf8')] = v.decode('utf8')
        # # utils.database.update_categories(new_dic)  # 更新数据库中的标注名称
        # utils.get_database(request.session.get(utils.SESSION_DB, "")).update_sug_category(new_dic)  # 更新分词对应的标注
        # 更新服务
        requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")), data=request.session.get(utils.SESSION_DB, ""), headers=utils.headers)

        return HttpResponse("", content_type='application/text')


def delete_sug_category(request):
    '''
    删除某个标注和该标注下的分词
    :param request:
    :return:
    '''
    if request.method == "POST":
        category = request.POST.get("category", "")
        utils.get_database(request.session.get(utils.SESSION_DB, "")).delete_category(category)
        utils.get_database(request.session.get(utils.SESSION_DB, "")).delete_items_by_sug(category)
        # 更新服务
        requests.post(utils.update_sug_url(request.session.get(utils.SESSION_DB, "")), data=request.session.get(utils.SESSION_DB, ""), headers=utils.headers)

        return HttpResponse("", content_type='application/test')

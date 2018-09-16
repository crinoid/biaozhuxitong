# coding=utf8
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect

from utils import utils

import os
import xlwt, xlrd
import json
import requests
import re
import sys
import logging

error_logger = logging.getLogger('error')

def segment(request):
    if not utils.check_user_session(request):
        return HttpResponseRedirect("/login/")
    return render_to_response("segment.html", "")


def send_segment(request):
    '''
    get segment

    :param request:
    :return:
    '''
    if request.method == "POST":
        utils.update_db(request)
        dbname=request.POST.get("db", "")
        try:
            info = dict()
            info['seg'] = dict()
            info['origin'] = dict()
            info['source'] = dict()
            # info['checked'] = []  # 已经查看过的index

            filename = request.session.get(utils.SESSION_FILE, "")
            msg_list = []  # 分词结果
            if filename == "":
                msg = request.POST.get("msg", "")
                msg_list = seg_from_disk(msg)
            else:
                msg_list = seg_from_file(filename)


            # 分词每次分MAX_TERM个，避免时间过长
            # seg_list = call_seg_api(json.dumps({"diag": msg_list}))["diag"]
            data = msg_list[:utils.SEGS_PER_PAGE] if len(msg_list) > utils.SEGS_PER_PAGE else msg_list
            seg_list = update_segments(data,dbname)

            terms = []  # 文本的分词
            i = 1
            # msg_list是正序的，为了保持顺序（遍历字典顺序会错乱），通过msg_list遍历
            for origin in msg_list:
                info['origin'][i] = origin
                # 获取第一页的分词，显示来源
                if i <= utils.SEGS_PER_PAGE:
                    info['seg'][i] = dict()
                    tmp=[]
                    for j in range(len(seg_list[origin])):
                        seg_list[origin][j] = seg_list[origin][j].decode('utf8')
                        info['seg'][i][j + 1] = [s for s in seg_list[origin][j]]
                        tmp.append(seg_list[origin][j])
                    terms.append(tmp)
                i += 1

            info['source'] = get_seg_source(request.session.get(utils.SESSION_DB, ""), terms)
            info["page_count"] = utils.SEGS_PER_PAGE
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            output = ",".join([str(e), fname, str(exc_tb.tb_lineno)])
            error_logger.info(request.session.get("username", "") + " - 分词服务错误 - " + output)

        return HttpResponse(json.dumps(info), content_type='application/json')


def update_segments(data, dbname):
    return call_seg_api(json.dumps({"diag": data}), dbname)["diag"]


def call_seg_api(data, dbname):
    # 调用分词服务
    if dbname == "zhenduan":
        url = utils.seg_service_url_zd
    elif dbname == "shoushu":
        url = utils.seg_service_url_ss
    res = requests.post(url, data=data, headers=utils.headers).content.decode('utf8')
    return eval(res)


def seg_from_disk(msg):
    '''
    手动输入-分词
    :param msg: 输入的文本
    :return: 一组分词
    '''
    if isinstance(msg, str):
        msg = msg.decode('utf8')

    msg_list = []
    for content in re.split(u'[，。,.\n]', msg):
        if content:  # 文本不为空
            # 去掉多余字符，如两头的空格（trim?）
            # msg = utils.remove_special_word(content)
            if isinstance(content, unicode):
                msg_list.append(content.encode("utf8"))
    return msg_list


def seg_from_file(filename):
    '''
    从文件读取分词
    :param filename: 文件名
    :return:
    '''
    msg_list = []
    ext = filename.split(".")[-1]
    if ext == "txt" or ext == "csv":
        for line in open(os.path.join("uploads/", filename)).readlines():
            line = line.strip()
            if line:  # 文本不为空
                content = line.split("\t")[0]
                # msg = utils.remove_special_word(content).replace(",", u"，")
                if isinstance(content, unicode):
                    content = content.encode("utf8")
                msg_list.append(content)

    elif ext == "xls" or ext == "xlsx":
        wb = xlrd.open_workbook(os.path.join("uploads/", filename))
        # m = 0  # 总共诊断数
        for k in range(len(wb.sheets())):
            ws = wb.sheet_by_index(k)
            for i in range(ws.nrows):
                line = ws.cell(i, 0).value.strip()
                # 获得处理过的分词，暂时不需要
                # if len(ws.row_values(i)) > 1 and ws.row_values(i)[1] != "":
                #     info['checked'].append(m)
                # 去掉特殊字符
                # msg = utils.remove_special_word(line).replace(",", u"，")
                msg_list.append(line)
    return msg_list


# 切换页面，重新加载分词来源
def update_seg_source(request):
    if request.method == "POST":
        items = request.POST.get("terms", "")  # [诊断1，诊断2...]
        is_seg = request.POST.get("is_seg", False)  # 是否分词
        items = items.split(utils.SEP)[:-1]

        # for k in range(len(items)):
        #     tmp = []
        #     for s in items[str(k)]["seg"]:
        #         tmp.append(merge_segs(s)) #将分词合并成诊断，相当于原文
        #     terms.append(tmp)

        res = {}
        if is_seg:
            res_segs = update_segments(items,request.session[utils.SESSION_DB])  # 更新分词
            res["segs"] = []
            terms = []
            # 保证顺序不变，依照items的来
            for k in items:
                v = res_segs[k.encode('utf8')]
                # for k,v in res_segs.iteritems():
                tmp1 = []
                for s in v:
                    tmp = []
                    for s1 in s.decode("utf8"):
                        tmp.append(s1)
                    tmp1.append(tmp)
                res["segs"].append(tmp1)

                terms.append(res_segs[k.encode('utf8')])

            # for k,v in res_segs.iteritems():
            #     terms.append(v)
            res["sources"] = get_seg_source(request.session.get(utils.SESSION_DB, ""), terms)  # 更新来源

        return HttpResponse(json.dumps(res), content_type='application/json')


def get_seg_source(dbname, terms):
    '''
    每次分页，加载分词来源
    :param dbname: session中的数据库名称
    :param terms: 一组分词[[高血压,3级],[右眼,外伤]...]，length=每页分词个数
    :return:
    '''
    res = utils.get_database(dbname).get_seg_source(terms, utils.MAX_TERMS)
    return res


def merge_segs(segs):
    res = ""
    for seg in segs:
        res += seg
    return res

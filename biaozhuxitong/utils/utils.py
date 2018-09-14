# coding=utf8

import codecs
import random
import string
import chardet
import commands

from database.zhenduan import ZhenDuan
from database.shoushu import ShouShu

import requests

from pyfasttext import FastText

# ft_model=FastText()
# ft_model.load_model('bcjl_model.bin')


SPECIAL_CHARACTERS = ['*', '°', '%', '＋', '—', '～', '±', '\\', ']', '[', '#', '/', '+', '┘', '\n', '\t', '\r\n', ' ']

COLOR_LIST = ["#c0a16b", "#e4b9c0", "#f7ecb5", "#31b0d5", "#add8e6", "#8fbc8f",
              "#6495ed", "#dda0dd", "#bdb76b", "#ffe4b5", "#e1ffff", "#cce59a"]

UNKNOWN_COLOR = "#fffff0"

seg_service_url_zd = "http://127.0.0.1:8002/seg_service"
sug_service_url_zd = "http://127.0.0.1:8002/sug_service"
all_segs_service_url_zd = "http://127.0.0.1:8002/get_all_segs"
update_seg_url_zd = "http://127.0.0.1:8002/update_seg"
update_sug_url_zd = "http://127.0.0.1:8002/update_sug"
get_seg_dic_url_zd = "http://127.0.0.1:8002/get_seg_dic"
get_sug_dic_url_zd = "http://127.0.0.1:8002/get_sug_dic"

seg_service_url_ss = "http://127.0.0.1:8001/seg_service"
sug_service_url_ss = "http://127.0.0.1:8001/sug_service"
all_segs_service_url_ss = "http://127.0.0.1:8001/get_all_segs"
update_seg_url_ss = "http://127.0.0.1:8001/update_seg"
update_sug_url_ss = "http://127.0.0.1:8001/update_sug"
get_seg_dic_url_ss = "http://127.0.0.1:8001/get_seg_dic"
get_sug_dic_url_ss = "http://127.0.0.1:8001/get_sug_dic"

match_icd_url = "http://127.0.0.1:8003/match_icd"
match_icd_code_url = "http://127.0.0.1:8003/match_icd_with_code"
# seg_service_url = "http://172.18.18.26:8002/seg_service"
# sug_service_url = "http://172.18.18.26:8002/sug_service"
# all_segs_service_url = "http://172.18.18.26:8002/get_all_segs"
# update_seg_url = "http://172.18.18.26:8002/update_seg"
# update_sug_url = "http://172.18.18.26:8002/update_sug"
# get_seg_dic_url = "http://172.18.18.26:8002/get_seg_dic"
# get_sug_dic_url = "http://172.18.18.26:8002/get_sug_dic"
# match_icd_url = "http://172.18.18.26:8003/match_icd"
# match_icd_code_url = "http://172.18.18.26:8003/match_icd_with_code"

headers = {'content-type': 'application/json'}

######
# session名称
SESSION_USER = "username"
SESSION_DB = "dbname"
SESSION_TERMTYPE="term_type"
SESSION_FILE = "filename"
SESSION_ORIGIN_FILE = "origin_file"
SESSION_ALLDATA = "all_data"
######

UNKNOWN = u"未知"

LOGIN_LOG = "login"
SEGMENT_LOG = "segment"
SUGGEST_LOG = "suggest"
FILEUPLOAD_LOG = "upload"
USER_LOG = "user"  # 记录添加/删除/用户
ERROR_LOG = "error"

FILE_LOGIN_LOG = "f_login.log"
FILE_SEGMENT_LOG = "f_seg.log"
FILE_SUGGEST_LOG = "f_sug.log"
FILE_FILEUPLOAD_LOG = "f_upload.log"
FILE_USER_LOG = "f_user.log"
FILE_ERROR_LOG = "f_error.log"

DIR_UPLOADS = "uploads/"

MAX_TERMS = 10  # 分词/标注查看来源,前10个

SEGS_PER_PAGE = 20  # 分词每页的个数
SUGS_PER_PAGE = 20  # 标注每页的个数


def get_database(db):
    # global database
    if db == "zhenduan":
        return ZhenDuan()
    elif db == "shoushu":
        return ShouShu()


def get_database_name(db):
    if db == "zhenduan":
        return "疾病诊断"
    elif db == "shoushu":
        return "手术操作"

###########
# 根据数据类型更新

def seg_service_url(dbname):
    if dbname == "zhenduan":
        return seg_service_url_zd
    elif dbname == "shoushu":
        return seg_service_url_ss

def update_seg_url(dbname):
    if dbname == "zhenduan":
        return update_seg_url_zd
    elif dbname == "shoushu":
        return update_seg_url_ss

def update_sug_url(dbname):
    if dbname == "zhenduan":
        return update_sug_url_zd
    elif dbname == "shoushu":
        return update_sug_url_ss

###########

def check_user_session(request):
    if request.session.get("username", "") != "":
        return True
    else:
        return False


# 去掉特殊字符,type=unicode
def remove_special_word(word):
    if isinstance(word, str):
        word = word.decode("utf8")

    for char in SPECIAL_CHARACTERS:
        word = word.replace(char, "")
    # session["cut"] = 1
    return word.strip()


# 随机字符串,文件重命名
def random_string():
    salt = ''.join(random.sample(string.ascii_letters + string.digits, 8))
    return salt


# 将上传文件转成unicode编码
def convert_unicode(line):
    if chardet.detect(line)["encoding"] != "utf-8":
        line = line.decode("gbk")
    return line


def write_to_file(upload_file, target_file, ext):
    '''
    保存上传的文件，写入新的文件
    :param upload_file:上传文件名
    :param target_file:新文件文件名
    :param ext:文件扩展名
    :return:
    '''
    destination = open(target_file, 'wb+')  # 打开特定的文件进行二进制的写操作
    for chunk in upload_file.chunks():  # 分块写入文件
        if ext == "txt" or ext == "csv":  # 只有文本文档涉及编码
            chunk = convert_unicode(chunk)
        destination.write(chunk)
    destination.close()


# 得到所有标注+颜色
def get_suggests_dic(db):
    mark_dic = {}
    mark_dic[u"未知"] = UNKNOWN_COLOR
    lines = get_database(db).get_categories()
    for i in range(len(lines)):
        # 标注个数超过自定义颜色数,背景色为白色
        if i < len(COLOR_LIST):
            mark_dic[lines[i]] = COLOR_LIST[i]
        else:
            mark_dic[lines[i]] = "#fff"
    return mark_dic


# 所有标注
def get_suggestions(db):
    return get_database(db).get_categories()


def add_suggests(suggests):
    f = open("data/distinct_category.dat", 'aw')
    for s in suggests:
        f.write(s + "\n")
    f.close()


def get_seg_sug_count():
    pass

# def auto_match(term,dbname,size=10):
#     '''
#     找到跟某个未知的词相关的size个，预测成分
#     :param term: 输入的词
#     :param database: 数据库
#     :param size:
#     :return: 成分
#     '''
#     # return ""
#     dic = {u"部位": 0, u"中心词": 0, u"病因": 0, u"病理": 0, u"特征词": 0, u"连接词": 0, u"判断词": 0, u"其他": 0, u"未知": 0}
#     similarity = {}
#     weight = 2
#     i = 0
#     term=term.encode('utf8')
#     for m in ft_model.nearest_neighbors(term, k=size):
#         weight -= 0.2
#         try:
#             database=ZhenDuan()
#             if dbname=="shoushu":
#                 database=ShouShu()
#             a = database.get_suggest_from_seg(m[0])[0]
#             dic[a["sug"]] += m[1] + weight
#             similarity[str(i)] = [m[0], a["sug"], round(m[1], 4)]
#             i += 1
#         except:
#             # 降低未知的权值，保证如果有识别出的成分，选择那个成分
#             dic[u"未知"]+= m[1] + weight*0.001
#             similarity[str(i)] = [m[0], u"未知", round(m[1], 4)]
#             i += 1
#
#     sug = sorted(dic.items(), key=lambda x: x[1], reverse=True)[0]
#     return sug[0]


def delete_category(category):
    f = open("tmp.csv", "w")
    for line in open("data/distinct_category.dat").readlines():
        if not line.strip() == category:
            f.write(line)
    f.close()

    commands.getstatusoutput("mv tmp.csv " + "data/distinct_category.dat")


# 术语分词,将当前term分隔
def seperate_term(target, terms):
    res = ""
    for term in terms:
        if term == target:
            res += "/" + term + "/"
        elif term != "":
            res += term
    return res.replace("//", "/")  # 两个相同的term连在一起,去掉多出的/


def update_nav_style(dic, db_name):
    if db_name == "zhenduan":
        dic['active_zd'] = True
        dic['color_zd'] = "#555"
        dic['active_ss'] = False
        dic['color_ss'] = "#fff"
    else:
        dic['active_zd'] = False
        dic['color_zd'] = "#fff"
        dic['active_ss'] = True
        dic['color_ss'] = "#555"
    return dic

def update_db(request):
    '''
    更新所选术语集(数据库名称)
    :param request:
    :return:
    '''
    db = request.POST.get("db", "")
    if db:
        request.session[SESSION_DB] = db
        # SESSION_DB=db

# 调用api，如分词，标注服务
def call_api(url, data):
    res = requests.post(url, data=data, headers=headers).content.decode('utf8')
    return eval(res)

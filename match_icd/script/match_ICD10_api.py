# encoding=utf8
from __future__ import unicode_literals
from collections import OrderedDict
import re
from fuzzywuzzy import fuzz
from copy import deepcopy
import codecs
import sys
import requests
import json

import utils
from build_icd import build_icd_norm, build_icd_type_norm, build_icd_code_dict

from elasticsearch2 import Elasticsearch

es = Elasticsearch()

reload(sys)
sys.setdefaultencoding('utf-8')

MATCH_COUNT = 10
ACCURACY = 55

'''
预处理
'''


def get_config(type):
    source_dic = {}
    for line in open("config.txt").readlines():
        t, k, v = line.strip().split(" ")
        if t == type:
            source_dic[k] = v
    return source_dic


def replace_punctuation(content):
    if isinstance(content, float):
        return str(content)

    _chinese_english = [
        (u'，', u','),
        (u'、', u','),
        (u'（', u'('),
        (u'）', u')'),
        (u'。', u'.'),
        (u'；', u';'),
        (u'：', u':'),
        (u'“', u'"'),
        (u'－', u'-'),
        (u' ', u''),
        (u'°', u''),
        (u'？', u'')
    ]
    for i in _chinese_english:
        content = content.replace(i[0], i[1]).upper()

    _filter_punctuation = [u'"', u'\'']
    for i in _filter_punctuation:
        content = content.replace(i, u'')

    return content

def remove_punctuation(content):
    punctuation = [
        u',', u',', u'(', u')', u'.', u';', u':', u'"', u'-', u'', u'', u''
    ]
    for p in punctuation:
        content = content.replace(p, "")
    return content


def pre_load(source_dic, CACHE_PATH, TMP_PATH, update_types):
    '''
    检查icd_name是否更新，若更新，重新生成cache文件，并更新tmp文件
    :param source_dic: {LC:国家临床版,GB:国家版}
    :return:
    '''
    for file_pre, file_name in source_dic.iteritems():
        f1_path = CACHE_PATH + file_pre + '_icd_name.csv'
        f2_path = TMP_PATH + file_pre + '_icd_name_shoushu.csv'

        if not utils.file_compare(f1_path, f2_path):
            # 文件改变，重新生成cache
            build_icd_norm(CACHE_PATH + file_pre + "_icd_name.csv",
                           CACHE_PATH + file_pre + "_icd_norm.csv", utils.SERVICE_URL_SS)
            for type, name in update_types.iteritems():
                build_icd_type_norm(CACHE_PATH + file_pre + "_icd_name.csv",
                                    CACHE_PATH + file_pre + "_icd_" + type + ".csv", name, file_name)
            build_icd_code_dict(CACHE_PATH + file_pre + "_icd_name.csv",
                                CACHE_PATH + file_pre + "_icdcode_dict.csv", file_name, 2)
            # 更新tmp文件
            utils.copy_file(f1_path, f2_path)


def extract_icd(icd_norm_path):
    '''
    获得所有icd
    :return:
    '''
    icd_norm = codecs.open(icd_norm_path, encoding="utf8")
    icd_dict = dict()
    for line in icd_norm.readlines():
        item = line.split("\t")
        icd_dict[item[0]] = [item[2], item[1].replace("\n", "")]  # 分词,编码
    return icd_dict


def build_code_dict(path):
    '''

    :param path:
    :return: key=编码,value=编目
    '''
    code_dict = {}
    for line in open(path).readlines():
        try:
            line_list = line.strip().split("\t")
            code_dict[line_list[1]] = line_list[0]
        except:
            print line
    return code_dict

def build_syn_dic1(syn_file_path):
    syn_dict = {}
    for line in open(syn_file_path).readlines():
        syns = line.strip().split("\t")
        for s in syns:
            cp_syns = deepcopy(syns)
            cp_syns.remove(s)
            syn_dict[s] = cp_syns

    return syn_dict

def build_syn_dic(syn_file_path):
    syn_dict = []
    # for line in open(syn_file_path).readlines():
    #     syns = line.strip().split("\t")
    #     for s in syns:
    #         cp_syns = deepcopy(syns)
    #         cp_syns.remove(s)
    #         syn_dict[s] = cp_syns
    for line in open(syn_file_path).readlines():
        syn_dict.append(line.strip().split("\t"))
    return syn_dict


'''
匹配部分
'''

def is_similar(term1,term2,sentence,syn_dict):
    '''
    判断两个部位是否是同义词
    :param term1:
    :param term2: sentence的term
    :param sentence:原文
    :param syn_dict:
    :return:
    '''
    if term1 in sentence: #e.g term1=肝 sentence=多囊肝
        return 0
    # if term1 in term2 or term2 in term1:
    #     return 0

    try:
        if term2 in syn_dict[term1]:
            return 0
    except:
        pass
    try:
        if term1 in syn_dict[term2]:
            return 0
    except:
        pass

    return 1

def get_ratio(term1,term2):
    '''
    计算两个词的相似度，不考虑顺序
    :param term1:
    :param term2:
    :return:
    '''
    if type(term1)==str:
        term1=term1.encode("utf8")
    if type(term2)==str:
        term2=term2.encode("utf8")

    def split_word(term):
        return " ".join([t for t in term])
    term1=split_word(term1)
    term2=split_word(term2)

    r1 = fuzz.token_sort_ratio(term1,term2,force_ascii=False)
    r2 = fuzz.token_set_ratio(term1,term2,force_ascii=False)
    return (r1+r2)/2

def match_all_code(icd_list, code_list, source_list, pos, size):
    '''
    只输入编码，按编码匹配
    完全一样的，返回；没有完全一样的，返回前3位对应的所有条目
    :param code: [code1,code2...]
    :return: list，[icd,code] [[icd1,code1],[icd2,code2]...]
    '''

    def match(code):

        def match_detail(code, match1, pos):
            for c in icd_list[s]["icd"][code[:pos]]:
                if c[1] == code or c[1].upper() == code:
                    same_list.append(c)
                else:
                    match1.append(c)

        find_list, match_list, part_list, same_list = [], [], [], []
        for s in source_list:
            match1 = []
            if code[:pos] in icd_list[s]["icd"].keys():
                match_detail(code, match1, pos)
                match_list.append(match1)

        # 完全匹配的放在最前
        find_list.extend(same_list)

        if match_list:
            if "." in code and len(code.split(".")[1]) > 0:
                for i in range(len(code), len(code.split(".")[0]) + 1, -1):
                    tmp = code[:i]
                    for c in match_list[0]:
                        if tmp in c[1]:
                            part_list.append(c)
                            match_list[0].remove(c)

        find_list.extend(part_list)
        if match_list:
            # code不完全匹配icd的穿插插入
            for idx in range(max(len(m_list) for m_list in match_list)):
                for i in range(len(match_list)):
                    if idx < len(match_list[i]):
                        find_list.append(match_list[i][idx])
        # 取前size个
        find_list = find_list[:size] if len(find_list) > size else find_list
        return find_list

    return map(match, code_list)


def update_res(old_data, new_data):
    try:
        if old_data:
            res = {}
            for k, v in new_data.iteritems():
                new_list = []
                top = old_data[k][0][2]
                i = 0
                j = 0
                while i < len(v) and j<len(old_data[k]):
                    if v[i][2] > top:
                        new_list.append(v[i])
                        i += 1
                        top = old_data[k][j][2]
                    else:
                        new_list.append(old_data[k][j])
                        j += 1
                        top = v[i][2]
                    if len(new_list) == MATCH_COUNT:
                        break
                if len(new_list)<MATCH_COUNT and j<len(old_data[k])-1:
                    while j<len(old_data[k]):
                        new_list.append(old_data[k][j])
                res[k] = new_list
        else:
            res=new_data
    except Exception,e:
        res=new_data

        # if k in res.keys():
        #     if len(res[k]) < MATCH_COUNT:
        #         total = len(res[k])
        #         for v1 in v:
        #             if v1 not in res[k]:
        #                 res[k].append(v1)
        #                 total += 1
        #                 if total == MATCH_COUNT:
        #                     break
        # else:
        #     res[k] = v
    return res


def build_res_dict(res, dis_sentence):
    '''
    返回icd不足n个的诊断
    :param res:
    :param dis_sentence:
    :param is_dict:
    :return:
    '''
    # dis_list:icd，没有code
    dis_list = dis_sentence
    if len(res.keys()):
        for k, v in res.iteritems():
            k_no_code = k.split("\t")[0]
            if isinstance(dis_list, list):
                if k_no_code in dis_list:
                    dis_list.remove(k_no_code)
                elif k in dis_list:
                    dis_list.remove(k)
            else:
                if k_no_code in dis_list:
                    del dis_list[k_no_code]
                elif k in dis_list:
                    del dis_list[k]

    return dis_list

# def check_region(match_group,diag_key,sentence):
#
#     for i in match_group[diag_key].keys(): #i:icd
#         diag = i
#         seg_res = seg_sentence(diag, False)
#         for t in seg_res:
#             if "部位" in t:
#                 regions = t["部位"]
#                 is_match = 1
#                 # 如果icd所有的部位与diag所有的部位都不相同（相似度较小），排除
#                 for r in regions:
#                     try: # sentence可能没有部位
#                         for diag in sentence["部位"]:
#                             is_match = is_similar(r, diag, sentence["原文"],{})
#                     except:
#                         pass
#
#                 if is_match == 1:
#                     del match_group[diag_key][i]
#             # icd如果带有"不伴"，"不伴有",这部分不能出现在
#             if "不伴" in i:
#                 not_include=i.split("不伴")[1]
#                 if sentence["原文"].find(not_include)>-1:
#                     del match_group[diag_key][i]
#     return match_group

# 相似度匹配要检查部位是否一样,match_term:相同部位,由于可能用了同义词,此部位不参与比较
def check_region(diagnose, region_list,region):
    if not region:
        return t
    for r in region:
        if r in diagnose:
            return True
        else:
            replacements = {"左": "", "右": "","前": "", "后": "", "双": "","部": "", "内": "", "外": "","侧":""}
            r = "".join([replacements.get(c, c) for c in r])
            if r in diagnose:
                return True

    else:
        # 相似度匹配，这个过后写
        # for r in region_list:
        #     if is_similar(r,region):
        #         return True
        return False


def icd_part_in_dis(icd_list, dis, icd, source,types):
    try:
        # source = get_source_code(source)
        source="LC"
        icd_dic = eval(icd_list[source]['norm'][icd][0])
        dis_rep = replace_digits(dis)

        for type in types:
            if type in icd_dic:
                for i in icd_dic[type]:
                    if replace_digits(i) not in dis_rep:
                        return False
    except:
        return False
    return True


def get_terms_with_same_icd3(icd_list, dis_sentence, source_list, pos):
    '''
    按输入的编码的前pos位匹配
    :param dis_sentence: {icd:code}
    :param icd_file:
    :return:
    '''

    res = {}
    for icd, code in dis_sentence.iteritems():
        icd_file = {}
        for s in source_list:
            if code[:pos] in icd_list[s]['icd']:
                v = deepcopy(icd_list[s]['icd'][code[:pos]])
                k = code[:pos]
                if k in icd_file.keys():
                    icd_file[k].extend(v)
                else:
                    icd_file[k] = v

        res[icd] = []
        targets = {}
        if code[:pos] in icd_file.keys():
            icd_list = icd_file[code[:pos]]

            flag = False  # 是否有完全匹配
            for i in icd_list:
                # 去掉标点，数字格式统一
                r = fuzz.ratio(remove_para(icd), remove_para(i[0]))
                if len(i[0]) <= len(icd) and icd_part_in_dis(icd, i[0], i[2]):
                    r += 5
                if r < ACCURACY:
                    continue
                targets[i[0] + " " + i[2]] = [i[1], r, i[2]]
                if targets[i[0] + " " + i[2]] == 100:
                    flag = True
            targets_sorted = sorted(targets.keys(), key=lambda d: targets[d][1], reverse=True)

            MAX = MATCH_COUNT if len(targets_sorted) > 5 else len(targets_sorted)
            start = 0
            # 如果最高匹配不是100，即在3位码下没有找到与icd一样的，先整体搜索有没有一样的icd，如果有，放在最高匹配
            if not flag:
                if icd in icd_list.keys():
                    res[icd].append([icd, icd_list[icd][-1], 120])
                    start = 1
            for t in targets_sorted[start:MAX]:
                res[icd].append([t[:t.rindex(" ")], targets[t][0], targets[t][1], targets[t][2]])
    return res


def add_icd_items(icds, new_icd):
    '''
    多个数据来源合并，如 国标的"部位"附加在临床的"部位"后面
    :param icds: 原始icd_list
    :param new_icd: 附加的icd_list
    :return:
    '''
    for k, v in new_icd.iteritems():
        if k in icds.keys():
            icds[k].extend(v)
        else:
            icds[k] = v
    return icds


'''
es搜索部分
'''


def es_reflection(source, source_dic):
    return source_dic[source[-2:].upper()]


def rewrite_search(res, source):
    '''
    es搜索到的整理成对应的形式
    :param res_list:
    :return:
    '''
    return [res["_source"]["icd"], res["_source"]["code"], res["_score"], es_reflection(res["_index"], source)]


def es_search(dis, index, size):
    res = es.search(index=index, body={
        "query": {"multi_match": {
            "query": dis,
            "fields": ["icd"]
        }},
        "size": size,
    })
    return res["hits"]["hits"]


'''
字符替换
'''


def replace_punctuation(content):
    if isinstance(content, float):
        return str(content)

    _chinese_english = [
        (u'，', u','),
        (u'、', u','),
        (u'（', u'('),
        (u'）', u')'),
        (u'。', u'.'),
        (u'；', u';'),
        (u'：', u':'),
        (u'“', u'"'),
        (u'－', u'-'),
        (u'°', u''),
        (u'？', u'')
    ]
    for i in _chinese_english:
        content = content.replace(i[0], i[1]).upper()

    # _filter_punctuation = [u'"', u'\'']
    # for i in _filter_punctuation:
    #     content = content.replace(i, u'')

    return content


def build_digits():
    '''
    将数字统一成阿拉伯数字，匹配有优先级（III 可以识别为 II 和 I，在II和I之前）
    :return:
    '''
    digits_dic = OrderedDict()
    digits_dic["Ⅲ"] = "3"
    digits_dic["III"] = "3"
    digits_dic["ⅠV"] = "4"
    digits_dic["Ⅳ"] = "4"
    digits_dic["V"] = "5"
    digits_dic["Ⅱ"] = "2"
    digits_dic["II"] = "2"
    digits_dic["I"] = "1"
    digits_dic[u"一"] = "1"
    digits_dic[u"二"] = "2"
    digits_dic[u"三"] = "3"

    return digits_dic


# 在匹配时,将罗马数字/大写数字换成阿拉伯数字
def replace_digits(data, digits_dic=build_digits()):
    for k, v in digits_dic.iteritems():
        data = data.replace(k, v)
    return data


# 去掉1. 2.这样的
def remove_digits_with_serial(data):
    patterns = ["\d+\."]
    for p in patterns:
        data = re.sub(p, "", data)

    return data


# 胸11椎体骨折中的数字去掉
def remove_digits(data):
    data = re.sub("\d+", "", data)

    return data


def remove_para(data):
    items = [u"、", u"（", u"）", u",", u"，", "(", ")", u"？", " ", u"-", u"/", u"：", u":", u"."]
    for i in items:
        data = data.replace(i, "")
    return data


# 去掉括号内的内容
def remove_content_in_para(data):
    patterns = ["(.*?)", u"（.*?）", u"(.*?)"]
    for p in patterns:
        data = re.sub(p, "", data)

    return data


# 通过来源名字找到code(国家临床版-->LC)
def get_source_code(source, source_dic):
    for k, v in source_dic.iteritems():
        if source == v:
            return k
    return ""

def seg_sentence(diag,seg_para=False):
    # if diag=="面骨骨折":
    #     print "00000"
    terms_dict = requests.post(utils.SERVICE_URL_ZD,
                               data=json.dumps({"diag": [diag], "seg_para": seg_para}),
                               headers=utils.HEADERS).content.decode('utf8')
    terms_dict = eval(terms_dict)
    if "未知" in terms_dict["diag"][0]:
        for w in terms_dict["diag"][0]["未知"]:
            type=utils.auto_match(w,5)
            terms_dict["diag"][0]["未知"].remove(w)
            if type not in terms_dict["diag"][0]:
                terms_dict["diag"][0][type]=[]
            terms_dict["diag"][0][type].append(w)
    return terms_dict["diag"]

# def sentence_seg(dis):
#     unknown_terms = {}
#     f = open("seg_reseg.csv", "w")
#     terms_dict = requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"diag": dis.keys()}),
#                                headers=utils.HEADERS).content.decode(
#         'utf8')
#     terms_dict = eval(terms_dict)
#     for item in terms_dict["diag"]:
#         flag = True
#         # for i in item.keys():
#         #     if "未知" in i:
#         # for u in item[i]: #未知：[胸壁，及]
#         #     if u not in unknown_terms.keys():
#         #         unknown_terms[u]=0
#         #     unknown_terms[u]+=1
#         #     flag=True
#         #     break
#         if flag:
#             f.write(item["原文"])
#             f.write("\t" + json.dumps(item, ensure_ascii=False))
#             f.write("\t" + dis[item["原文"]])
#             # for k,v in unknown_terms.iteritems():
#             #     f.write(k+"\t"+str(v))
#             f.write("\n")

# print get_ratio("多囊肝","肝多发囊肿")
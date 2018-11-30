# coding=utf8

# from __future__ import unicode_literals
import requests
import json
import xlrd
from fuzzywuzzy import fuzz

import utils


# icd_lines = open("../data/icd/icd_name.csv").readlines()

def extract_icd(path, out_path, icd_idx, code_idx, extra_idx=""):
    with open(out_path, "w") as outfile:
        wb = xlrd.open_workbook(path)
        ws = wb.sheet_by_index(0)
        for i in range(ws.nrows):
            outfile.write(ws.row_values(i)[icd_idx].encode('utf8'))
            outfile.write("\t")
            if ws.row_values(i)[code_idx]:
                outfile.write(ws.row_values(i)[code_idx].encode('utf8'))
            # else:
            #     outfile.write(ws.row_values(i)[1].encode('utf8'))
            # if "单根血管操作" in ws.row_values(i)[icd_idx].encode('utf8'):
            #     a = ws.row_values(i)
            #     print ws.row_values(i)[icd_idx].encode('utf8')
            if extra_idx:
                outfile.write(ws.row_values(i)[extra_idx].encode('utf8'))
            outfile.write("\n")


def build_icd_norm(path, icd_path, service_url):
    '''
    将icd写成分词，标注的形式
    :param path:
    :param icd_path:
    :return:
    '''
    icd_list = []
    icd_dict = {}
    for line in open(path).readlines():
        icd, code = line.strip().split("\t")[0], line.strip().split("\t")[-1]
        icd_list.append(icd)
        icd_dict[icd] = code

    terms_dict = eval(requests.post(service_url, data=json.dumps({"terms": icd_list}),
                                    headers=utils.HEADERS).content.decode('utf8'))

    f = open(icd_path, "w")
    type_dict = {"中心词": "0_core_term", "部位": "1_region_term", "特征词": "2_type_term", "判断词": "3_judge_term",
                 "连接词": "4_connect_term", "其他": "5_others_term", "未知": "dummy_term"}
    # type_dict = {"入路": "0_approach_term", "部位/范围": "1_region_term", "术式": "2_operation_term", "疾病性质": "3_disease_term",
    #              "植入物": "4_implant_term", "其他": "5_others_term", "未知": "dummy_term"}

    for term in terms_dict:
        f.write(term["原文"] + "\t" + icd_dict[term["原文"]])
        new_type_dic = {}
        for type in type_dict.keys():
            if type in term.keys():
                new_type_dic[type_dict[type]] = term[type]
        f.write("\t" + json.dumps(new_type_dic, ensure_ascii=False))
        f.write("\n")


def build_icd_type_norm(icd_path, out_path, type_name, source_name):
    '''
    提取标注类型，写成字典形式，[icd,icd_code]
    :param icd_path: icd文件名
    :param out_path: 输出文件名
    :param type_name: 标注类型
    :return:
    '''

    # reflections = json.load(open("../data/synonyms/region_reflection.json"))

    icd_dict = {}
    icd_list = []
    for line in open(icd_path).readlines():
        line = line.strip().decode("utf8")
        icd, code = line.split("\t")[0], line.split("\t")[-1]
        icd_list.append(icd)
        icd_dict[icd] = code

    f = open(out_path, "w")
    core_dict = {}

    f_region = open("../data/region.csv").readlines()
    for tp in type_name:
        data_set = utils.db.zd_suggest.find({"sug":tp})
        for d in data_set:
            tmp=[]
            for icd in icd_list:
                if d["seg"] in icd:
                    terms_dict = eval(requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"terms": [icd]}),
                                                    headers=utils.HEADERS).content.decode('utf8'))
                    # if "部位" in terms_dict[0].keys():
                    #     regions = terms_dict[0]["部位"]
                    # elif "成分" in terms_dict[0].keys():
                    #     regions = terms_dict[0]["成分"]
                    # else:
                    #     regions=[]
                    try:
                        features = terms_dict[0]["特征词"]
                    except:
                        features = []
                    # 添加可能的部位
                    regions=[]
                    for r in f_region:
                        if r.strip() in icd.encode('utf8'):
                            regions.append(r.strip())
                    tmp.append([icd.encode('utf8'),icd_dict[icd].encode('utf8'),source_name,list(set(regions)),list(set(features))])
            if tmp:
                core_dict[d["seg"].encode('utf8')]=tmp


    # terms_dict = requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"terms": icd_list}),
    #                            headers=utils.HEADERS).content.decode('utf8')
    # terms_dict = eval(terms_dict)
    #
    # for term in terms_dict:
    #     if type_name in term.keys():
    #         if isinstance(type_name, unicode):
    #             type_name = type_name.encode("utf8")
    #         for item in term[type_name]:
    #             try:
    #                 if [term["原文"], icd_dict[term["原文"].decode('utf8')].encode('utf8'), source_name] not in core_dict[
    #                     reflect.encode('utf8')]:
    #                     core_dict[item].append(
    #                         [term["原文"], icd_dict[term["原文"].decode('utf8')].encode('utf8'), source_name])
    #             except:
    #                 core_dict[item] = []
    #                 core_dict[item].append(
    #                     [term["原文"], icd_dict[term["原文"].decode('utf8')].encode('utf8'), source_name])
    #             try:
    #                 for reflect in reflections[item.decode('utf8')]:
    #                     try:
    #                         if [term["原文"], icd_dict[term["原文"].decode('utf8')].encode('utf8'), source_name] not in \
    #                                 core_dict[reflect.encode('utf8')]:
    #                             core_dict[reflect.encode('utf8')].append(
    #                                 [term["原文"], icd_dict[term["原文"].decode('utf8')].encode('utf8'), source_name])
    #                     except:
    #                         core_dict[reflect.encode('utf8')] = []
    #                         core_dict[reflect.encode('utf8')].append(
    #                             [term["原文"], icd_dict[term["原文"].decode('utf8')].encode('utf8'), source_name])
    #             except:
    #                 pass

    f.write(json.dumps(core_dict, ensure_ascii=False, indent=4))

def build_icd_simple(icd_path, out_path, type_name):
    '''
    提取标注类型，写成字典形式，[icd,icd_code]
    :param icd_path: icd文件名
    :param out_path: 输出文件名
    :return:
    '''

    # reflections = json.load(open("../data/synonyms/region_reflection.json"))

    icd_list = open(icd_path).readlines()

    f = open(out_path, "w")
    keyword_dict = {}

    #部位对应 部位 和 成分
    if type_name=="部位":
        all_regions = open("../data/region.csv").readlines()
        for r in all_regions:
            keyword_dict[r.strip()]=[]
    elif type_name=="中心词":
        all_cores = open("../data/core.csv").readlines()
        for r in all_cores:
            keyword_dict[r.strip()]=[]
    if type_name=="部位":
        for icd in icd_list:
            icd=icd.strip()
            terms_dict = eval(requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"terms": [icd]}),
                                            headers=utils.HEADERS).content.decode('utf8'))
            try:
                features = terms_dict[0]["特征词"]
            except:
                features = []

            if "部位" in terms_dict[0].keys():
                for r in terms_dict[0]["部位"]:
                    keyword_dict[r].append([icd,terms_dict[0]["部位"],features])
            if "成分" in terms_dict[0].keys():
                for r in terms_dict[0]["成分"]:
                    keyword_dict[r].append([icd, terms_dict[0]["成分"], features])
            '''
            中心词是否要带部位？理想的分词是中心词不带有部位，如脑积水=>脑/积水，不要整体作为中心词（不使用jieba系统词库）
            中心词使用in来建立key，如脑积水是个常见的中心词，可以不用分得过细为了提取部位，只要有 积水 这个词就行，用in可以将结核对应到肺结核
            这样输入 大脑/积水，通过积水找到脑积水，匹配
            如果输入的编目带有部位，而部位不在词库中，通过中心词查找，中心词对应的编目有部位，需要判断这两个部位是否近似，否则不能匹配
            或者输入的编目的部位有对应的，但最佳匹配的部位是其近似词（如腿&四肢），还需要通过中心词查找，部位近似
                '''

    elif type_name=="中心词":
        for icd in icd_list:
            icd=icd.strip()
            terms_dict = eval(requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"terms": [icd]}),
                                            headers=utils.HEADERS).content.decode('utf8'))
            try:
                features = terms_dict[0]["特征词"]
            except:
                features = []
            for c in keyword_dict.keys():
                if c in icd:
                    keyword_dict[c].append([icd,features])

        # if "中心词" in terms_dict[0].keys():
        #     for r in terms_dict[0]["中心词"]:
        #         keyword_dict[r].append([icd, [], features])

    new_dic={}
    for k,v in keyword_dict.iteritems():
        if v:
            new_dic[k]=v

    f.write(json.dumps(new_dic, ensure_ascii=False, indent=4))

def build_similarity(target, dis):
    '''

    :param target: 诊断名称
    :param dis: 所有icd[icd,code]
    :return:
    '''
    res = []
    for d in dis:
        icd = d.split("\t")[0]
        ratio = fuzz.ratio(target, icd)
        if ratio > 0:
            res.append([d, ratio])
    return sorted(res, key=lambda x: x[1], reverse=True)[:5]


def build_icd_code_dict(icd_path, out_path, source, pos):
    '''

    :param icd_path: icd文件
    :param out_path: 输出文件
    :param source: 国家临床版/国标版/北京临床版
    :param pos: icd编码第一组，如诊断A00.100：前3位，手术00.16002：前2位
    :return:
    '''
    icd_dict = {}
    for line in open(icd_path).readlines():
        icd, code = line.strip().split("\t")[0], line.strip().split("\t")[-1]
        # code_st=code[:pos]
        code_st = code.split(".")[0]
        if code_st not in icd_dict.keys():
            icd_dict[code_st] = []
        icd_dict[code_st].append([icd, code, source])

    f = open(out_path, "w")
    f.write(json.dumps(icd_dict, ensure_ascii=False, indent=4))

def get_unknows_terms(path):
    for icd in open(path).readlines():
        icd=icd.strip()
        terms_dict = eval(requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"terms": [icd]}),
                                        headers=utils.HEADERS).content.decode('utf8'))
        if "部位" not in terms_dict[0].keys() and "中心词" not in terms_dict[0].keys() and "成分" not in terms_dict[0].keys():
            print icd

# extract_icd("../data/icd/北京临床ICD9(v7.01).xls","../data/icd/cache/shoushu/BJ_icd_name.csv",1,0)
# build_icd_norm("../data/icd/cache/zhenduan/LC_icd_name.csv", "../data/icd/cache/zhenduan/LC_icd_norm.csv",utils.SERVICE_URL_ZD)
# build_icd_type_norm("../data/icd/cache/zhenduan/LC_icd_name.csv", "../data/icd/cache/zhenduan/LC_icd_region.json", ["部位","成分"],
#                     "国家临床版")
# build_icd_simple("../data/协和数据匹配/terms.csv", "../data/协和数据匹配/terms_core.json", "中心词")
# build_icd_code_dict("../data/icd/cache/shoushu/BJ_icd_name.csv", "../data/icd/cache/shoushu/BJ_icdcode_dict.csv","北京临床版",2)

# get_unknows_terms("../data/协和数据匹配/terms.csv")

def remove_para(data):
    items = ["、", "（", "）", ",", "，", "(", ")", "？", " ", "-", "/", "：", ":", ".", "［", "］", "[", "]", "%", "~", "†"]
    for i in items:
        data = data.replace(i, "")
    return data


def replace_neg_pos(data):
    prop = {"（+）": "阳性", "（-）": "阴性"}
    for k, v in prop.iteritems():
        data = data.replace(k, v)
    return data


def replace_extra(data):
    return data.replace("†", "+")


def upper(data):
    return data.upper()


def find_difference(path):
    lines = open(path).readlines()
    i = 0
    while i < len(lines):
        if "-----" not in lines[i + 1]:
            if replace_extra(lines[i].split("\t")[1]) == replace_extra(lines[i + 1].split(" ")[1]) or (
                        lines[i].split("\t")[1][:3] == lines[i + 1].split(" ")[1][:3]):
                if not upper(remove_para(lines[i].split("\t")[0])) == upper(remove_para(lines[i + 1].split(" ")[0])):
                    # print remove_para(lines[i].split("\t")[0]), remove_para(lines[i + 1].split(" ")[0])
                    # print lines[i],lines[i+1]
                    pass

        # 内容相同
        if remove_para(replace_neg_pos(lines[i].split("\t")[0])) == remove_para(
                replace_neg_pos(lines[i + 1].split(" ")[0])):
            # icd不同
            if upper(replace_extra(lines[i].split("\t")[-1].strip())) not in upper(lines[i + 1].split(" ")[1]):
                # pass
                print lines[i], lines[i + 1]
            # 完全相同
            else:
                pass
                # print lines[i], lines[i + 1]
            i += 3
        # 未找到匹配
        elif "-----" in lines[i + 1]:
            # print lines[i]
            i += 2
        # 内容不同
        else:
            try:
                # icd大类不同
                if lines[i].split("\t")[1][:3] != lines[i + 1].split(" ")[1][:3]:
                    pass
                    # print lines[i],lines[i+1]
                # icd完全相同
                elif lines[i].split("\t")[1] == lines[i + 1].split(" ")[1]:
                    # print lines[i], lines[i + 1]
                    pass
                # icd大类相同
                else:
                    pass
                    # print lines[i],lines[i+1]
            except:
                pass
                # print lines[i],lines[i+1]
            i += 3

def seg_icd(path):
    '''

    :return:
    '''
    for l in open("../data/icd/cache/zhenduan/"+path+"_icd_name.csv").xreadlines():
        icd=l.split("\t")[0]
        terms_dict = eval(requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"terms": [icd]}),
                                        headers=utils.HEADERS).content.decode('utf8'))
        if "部位" not in terms_dict[0].keys():
            print icd
# find_difference("../data/output/国标-临床版.csv")

# seg_icd("LC")

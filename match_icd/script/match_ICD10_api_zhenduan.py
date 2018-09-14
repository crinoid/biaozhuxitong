# encoding=utf8
from __future__ import unicode_literals
from collections import Counter, OrderedDict
import re
import json
from fuzzywuzzy import fuzz
from copy import deepcopy
import codecs
import requests
import sys
import elasticsearch2

import utils
import match_ICD10_api
from build_icd import build_icd_norm, build_icd_type_norm, build_icd_code_dict

reload(sys)
sys.setdefaultencoding('utf-8')

'''
匹配逻辑

'''
MATCH_COUNT = 10  # 返回的匹配数量

CACHE_PATH = "../data/icd/cache/zhenduan/"
TMP_PATH = "../data/icd/tmp/zhenduan/"

syn_file_path = "../data/synonyms/merged_syn.csv"

es=elasticsearch2.Elasticsearch()

class MatchingICD(object):
    def __init__(self):
        self.MATCH_COUNT = 10  # 返回的匹配数量
        self.ACCURACY = 20  # 匹配度阈值

        self.source_dic = match_ICD10_api.get_config("zd")
        # 检查icd文件是否有更新
        match_ICD10_api.pre_load(self.source_dic,CACHE_PATH,TMP_PATH,{"region": "部位", "core": "中心词"})

        self.icd_list = self.load_cache_files(self.source_dic.keys())

        self.digits_dic = match_ICD10_api.build_digits()
        self.syn_dict = match_ICD10_api.build_syn_dic(syn_file_path)

    def load_cache_files(self, source_list):
        '''
        加载icd缓存，储存形式为：icd[LC]={norm:...,region:...,core:..,}
        :return:
        '''
        icd = {}
        for source in source_list:
            icd[source] = {}
            icd[source]["name"] = match_ICD10_api.build_code_dict("{0}{1}_icd_name.csv".format(CACHE_PATH, source))
            icd[source]["norm"] = match_ICD10_api.extract_icd("{0}{1}_icd_norm.csv".format(CACHE_PATH, source))
            icd[source]["region"] = json.load(open("{0}{1}_icd_region.csv".format(CACHE_PATH, source)))
            icd[source]["core"] = json.load(open("{0}{1}_icd_core.csv".format(CACHE_PATH, source)))
            # icd[source]["type"] = json.load(open("{0}{1}_icd_type.csv".format(CACHE_PATH, source)))
            # icd[source]["others"] = json.load(open("{0}{1}_icd_others.csv".format(CACHE_PATH, source)))
            # icd[source]["unknown"] = json.load(open("{0}{1}_icd_unknown.csv".format(CACHE_PATH, source)))

            icd[source]["icd"] = json.load(open("{0}{1}_icdcode_dict.csv".format(CACHE_PATH, source)))
        return icd

    def get_matched_dis(self,res):
        matched_dis=[]
        for k,v in res.iteritems():
            if len(v)==self.MATCH_COUNT:
                matched_dis.append(k)
        return matched_dis

    def matched_dis(self, dis_list, source_list,size):
        '''

        :param dis_list: 诊断，[诊断1，诊断2...]
        :param source_list: 匹配源，如临床版，国标版 [source1,source2...]
        :return:
        '''
        self.MATCH_COUNT=size
        res = {}

        return self.match_region_core(dis_list, source_list, res)

    def matched_dis_icd(self, dis_sentence, source_list,size):
        '''

        :param dis_sentence: list
        :return:
        '''

        self.MATCH_COUNT = size

        # 按code查找
        res = match_ICD10_api.get_terms_with_same_icd3(self.icd_list,dis_sentence,source_list,pos=3)

        rest_dis = {}  # {icd:code} 按code没找到的
        for dis in dis_sentence.keys():
            if len(res[dis]) < self.MATCH_COUNT:
                rest_dis[dis] = dis_sentence[dis]

        return self.match_region_core(dis_sentence,source_list,res,rest_dis)

    def match_region_core(self,dis_sentence,source_list,res,rest_dis=""):
        diag=dis_sentence
        if rest_dis:
            diag=rest_dis.keys()
        # 诊断标注，提取key=原文，部位，中心词
        terms_dict = requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"diag": diag, "seg_para": False}),
                                   headers=utils.HEADERS).content.decode('utf8')
        terms_dict = eval(terms_dict)

        # 按部位匹配
        res_epoch3 = self.get_same_position(terms_dict, source_list)
        res = match_ICD10_api.update_res(res, res_epoch3)

        matched = self.get_matched_dis(res)

        # 按中心词匹配
        res_epoch4 = self.get_same_core(terms_dict, source_list, matched)
        res = match_ICD10_api.update_res(res, res_epoch4)

        dis_sentence = match_ICD10_api.build_res_dict(res, dis_sentence)

        # 没有找到结果的，用es匹配
        for dis in dis_sentence:
            r = match_ICD10_api.es_search(dis,map(self.source_reflection,source_list))
            res[dis]=map(self.rewrite_search,r)
            # res[dis] = ""

        return res

    def source_reflection(self,source):
        return "zd-icd-"+source.lower()

    def es_reflection(self,source):
        return self.source_dic[source[-2:].upper()]

    def rewrite_search(self,res):
        '''
        es搜索到的整理成对应的形式
        :param res_list:
        :return:
        '''
        return [res["_source"]["icd"],res["_source"]["code"],res["_score"],self.es_reflection(res["_index"])]

    def match_all_code(self,code_list,source_list,size):
        '''
        只输入编码，按编码匹配
        完全一样的，返回；没有完全一样的，返回前3位对应的所有条目
        :param code: [code1,code2...]
        :return: list，[icd,code] [[icd1,code1],[icd2,code2]...]
        '''
        return match_ICD10_api.match_all_code(self.icd_list, code_list, source_list, 3,size)

    def add_icd_items(self, icds, new_icd):
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

    def get_same_position(self, dis_sentence, source_list):
        '''
        按部位匹配
        :param dis_sentence:
        :return:
        '''
        icd_region_file = {}
        for s in source_list:
            tmp = deepcopy(self.icd_list[s]["region"])
            icd_region_file = self.add_icd_items(icd_region_file, tmp)

        return self.get_item_same_type(dis_sentence, "部位", icd_region_file,[])

    def get_same_core(self, dis_sentence, source_list, matched):
        '''
        按中心词匹配
        :param dis_sentence:
        :return:
        '''
        icd_core_file = {}
        for s in source_list:
            tmp = deepcopy(self.icd_list[s]["core"])
            icd_core_file = self.add_icd_items(icd_core_file, tmp)
        return self.get_item_same_type(dis_sentence, "中心词", icd_core_file,matched)

    def get_same_type(self, dis_sentence, source_list):
        '''
        按特征词匹配
        :param dis_sentence:
        :return:
        '''
        icd_type_file = {}
        for s in source_list:
            icd_type_file = self.add_icd_items(icd_type_file, self.icd_list[s]["type"])
        return self.get_item_same_type(dis_sentence, "特征词", icd_type_file)

    def get_same_others(self, dis_sentence, source_list):
        '''
        按其他匹配
        :param dis_sentence:
        :return:
        '''
        icd_others_file = {}
        for s in source_list:
            tmp = deepcopy(self.icd_list[s]["others"])
            icd_others_file = self.add_icd_items(icd_others_file, tmp)
        return self.get_item_same_type(dis_sentence, "其他", icd_others_file)

    def get_item_same_type(self, dis_sentence, type, icd_file,matched):
        '''
        找到按部位或按中心词匹配到的icd，返回相似度最高的前N个icd
        :param dis_sentence: 诊断分词，dict
        :param type: 匹配的类型，部位/中心词
        :param icd_file: icd文件，部位/中心词
        :return:
        '''
        position_dic = dict()

        for sentence in dis_sentence["diag"]:
            diagnose = sentence["原文"]  # 诊断名

            if diagnose in matched:
                continue

            if type in sentence.keys():
                terms = sentence[type]
                icd_list1 = []
                syn_term_list = []
                for term in terms:
                    term = term.strip()

                    if term in icd_file:
                        icd_list1.extend(icd_file[term])
                    if type == "部位":
                        icd_list1, syn_term_list = self.add_region_terms(term, icd_list1, icd_file)
                        # 添加其他同义词
                        icd_list1, syn_term_list = self.add_syn_terms(term, icd_list1, icd_file)
                    elif type == "中心词":
                        icd_list1, syn_term_list = self.add_core_terms(term, icd_list1, icd_file)
                        # 添加其他同义词
                        icd_list1, syn_term_list = self.add_syn_terms(term, icd_list1, icd_file)

                accuracy_threshold = self.ACCURACY
                res = self.get_highest_similarity(diagnose, icd_list1, syn_term_list, term, accuracy_threshold)
                if res:
                    if diagnose not in position_dic.keys():
                        position_dic[diagnose] = res

        return position_dic

    def add_region_terms(self, term, icd_list, icd_file):
        '''
        按部位匹配，添加同义词
        :param term:
        :param icd_list:
        :param icd_file:
        :return:
        '''
        term_list = []
        # 部位带“左/右/前/后”的把“左/右/前/后”去掉 当做同义词
        if term[0] in ["左", "右", "前", "后", "双"]:
            syn_term = term[1:]
            icd_list.extend(icd_file[syn_term] if syn_term in icd_file else [])
        # 末尾为"部"把"部"去掉 （肺部）
        if term[-1] in ["部"]:
            syn_term = term[:-1]
            icd_list.extend(icd_file[syn_term] if syn_term in icd_file else [])
        # 部位带“左侧/右侧/”的把“左侧/右侧”去掉 当做同义词,unicode，取前6个字符
        if len(term) > 2:
            if term[:2] in ["左侧", "右侧", "双侧"]:
                syn_term = term[2:]
                icd_list.extend(icd_file[syn_term] if syn_term in icd_file else [])
        return icd_list, term_list

    def add_core_terms(self, term, icd_list, icd_file):
        '''
        按中心词匹配，添加同义词
        :param term:
        :param icd_list:
        :param icd_file:
        :return:
        '''
        term_list = []
        # 中心词以“病”结尾的,添加“病”去掉的同义词（高血压病&高血压）
        if term[-1] in [u"病", u"症"]:
            syn_term = term[:-1]
            icd_list.extend(icd_file[syn_term] if syn_term in icd_file else [])
        # 将"癌"替换成"恶性肿瘤"
        if u"癌" in term:
            syn_term = term.replace(u"癌", u"恶性肿瘤")
            term_list.append(syn_term)
            icd_list.extend(icd_file[syn_term] if syn_term in icd_file else [])
        elif u"恶性肿瘤" in term:
            syn_term = term.replace(u"恶性肿瘤", u"癌")
            term_list.append(syn_term)
            icd_list.extend(icd_file[syn_term] if syn_term in icd_file else [])
        return icd_list, term_list

    def add_syn_terms(self, term, icd_list, icd_file):
        '''
        将诊断的同义词添加到同义词组中
        :param term:
        :return:
        '''
        term_list = []

        if term in self.syn_dict.keys():
            for syn_term in self.syn_dict[term]:
                term_list.append(syn_term)
                icd_list.extend(icd_file[syn_term] if syn_term in icd_file else [])
        return icd_list, term_list


    def get_highest_similarity(self, dis, icd_list, syn_term_list, match_term, threshold):
        '''
        相似度计算
        :param dis: 诊断名称
        :param icd_list: 可能匹配的icd列表
        :param match_term: 相同的部位/中心词
        :param threshold: 相似度阈值
        :return:[["肾损害","M34",42],["硬皮病肾损害","N28",38]...]
        '''

        targets = dict()  # 所有符合的icd:ratio
        # 去掉诊断中的数字，特殊字符
        dis_rep = match_ICD10_api.remove_digits_with_serial(dis)
        dis_rep = match_ICD10_api.remove_para(match_ICD10_api.replace_digits(dis_rep,self.digits_dic))
        pattern = re.compile("\d+")
        dis_digits = re.findall(pattern, dis_rep)

        icd_list = list(icd_list)
        # icd_list.sort(key=lambda x: len(x))

        # for icds in icd_list:
        def build(icds):
            icd = icds[0]
            icd_rep = match_ICD10_api.remove_para(match_ICD10_api.replace_digits(icd))

            # 如果icd/dis中有数字,如icd=第1肋骨骨折,dis=第2,3肋骨骨折,不对
            flag = True
            icd_digits = re.findall(pattern, icd_rep)
            if len(icd_digits) > 0:
                # icd的数字要都在dis中出现
                for digit in icd_digits:
                    if digit not in dis_digits:
                        flag=False
            # icd在dis中,icd长度<=dis
            if flag:
                if len(icd) <= len(dis) and self.icd_part_in_dis(dis, icd,icds[2]):
                    # 类似2型糖尿病和糖尿病2型,字相同,顺序不同,一定是最匹配的(此时完全一样的已经去掉)
                    if len(dis_rep) == len(icd_rep):
                        targets[icd + " " + icds[2]] = [icds[1], 105, icds[2]]
                    # 其他情况,icd所有词都在dis中,相似度+5
                    # 计算2个相似度,去掉括号内内容和不去掉的
                    else:
                        new_ratio = max(fuzz.ratio(match_ICD10_api.remove_content_in_para(dis), icd_rep),
                                        fuzz.ratio(dis_rep, icd_rep))
                        if new_ratio >= threshold:
                            targets[icd+" "+icds[2]] = [icds[1], new_ratio + 5, icds[2]]

                else:
                    ratio = fuzz.ratio(dis_rep, icd_rep)
                    if syn_term_list:
                        ratio = max(ratio, max(fuzz.ratio(x, icd_rep) for x in syn_term_list))
                    # 相似度不高,但是dis包含了icd,可以考虑
                    if ratio > threshold:
                        targets[icd+" "+icds[2]] = [icds[1], ratio, icds[2]]

        map(build,icd_list)

        results = []
        count = 0
        # 符合的icd由相似度最高到最低,检查是否部位/中心词相同,返回最匹配的
        targets_sorted = sorted(targets.keys(), key=lambda d: targets[d][1], reverse=True)
        for t in targets_sorted:
            # if self.check_region(dis_rep, t, match_term):
            count += 1
            results.append([t[:t.rindex(" ")], targets[t][0], targets[t][1], targets[t][2]])
            if count == self.MATCH_COUNT:
                break

        return results


m_icd = MatchingICD()

# 按icd查找
def icd_service(data, source_list,size=MATCH_COUNT):
    '''

    :param data: json格式的诊断，{diag:[]}
    :return:
    '''

    res = m_icd.matched_dis(data,source_list,size)
    for k, v in res.iteritems():
        print k
        for icd in v:
            print icd[0], icd[1],icd[2], icd[3]
        print "-----"

    return res

# 按icd和code查找（icd可以为空）
def icd_code_service(data,source_list,size=MATCH_COUNT):
    if isinstance(data,dict):
        res = m_icd.matched_dis_icd(data,source_list,size)
    else:
        r = m_icd.match_all_code(data,source_list,size)
        res = {}
        for i in range(len(data)):
            res[data[i]]=r[i]
    # for k, v in res.iteritems():
    #     print k
    #     for icd in v:
    #         print icd[0], icd[1], icd[-1]
    #     print "-----"
    return res

icd_service(["放射治疗"], ["BJ","LC"])
# icd_code_service(["R23.1","R24"], ["BJ","GB","LC"])

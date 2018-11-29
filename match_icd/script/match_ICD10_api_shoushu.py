# encoding=utf8
from __future__ import unicode_literals
import re
import json
from fuzzywuzzy import fuzz
from copy import deepcopy
import requests
import sys
import elasticsearch2

import utils
import match_ICD10_api

reload(sys)
sys.setdefaultencoding('utf-8')

'''
匹配逻辑

'''
MATCH_COUNT = 10  # 返回的匹配数量

CACHE_PATH = "../data/icd/cache/shoushu/"
TMP_PATH = "../data/icd/tmp/shoushu/"

syn_file_path = "../data/synonyms/merged_syn.csv"

PATCH_DATA={}

es=elasticsearch2.Elasticsearch()

def patch(path):
    for line in open(path).readlines():
        try:
            source,target,target_code=line.strip().split("\t")
            PATCH_DATA[source]=[target,target_code]
        except:
            print line

class MatchingICD(object):
    def __init__(self):
        self.MATCH_COUNT = 10  # 返回的匹配数量
        self.ACCURACY = 20  # 匹配度阈值

        self.source_dic = match_ICD10_api.get_config("ss")
        # 检查icd文件是否有更新
        match_ICD10_api.pre_load(self.source_dic,CACHE_PATH,TMP_PATH,{"region": "部位/范围", "core": "术式"})

        self.icd_list = self.load_cache_files(self.source_dic.keys())

        self.digits_dic = match_ICD10_api.build_digits()
        # self.syn_dict = self.build_syn_dic()

        patch("../data/shoushu_patch.csv")

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

            icd[source]["icd"] = json.load(open("{0}{1}_icdcode_dict.csv".format(CACHE_PATH, source)))
        return icd

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
        res = match_ICD10_api.get_terms_with_same_icd3(self.icd_list,dis_sentence,source_list,pos=2)

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
        terms_dict = requests.post(utils.SERVICE_URL_SS, data=json.dumps({"diag": diag}),
                                   headers=utils.HEADERS).content.decode('utf8')
        terms_dict = eval(terms_dict)

        # for item in terms_dict:
        #     if "部位/范围" not in item.keys():
        #         terms_dict["diag"].remove(item)

        # 按部位匹配
        res_region = self.get_same_position(terms_dict, source_list)
        res = match_ICD10_api.update_res(res, res_region)

        dis_sentence = match_ICD10_api.build_res_dict(res, dis_sentence)

        for dis in dis_sentence:
            r = match_ICD10_api.es_search(dis,map(self.source_reflection,source_list),self.MATCH_COUNT)
            res[dis]=map(self.rewrite_search,r)
            # res[dis] = map(match_ICD10_api.rewrite_search, r)

        for k,v in res.iteritems():
            if k in PATCH_DATA.keys():
                for v1 in v:
                    if v1[0] == PATCH_DATA[k][0]:
                        res[k].remove(v1)
                res[k].insert(0,[PATCH_DATA[k][0],PATCH_DATA[k][1],100,"北京临床版"])
                res[k]=res[k][:self.MATCH_COUNT]
                break

        return res

    def source_reflection(self,source):
        return "ss-icd-"+source.lower()

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

        return match_ICD10_api.match_all_code(self.icd_list,code_list,source_list,2,size)

    def get_same_position(self, dis_sentence, source_list):
        '''
        按部位匹配
        :param dis_sentence:
        :return:
        '''
        icd_region_file = {}
        for s in source_list:
            tmp = deepcopy(self.icd_list[s]["region"])
            icd_region_file = match_ICD10_api.add_icd_items(icd_region_file, tmp)
            # icd_region_file = dict(icd_region_file, **self.icd_list[s]["region"])
        return self.get_item_same_type(dis_sentence, "部位/范围", icd_region_file,[])

    def get_item_same_type(self, dis_sentence, type, icd_file,matched):
        '''
        找到按部位或按中心词匹配到的icd，返回相似度最高的前N个icd
        :param dis_sentence: 诊断分词，dict
        :param type: 匹配的类型，部位/中心词
        :param icd_file: icd文件，部位/中心词
        :return:
        '''
        position_dic = dict()

        for sentence in dis_sentence:
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
                    # if type == "部位/范围":
                    #     icd_list1, syn_term_list = self.add_region_terms(term, icd_list1, icd_file)
                        # 添加其他同义词
                        # icd_list1, syn_term_list = self.add_syn_terms(term, icd_list1, icd_file)
                    # elif type == "术式":
                    #     icd_list1, syn_term_list = self.add_core_terms(term, icd_list1, icd_file)
                        # 添加其他同义词
                        # icd_list1, syn_term_list = self.add_syn_terms(term, icd_list1, icd_file)

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

        # for icds in icd_list:
        def build(icds):
            icd = icds[0]
            icd_rep = match_ICD10_api.remove_para(match_ICD10_api.replace_digits(icd,self.digits_dic))

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
                types=["0_approach_term", "1_region_term", "2_operation_term", "3_disease_term", "4_implant_term",
                 "5_others_term",
                 "dummy_term"]
                if len(icd) <= len(dis) and match_ICD10_api.icd_part_in_dis(self.icd_list,dis, icd,icds[2],types):
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
def icd_service(data, source_list,size=MATCH_COUNT,is_enable_ft=False):
    '''

    :param data: json格式的诊断，{diag:[]}
    :return:
    '''

    res = m_icd.matched_dis(data,source_list,size)
    # for k, v in res.iteritems():
    #     print k
    #     for icd in v:
    #         print icd[0], icd[1], icd[2],icd[3]
    #     print "-----"

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

# icd_service(["肋骨取骨术"], ["BJ"])
# icd_code_service(["00.02"], ["BJ","LC"])

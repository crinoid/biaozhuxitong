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

import utils
from build_icd import build_icd_norm, build_icd_type_norm, build_icd_code_dict

from elasticsearch2 import Elasticsearch
es = Elasticsearch()

reload(sys)
sys.setdefaultencoding('utf-8')

'''
匹配逻辑

'''
MATCH_COUNT = 10  # 返回的匹配数量

CACHE_PATH = "../data/icd/cache/zhenduan/"
TMP_PATH = "../data/icd/tmp/zhenduan/"

syn_file_path = "../data/synonyms/merged_syn.csv"

def pre_load(source_dic):
    '''
    检查icd_name是否更新，若更新，重新生成cache文件，并更新tmp文件
    :param source_dic: {LC:国家临床版,GB:国家版}
    :return:
    '''
    for file_pre,file_name in source_dic.iteritems():
        f1_path = CACHE_PATH + file_pre + '_icd_name.csv'
        f2_path = TMP_PATH + file_pre + '_icd_name.csv'

        if not utils.file_compare(f1_path, f2_path):
            # 文件改变，重新生成cache
            build_icd_norm(CACHE_PATH + file_pre + "_icd_name.csv",
                           CACHE_PATH + file_pre + "_icd_norm.csv")
            for type, name in {"region": "部位", "core": "中心词", "type": "特征词", "others": "其他", "unknown": "未知"}.iteritems():
                build_icd_type_norm(CACHE_PATH + file_pre + "_icd_name.csv",
                                    CACHE_PATH + file_pre + "_icd_" + type + ".csv", name, file_name)
            build_icd_code_dict(CACHE_PATH + file_pre + "_icd_name.csv",
                                CACHE_PATH + file_pre + "_icdcode_dict.csv",file_name)
            # 更新tmp文件
            utils.copy_file(f1_path, f2_path)

class MatchingICD(object):
    def __init__(self):
        self.MATCH_COUNT = 10  # 返回的匹配数量
        self.ACCURACY = 20  # 匹配度阈值

        self.source_dic = self.get_config()
        # 检查icd文件是否有更新
        pre_load(self.source_dic)

        self.icd_list = self.load_cache_files(self.source_dic.keys())

        self.digits_dic = self.__replace_digits()
        self.syn_dict = self.build_syn_dic()

    def get_config(self):
        source_dic = {}
        for line in open("config.txt").readlines():
            k,v = line.strip().split(" ")
            source_dic[k]=v
        return source_dic

    def load_cache_files(self, source_list):
        '''
        加载icd缓存，储存形式为：icd[LC]={norm:...,region:...,core:..,}
        :return:
        '''
        icd = {}
        for source in source_list:
            icd[source] = {}
            icd[source]["name"] = self.build_code_dict("{0}{1}_icd_name.csv".format(CACHE_PATH, source))
            icd[source]["norm"] = self.__extract_icd("{0}{1}_icd_norm.csv".format(CACHE_PATH, source))
            icd[source]["region"] = json.load(open("{0}{1}_icd_region.csv".format(CACHE_PATH, source)))
            icd[source]["core"] = json.load(open("{0}{1}_icd_core.csv".format(CACHE_PATH, source)))
            icd[source]["type"] = json.load(open("{0}{1}_icd_type.csv".format(CACHE_PATH, source)))
            icd[source]["others"] = json.load(open("{0}{1}_icd_others.csv".format(CACHE_PATH, source)))
            icd[source]["unknown"] = json.load(open("{0}{1}_icd_unknown.csv".format(CACHE_PATH, source)))

            icd[source]["icd"] = json.load(open("{0}{1}_icdcode_dict.csv".format(CACHE_PATH, source)))
        return icd

    @staticmethod
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

    def build_syn_dic(self):
        syn_dict = {}
        for line in open(syn_file_path).readlines():
            syns = line.strip().split("\t")
            for s in syns:
                cp_syns = deepcopy(syns)
                cp_syns.remove(s)
                syn_dict[s] = cp_syns
        return syn_dict

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

        match_source = []
        for source in source_list:
            match_source.append("zd-icd-"+source.lower())

        # 切词，看有没有部位
        terms_dict = requests.post(utils.SERVICE_URL, data=json.dumps({"diag": dis_list, "seg_para": False}),
                                   headers=utils.HEADERS).content.decode('utf8')
        terms_dict = eval(terms_dict)

        for term in terms_dict["diag"]:
            diag = term["原文"]
            if "部位" in term:
                regions = ""
                for r in term["部位"]:
                    regions+=r+" "

                res_search = es.search(index=match_source, body={
                    "query": {
                        # "match": {"icd":"睾丸肿块"},
                        "bool":{
                            "must":[
                                {"match": {"region": regions[:-1]}}
                            ],
                            "should":[
                                {"constant_score": {
                                    "boost":2,
                                    "query":{
                                "match": {"icd":diag}}

                                }}
                            ]
                        }
                    },
                    "size": 10
                })
            elif "中心词" in term:
                regions = ""
                for r in term["中心词"]:
                    regions += r + " "

                res_search = es.search(index=match_source, body={
                    "query": {
                        # "match": {"icd":"睾丸肿块"},
                        "bool": {
                            "must": [
                                {"match": {"core": regions[:-1]}}
                            ],
                            "should": [
                                # {"match": {"region": regions[:-1]}},
                                {"match": {"icd": diag}},
                            ]
                        }
                    },
                    "size": 10
                })
            else:
                res_search = es.search(index=match_source, body={
                    "query":{
                        # "filtered":{
                        #     "filter": {
                                "match": {"icd":diag}
                            # }
                        # }
                    }
                })
            result = res_search["hits"]["hits"]
            res[diag]=[]
            for r in result:
                res_dic = r["_source"]
                res_dic.pop("region")
                res_dic["source"]=r["_index"]
                res[diag].append(res_dic)
        return res

        # return self.match_region_core(dis_list, source_list, res)

    def matched_dis_icd(self, dis_sentence, source_list,size):
        '''

        :param dis_sentence: list
        :return:
        '''

        self.MATCH_COUNT = size

        # 按code查找
        res = self.get_terms_with_same_icd3(dis_sentence,source_list)

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
        terms_dict = requests.post(utils.SERVICE_URL, data=json.dumps({"diag": diag, "seg_para": False}),
                                   headers=utils.HEADERS).content.decode('utf8')
        terms_dict = eval(terms_dict)

        # 按部位匹配
        res_epoch3 = self.get_same_position(terms_dict, source_list)
        res = self.update_res(res, res_epoch3)

        matched = self.get_matched_dis(res)

        # 按中心词匹配
        res_epoch4 = self.get_same_core(terms_dict, source_list, matched)
        res = self.update_res(res, res_epoch4)

        dis_sentence = self.__build_res_dict(res, dis_sentence)

        for dis in dis_sentence:
            res[dis] = ""

        return res

    def match_all_code(self,code_list,source_list,size):
        '''
        只输入编码，按编码匹配
        完全一样的，返回；没有完全一样的，返回前3位对应的所有条目
        :param code: [code1,code2...]
        :return: list，[icd,code] [[icd1,code1],[icd2,code2]...]
        '''
        self.MATCH_COUNT = size

        def match(code):
        # res = []
        # for code in code_list:
            find_list = []
            match_list = []
            same_list = []
            for s in source_list:
                match1 = []
                if code[:3] in self.icd_list[s]["icd"].keys():
                    for c in self.icd_list[s]["icd"][code[:3]]:
                        if c[1]==code:
                            same_list.append(c)
                            match1=[]
                            break
                        else:
                            match1.append(c)
                    match_list.append(match1)
            # 完全匹配的放在最前
            find_list.extend(same_list)

            if match_list:
                # code不完全匹配icd的穿插插入
                for idx in range(max(len(m_list) for m_list in match_list)):
                    for i in range(len(match_list)):
                        if idx<len(match_list[i]):
                            find_list.append(match_list[i][idx])
            # 取前MATCH_COUNT个
            find_list = find_list[:self.MATCH_COUNT] if len(find_list) > self.MATCH_COUNT else find_list
            return find_list
            # res.append(find_list)
        # return res
        return map(match,code_list)

    def update_res(self, res, data):
        for k, v in data.iteritems():
            if k in res.keys():
                if len(res[k])<self.MATCH_COUNT:
                    total = len(res[k])
                # res[k]=list(set(res[k]).add(v))
                    for v1 in v:
                        if v1 not in res[k]:
                            res[k].append(v1)
                            total+=1
                            if total==self.MATCH_COUNT:
                                break
                # res[k] = self.merged_sorted_array(res[k], data[k])
            else:
                res[k] = v
        return res

    def merged_sorted_array(self, A, B):
        '''

        :param arr: 原数组[[icd1,score1],[icd2,score2]...]
        :param data: 新的icd组[icd,score]
        :return: score MATCH_COUNT
        '''
        if len(A) > len(B):
            big, sm = A, B
        else:
            big, sm = B, A
        i = 0
        while len(sm) > 0:
            n1 = sm[0]
            j = len(big)
            if i == j:
                big.append(n1)
                sm.remove(sm[0])
            elif n1[2] >= big[i][2]:
                # 移除重复icd
                if n1[0] != big[i][0]:
                    big.insert(i, n1)
                i += 1
                sm.remove(sm[0])
            else:
                i += 1
        return big[:self.MATCH_COUNT]

    def __update_terms_dict(self, terms_dict, res):
        for dis, icds in res.iteritems():
            for values in terms_dict["diag"]:
                # 已找到MATCH_COUNT个匹配的icd，移除该诊断
                if values["原文"] == dis and len(icds) == self.MATCH_COUNT:
                    terms_dict["diag"].remove(values)
        return terms_dict

    def __build_res_dict(self, res, dis_sentence):
        '''
        返回icd不足5个的诊断
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
                if isinstance(dis_list,list):
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


    def __replace_digits(self):
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

    def __match_completely(self, dis, icd10):
        '''
        dis和icd完全一样
        :param dis: list数组，诊断名称
        :param icd10: icd字典
        :return: set(匹配到的值)
        '''
        hitting_dis = set(dis).intersection(icd10.keys())

        match_res = {}
        for d in hitting_dis:
            match_res[d] = [[d, icd10[d][-1]]]

        return match_res

    def __extract_icd(self, icd_norm_path):
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
            # icd_region_file = dict(icd_region_file, **self.icd_list[s]["region"])
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

    def get_same_unknown(self, dis_sentence, source_list):
        '''
        按未知匹配
        :param dis_sentence:
        :return:
        '''
        icd_others_file = {}
        for s in source_list:
            icd_others_file = self.add_icd_items(icd_others_file, self.icd_list[s]["unknown"])
        return self.get_item_same_type(dis_sentence, "未知", icd_others_file)

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
        # if u"癌" in term:
        #     term_list.append(term.replace(u"癌", u"恶性肿瘤"))

        if term in self.syn_dict.keys():
            for syn_term in self.syn_dict[term]:
                term_list.append(syn_term)
                icd_list.extend(icd_file[syn_term] if syn_term in icd_file else [])
        return icd_list, term_list

    def get_terms_with_same_icd3(self, dis_sentence,source_list):
        '''
        按输入的编码的前3位匹配
        :param dis_sentence: {icd:code}
        :param icd_file:
        :return:
        '''

        res = {}
        for icd, code in dis_sentence.iteritems():
            icd_file = {}
            for s in source_list:
                if code[:3] in self.icd_list[s]['icd']:
                    v = deepcopy(self.icd_list[s]['icd'][code[:3]])
                    k = code[:3]
                    if k in icd_file.keys():
                        icd_file[k].extend(v)
                    else:
                        icd_file[k] = v

            res[icd] = []
            targets = {}
            if code[:3] in icd_file.keys():
                icd_list = icd_file[code[:3]]

                flag = False  # 是否有完全匹配
                for i in icd_list:
                    # 去掉标点，数字格式统一
                    r = fuzz.ratio(self.remove_para(icd), self.remove_para(i[0]))
                    if len(i[0]) <= len(icd) and self.icd_part_in_dis(icd,i[0],i[2]):
                        r+=5
                    if r < self.ACCURACY:
                        continue
                    targets[i[0]+" "+i[2]] = [i[1], r,i[2]]
                    if targets[i[0]+" "+i[2]] == 100:
                        flag = True
                targets_sorted = sorted(targets.keys(), key=lambda d: targets[d][1], reverse=True)

                MAX = self.MATCH_COUNT if len(targets_sorted) > 5 else len(targets_sorted)
                start = 0
                # 如果最高匹配不是100，即在3位码下没有找到与icd一样的，先整体搜索有没有一样的icd，如果有，放在最高匹配
                if not flag:
                    if icd in self.icd_list.keys():
                        res[icd].append([icd, self.icd_list[icd][-1],120])
                        start = 1
                for t in targets_sorted[start:MAX]:
                    res[icd].append([t[:t.rindex(" ")], targets[t][0],targets[t][1],targets[t][2]])
        return res


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
        dis_rep = self.remove_digits_with_serial(dis)
        dis_rep = self.remove_para(self.replace_digits(dis_rep))
        pattern = re.compile("\d+")
        dis_digits = re.findall(pattern, dis_rep)

        icd_list = list(icd_list)
        # icd_list.sort(key=lambda x: len(x))

        # for icds in icd_list:
        def build(icds):
            icd = icds[0]
            icd_rep = self.remove_para(self.replace_digits(icd))

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
                        new_ratio = max(fuzz.ratio(self.remove_content_in_para(dis), icd_rep),
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

    # 在匹配时,将罗马数字/大写数字换成阿拉伯数字
    def replace_digits(self, data):
        for k, v in self.digits_dic.iteritems():
            data = data.replace(k, v)
        return data

    # 去掉1. 2.这样的
    def remove_digits_with_serial(self, data):
        patterns = ["\d+\."]
        for p in patterns:
            data = re.sub(p, "", data)

        return data

    # 11-12椎体附件骨折的11-12去掉
    def remove_digits_with_conj(self, data):
        patterns = ["\d+-\d+", u"\d+、\d+", u"\d+/\d+"]
        for p in patterns:
            data = re.sub(p, "", data)

        data = re.sub("\d+", "", data)

        return data

    # 胸11椎体骨折中的数字去掉
    def remove_digits(self, data):
        data = re.sub("\d+", "", data)

        return data

    def remove_para(self, data):
        items = [u"、", u"（", u"）", u",", u"，", "(", ")", u"？", " ", u"-", u"/", u"：", u":", u"."]
        for i in items:
            data = data.replace(i, "")
        return data

    # 去掉括号内的内容
    def remove_content_in_para(self, data):
        patterns = ["(.*?)", u"（.*?）", u"(.*?)"]
        for p in patterns:
            data = re.sub(p, "", data)

        return data

    # 通过来源名字找到code(国家临床版-->LC)
    def get_source_code(self,source):
        for k,v in self.source_dic.iteritems():
            if source==v:
                return k
        return ""

    # 判断icd的词是否全部出现在dis中,如"背部挫伤"in"背部皮肤挫伤",这样的词一定匹配,增加相似度
    def icd_part_in_dis(self, dis, icd,source):
        try:
            source = self.get_source_code(source)
            icd_dic = eval(self.icd_list[source]['norm'][icd][0])
            dis_rep = self.replace_digits(dis)
            types = ["0_core_term", "1_region_term", "2_type_term", "3_judge_term","4_connect_term","5_others_term",
                      "dummy_term"]
            for type in types:
                if type in icd_dic:
                    for i in icd_dic[type]:
                        if self.replace_digits(i) not in dis_rep:
                            return False
        except:
            return False
        return True

    # 相似度匹配要检查部位是否一样,match_term:相同部位,由于可能用了同义词,此部位不参与比较
    def check_region(self, dis, icd,source, match_term):
        try:
            if "1_region_term" in eval(self.icd_list[source]['norm'][icd][0]):
                icd_region = eval(self.icd_list[icd][0])["1_region_term"]
                # 保证icd的部位在dis都出现(除了匹配的部位),同时"部位"是正常部位(在self.region_keys里)
                for d in icd_region:
                    if d not in dis:
                        return False
                return True
            return True
        except:
            return False

    def build_code_dict(self, path):
        code_dict = {}
        for line in open(path).readlines():
            line_list = line.strip().split("\t")
            code_dict[line_list[1]] = line_list[0]
        return code_dict


def sentence_seg(dis):
    unknown_terms = {}
    f = open("seg_reseg.csv", "w")
    terms_dict = requests.post(utils.SERVICE_URL, data=json.dumps({"diag": dis.keys()}),
                               headers=utils.HEADERS).content.decode(
        'utf8')
    terms_dict = eval(terms_dict)
    for item in terms_dict["diag"]:
        flag = True
        # for i in item.keys():
        #     if "未知" in i:
        # for u in item[i]: #未知：[胸壁，及]
        #     if u not in unknown_terms.keys():
        #         unknown_terms[u]=0
        #     unknown_terms[u]+=1
        #     flag=True
        #     break
        if flag:
            f.write(item["原文"])
            f.write("\t" + json.dumps(item, ensure_ascii=False))
            f.write("\t" + dis[item["原文"]])
            # for k,v in unknown_terms.iteritems():
            #     f.write(k+"\t"+str(v))
            f.write("\n")


# dis_list = {}
# for line in open("").readlines():
#     dis,count = line.strip().split("\t")
#     dis_list[dis]=count
#
# sentence_seg(
#     dis_list
# )

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
            print icd["icd"],icd["code"],icd["source"]
        # for icd in v:
        #     print icd[0], icd[1], icd[3]
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



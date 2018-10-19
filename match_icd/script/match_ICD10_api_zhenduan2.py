# encoding=utf8
from __future__ import unicode_literals,division
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

1.诊断分词
2.提取部位和中心词，在cache文件中找到含有部位和中心词的icd
3.用ft提取含有部位和中心词的icd
4.cd的部位必须至少包含诊断的一个部位，用ft判断相似度
5.进行similiarity的计算，传入的icdlist建议带成分，特征词不对减分？
6.用es计算，提取前n个，如果没有在res中出现，先判断部位是否对，再用ratio和ft计算相似度，相加
7.按相似度排序，提取前n个

'''

'''
ft识别问题
"肝内多发囊肿", "肝囊肿"=0.912
"肝内多发囊肿", "多发性肝囊肿"=0.905
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
        self.FT_ENABLE=False #中心词/部位若不在key中，是否使用fasttext猜词

        self.source_dic = match_ICD10_api.get_config("zd")
        # 检查icd文件是否有更新
        match_ICD10_api.pre_load(self.source_dic,CACHE_PATH,TMP_PATH,{"region": "部位", "core": "中心词"})

        self.icd_list = self.load_cache_files(self.source_dic.keys())

        self.digits_dic = match_ICD10_api.build_digits()
        # 是个list
        self.syn_dict = match_ICD10_api.build_syn_dic(syn_file_path)

    def load_cache_files(self, source_list):
        '''
        加载icd缓存，储存形式为：icd[LC]={norm:...,region:...,core:..,}
        :return:
        '''
        icd = {}
        icd["rc"]={}
        icd["rc"]["部位"],icd["rc"]["中心词"] = {},{}
        for source in source_list:
            icd[source] = {}
            icd[source]["name"] = match_ICD10_api.build_code_dict("{0}{1}_icd_name.csv".format(CACHE_PATH, source))
            icd[source]["norm"] = match_ICD10_api.extract_icd("{0}{1}_icd_norm.csv".format(CACHE_PATH, source))
            # 小粒度
            # icd[source]["region"] = json.load(open("{0}{1}_icd_region.csv".format(CACHE_PATH, source)))
            # icd[source]["core"] = json.load(open("{0}{1}_icd_core.csv".format(CACHE_PATH, source)))
            # 大粒度
            # icd[source]["region1"] = json.load(open("{0}{1}_icd_region1.csv".format(CACHE_PATH, source)))
            # icd[source]["core1"] = json.load(open("{0}{1}_icd_core1.csv".format(CACHE_PATH, source)))
            regions=json.load(open("{0}{1}_icd_region.csv".format(CACHE_PATH, source)))
            cores=json.load(open("{0}{1}_icd_core.csv".format(CACHE_PATH, source)))
            regions_lg = json.load(open("{0}{1}_icd_region1.csv".format(CACHE_PATH, source)))
            cores_lg = json.load(open("{0}{1}_icd_core1.csv".format(CACHE_PATH, source)))
            icd["rc"]["部位"]=self.get_same_position(regions,regions_lg,icd["rc"]["部位"])
            icd["rc"]["中心词"]=self.get_same_core(cores,cores_lg,icd["rc"]["中心词"])
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

    def matched_dis(self, dis_list, source_list,size,is_enable_ft):
        '''

        :param dis_list: 诊断，[诊断1，诊断2...]
        :param source_list: 匹配源，如临床版，国标版 [source1,source2...]
        :return:
        '''
        self.MATCH_COUNT=size
        self.FT_ENABLE=is_enable_ft
        self.source=source_list
        res = {}

        return self.match_region_core(dis_list, res)

    def matched_dis_icd(self, dis_sentence,size):
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

        return self.match_region_core(dis_sentence,res,rest_dis)

    def match_region_core(self,dis_sentence,source_list,res,rest_dis=""):
        diag = deepcopy(dis_sentence)
        if rest_dis:
            diag = rest_dis.keys()
        # 诊断标注，提取key=原文，部位，中心词
        terms_dict = requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"diag": diag}),
                                   headers=utils.HEADERS).content.decode('utf8')
        terms_dict = eval(terms_dict)

        # 按部位匹配
        res_epoch3 = self.get_same_position(terms_dict, source_list)
        res = match_ICD10_api.update_res(res, res_epoch3)

        matched = self.get_matched_dis(res)

        # 按中心词匹配
        res_epoch4 = self.get_same_core(terms_dict, source_list, matched)
        res = match_ICD10_api.update_res(res, res_epoch4)

        # 整体作为同义词


        # diag = match_ICD10_api.build_res_dict(res, diag)

        rr = []
        for dis in dis_sentence:
            rr.append([dis, res[dis]])

        return rr


    def source_reflection(self,source):
        return "zd-icd-"+source.lower()

    def es_reflection(self,source):
        return self.source_dic[source[-2:].upper()]

    def rewrite_search(self,res,dis):
        '''
        es搜索到的整理成对应的形式
        :param res_list:
        :return:
        '''
        # print res["_score"],utils.get_similarity(dis,res["_source"]["icd"])
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
                # icds[k].extend(v)
                for v1 in v:
                    if not v1 in icds[k]:
                        icds[k].append(v1)
            else:
                icds[k] = v
        return icds

    def get_icds(self, dis_sentence,dis_sentence_lg_size):
        '''
        找到与诊断所含部位/中心词相同/相近的icd
        :param dis_sentence:
        :param source_list:
        :return:
        '''
        icds={}
        # icds["部位"]=self.get_same_position(source_list)
        # icds["中心词"] = self.get_same_core(source_list)
        icds["部位"]=self.icd_list['rc']["部位"]
        icds["中心词"] = self.icd_list['rc']["中心词"]

        return self.get_item_same_type(dis_sentence,dis_sentence_lg_size,icds)

    def get_same_position(self, regions,regions_lg,icd_region_file):
        '''
        按部位匹配
        :param dis_sentence:
        :return:所有部位key与value,如 {三叉神经:[[三叉神经病,G50,国家临床版],[三叉神经麻痹,G50.802,国家临床版]}
        '''
        # 先使用大粒度的，如果没找到，再使用小粒度
        icd_region_file = self.add_icd_items(icd_region_file, regions)
        icd_region_file = self.add_icd_items(icd_region_file, regions_lg)

        return icd_region_file

    def get_same_core(self,core,core_lg,icd_core_file):
        '''
        按中心词匹配
        :param dis_sentence:
        :return:所有中心词key与value
        '''

        icd_core_file = self.add_icd_items(icd_core_file, core)
        icd_core_file = self.add_icd_items(icd_core_file, core_lg)

        return icd_core_file


    def get_similarity_core(self,term,core_list,source,icd_file):
        '''
        从icd的中心词中找跟诊断/手术中心词相近的
        :param term:诊断/手术中心词
        :param source:
        :return:
        '''
        #LC core:3458
        term_list=[]
        for k in self.icd_list[source]["core"].keys():
            if k.find(term)>0:
                # pass
                term_list.append(k)
                core_list.extend(icd_file[k])
            elif utils.predict_similarity(k,term):
                term_list.append(k)
                core_list.extend(icd_file[k])
        return core_list,term_list

    def get_items(self,match_group,terms,type,icd_file,region,diagnose,is_syn,exclude=[]):
        '''
        根据诊断生成能够匹配的icd，如果诊断有部位，部位必须相同/相近
        :param match_group:
        :param terms:
        :param type:
        :param icd_file:
        :param sentence:
        :param diagnose:
        :param is_syn:是否使用同义词列表
        :param exclude:要排除的词
        :return:
        '''

        def source_match():
            for s in self.source:
                if self.source_dic[s] == icd[2]:
                    return True
            return False

        for term in terms:
            print "term=",term
            term = term.strip() #肾占位

            match_group_tmp=deepcopy(match_group)

            # 从icd dict匹配
            if term in icd_file[type]:
                for icd in icd_file[type][term]:
                    if source_match():
                        if icd[0] in match_group[diagnose].keys() and [icd[1],icd[2]] in match_group[diagnose][icd[0]]:
                            pass
                        else:
                            # 如果是中心词匹配，检查部位是否一致
                            if type=="中心词":
                                if match_ICD10_api.check_region(diagnose=icd[0],region_list=[],region=region):
                                    try:
                                        match_group[diagnose][icd[0]].append([icd[1], icd[2]])
                                    except:
                                        match_group[diagnose][icd[0]]=[[icd[1], icd[2]]]
                            else:
                                try:
                                    match_group[diagnose][icd[0]].append([icd[1], icd[2]])
                                except:
                                    match_group[diagnose][icd[0]]=[[icd[1], icd[2]]]

            # 同义词匹配
            if type == "部位":
                if is_syn:
                    match_group, syn_term_list = self.add_syn_terms(term, match_group,diagnose, icd_file, type,exclude)
                else:
                    match_group, syn_term_list = self.add_region_terms(term, match_group, diagnose, icd_file[type],exclude)
            elif type == "中心词":
                if is_syn:
                    match_group, syn_term_list = self.add_syn_terms(term, match_group, diagnose,icd_file, type,exclude)
                else:
                    match_group, syn_term_list = self.add_core_terms(term, match_group, diagnose, icd_file[type],exclude)
                # icd_list1, _ = self.get_similarity_core(term,icd_list1,"LC",icd_file)

            if match_group==match_group_tmp:
                print "======",term
                if self.FT_ENABLE:
                    new_terms = utils.most_similar_n(term, self.icd_list['LC']['core'].keys(), "中心词", 15, n=1)
                    print "new term:",new_term
                    if new_terms:
                        for new_term in new_terms:
                            diag = diag.replace(term, new_term)
                            match_group[diag] = utils.add({}, icd_file, new_term)

        return match_group

    def get_item_same_type(self, dis_sentence,dis_sentence_lg_size,icd_file):
        '''
        找到按部位或按中心词匹配到的icd，返回相似度最高的前N个icd
        :param dis_sentence: 诊断分词，小粒度，dict
        :param icd_file: dict，部位/中心词
        :return:
        '''
        position_dic = dict()

        for i,sentence in enumerate(dis_sentence["diag"]):
            print i
            diagnose = sentence["原文"]  # 诊断名

            # 大粒度匹配
            sentence_lg = dis_sentence_lg_size["diag"][i]

            # match_group:{diag1:{icd1:[code,source],icd2:[]},diag2:{}}
            # diag1,diag2...为synlist的同义词
            # icd部分做成dict为了多次匹配去重
            match_group = {}
            syn_term_list = []
            exclude_term=[]

            # if "连接词" in sentence:
            #     print "connect"
            #     connect_term = sentence["连接词"]
            #     diag_list=diagnose.split(connect_term[0])
            #     for d in diag_list:
            #         match_group[d]={}
            #         seg_words = match_ICD10_api.seg_sentence(d)[0]
            #         for type in ["部位","中心词"]:
            #             if type in seg_words.keys():
            #                 terms=seg_words[type]
            #                 match_group = self.get_items(match_group, terms, type, icd_file, seg_words, d, is_syn=False)


            if "判断词" in sentence:
                judge_term = sentence["判断词"]
                diag_list=diagnose.split(judge_term[0])
                exclude_term.append(diag_list[1])
                # print exclude_term

            match_group[diagnose] = {}

            for type in icd_file.keys(): #部位/中心词

                # 包含同义词匹配
                if type in sentence_lg.keys():
                    terms = sentence_lg[type]
                    region = sentence_lg["部位"] if "部位" in sentence_lg.keys() else ""
                    match_group=self.get_items(match_group,terms,type,icd_file,region,diagnose,is_syn=True,exclude=exclude_term)

                # if not match_group[diagnose]:
                #     print "not find1"
            if not sentence==sentence_lg:
                if "部位" in sentence.keys():
                    terms = sentence["部位"]
                    match_group = self.get_items(match_group, terms, "部位", icd_file,"", diagnose, is_syn=False,
                                             exclude=exclude_term)
                elif "中心词" in sentence.keys():
                    terms = sentence["中心词"]
                    region = sentence["部位"] if "部位" in sentence.keys() else ""
                    match_group = self.get_items(match_group, terms, "中心词", icd_file,region, diagnose, is_syn=False,
                                                 exclude=exclude_term)

            # print len(match_group)
            print "start match"
            accuracy_threshold = self.ACCURACY
            res = self.get_highest_similarity(match_group, syn_term_list, accuracy_threshold)
            if res:
                if diagnose not in position_dic.keys():
                    position_dic[diagnose] = res

        return position_dic

    def add_region_terms(self, term, match_group,diag,icd_file,exclude=[]):
        '''
        按部位匹配，添加同义词
        :param term: 分词（部位）
        :param match_group: {diag:{icd:[code,source]}}
        :param icd_file:
        :return:
        '''

        term_list = []
        # 部位带“左/右/前/后”的把“左/右/前/后”去掉 当做同义词
        if term[0] in ["左", "右", "前", "后", "双"]:
            syn_term = term[1:]
            match_group[diag]=utils.add(match_group[diag],icd_file,syn_term)
        # 末尾为"部"把"部"去掉 （肺部）
        if term[-1] in ["部","内","外"]:
            syn_term = term[:-1]
            match_group[diag] = utils.add(match_group[diag], icd_file, syn_term)
        # 部位带“左侧/右侧/”的把“左侧/右侧”去掉 当做同义词,unicode，取前6个字符
        if len(term) > 2:
            if term[:2] in ["左侧", "右侧", "双侧"]:
                syn_term = term[2:]
                match_group[diag] = utils.add(match_group[diag], icd_file, syn_term)
        return match_group, term_list

    def add_core_terms(self, term, match_group,diag, icd_file,exclude=[]):
        '''
        按中心词匹配，添加同义词
        :param term: 中心词
        :param icd_list:
        :param icd_file:
        :return:
        '''

        term_list = []

        # 中心词以“病”结尾的,添加“病”去掉的同义词（高血压病&高血压）
        if term[-1] in [u"病", u"症"]:
            syn_term = term[:-1]
            match_group[diag] = utils.add(match_group[diag], icd_file, syn_term)
        # 将"癌"替换成"恶性肿瘤"
        if u"癌" in term:
            syn_term = term.replace(u"癌", u"恶性肿瘤")
            term_list.append(syn_term)
            if syn_term not in match_group:
                match_group[syn_term]={}
            match_group[syn_term] = utils.add(match_group[syn_term], icd_file, syn_term)
        elif u"恶性肿瘤" in term:
            syn_term = term.replace(u"恶性肿瘤", u"癌")
            term_list.append(syn_term)
            if syn_term not in match_group:
                match_group[syn_term]={}
            match_group[syn_term] = utils.add(match_group[syn_term], icd_file, syn_term)
        return match_group, term_list

    def add_syn_terms(self, term, match_group, diagnose,icd_file,type,exclude=[]):
        '''
        将诊断的同义词添加到同义词组中
        :param term:
        :return: 带有icd编码列表，匹配到的词
        '''

        def add(match_group, icds, term): # 添加部位验证
            try:
                seg_res = match_ICD10_api.seg_sentence(term, False)[0] #对新的同义词分词
                for type in ["部位","中心词"]:
                    try:
                        for t in seg_res[type]:
                            if t in icds[type]:
                                for item in icds[type][t]:
                                    try:
                                        match_group[item[0]].append([item[1], item[2]])
                                    except:
                                        match_group[item[0]] = [[item[1], item[2]]]
                    except:
                        pass
            except:
                pass
            return match_group

        term_list = []

        for syn_list in self.syn_dict:
            if term in syn_list:
                syn_list.remove(term)
                for s in syn_list:
                    diagnose=diagnose.replace(term,s) #将诊断中同义词替换，作为新的诊断
                    term_list.append(diagnose)
                    if diagnose not in match_group:
                        match_group[diagnose] = {}
                    match_group[diagnose] = add(match_group[diagnose], icd_file, s)

        # if term in self.syn_dict.keys():
        #     for syn_term in self.syn_dict[term]:
        #         term_list.append(syn_term)
        #         icd_list = add(icd_list, icd_file, syn_term)
                # icd_list.extend(icd_file[syn_term] if syn_term in icd_file else [])
        return match_group, term_list


    def get_highest_similarity(self, icd_list, syn_term_list, threshold):
        '''
        相似度计算
        :param icd_list: 可能匹配的icd字典,diag:{icd:[code,source]}
        :param match_term: 相同的部位/中心词
        :param threshold: 相似度阈值
        :return:[["肾损害","M34",42],["硬皮病肾损害","N28",38]...]
        '''

        targets = dict()  # 所有符合的icd:ratio
        # 去掉诊断中的数字，特殊字符
        for dis in icd_list.keys():
            dis_rep = match_ICD10_api.remove_digits_with_serial(dis)
            dis_rep = match_ICD10_api.remove_para(match_ICD10_api.replace_digits(dis_rep,self.digits_dic))
            pattern = re.compile("\d+")
            dis_digits = re.findall(pattern, dis_rep)

            # icd_list.sort(key=lambda x: len(x))

            for icd,items in icd_list[dis].iteritems():
            # def build(icds):
            #     icd = icds[0]

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
                    ratio=match_ICD10_api.get_ratio(dis_rep, icd_rep)
                    # 优化一下，处理简单近似匹配部分
                    ratio2 = match_ICD10_api.get_ratio(dis_rep.replace(u"癌", u"恶性肿瘤"), icd_rep.replace(u"癌", u"恶性肿瘤"))
                    ratio=max(ratio,ratio2)

                    if syn_term_list:
                        ratio = max(ratio, max(match_ICD10_api.get_ratio(x, icd_rep) for x in syn_term_list))
                    new_ratio = max(match_ICD10_api.get_ratio(match_ICD10_api.remove_content_in_para(dis), icd_rep),
                                    match_ICD10_api.get_ratio(dis_rep, icd_rep))
                    ratio=max(ratio,new_ratio)
                    # print ratio
                    if ratio > threshold:
                        new_similarity = utils.get_similarity(dis, icd_rep)
                        #这个地方还可以再调整两者的比例
                        ratio = (ratio + new_similarity*50)/2
                        #一般icd长度小于dis
                        # if len(icd_rep)>len(dis):
                        #     ratio=ratio-(len(icd_rep)>len(dis))*0.5
                        for item in items:
                            targets[icd+" "+item[1]] = [item[0], ratio, item[1]]

            # map(build,icd_list.keys())

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

    res = m_icd.matched_dis(data,source_list,size,is_enable_ft)
    for k in res:
        print k[0]
        for icd in k[1]:
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
    #     print "-----"I
    return res

# print "start"
# import time
# t1=time.time()
# icd_service(["背部麻木"], ["GB","BJ"],size=5)
# t2=time.time()
# print t2-t1
# icd_code_service(["R23.1","R24"], ["BJ","GB","LC"])


# print fuzz.ratio("PH偏低", "低位刚啊")
# print fuzz.ratio("肝多发囊肿", "多发性肝囊肿")
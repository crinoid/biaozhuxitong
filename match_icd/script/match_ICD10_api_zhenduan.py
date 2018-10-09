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

# es = elasticsearch2.Elasticsearch()


class MatchingICD(object):
    def __init__(self):
        self.MATCH_COUNT = 10  # 返回的匹配数量
        self.ACCURACY = 35  # 匹配度阈值

        self.source_dic = match_ICD10_api.get_config("zd")
        # 检查icd文件是否有更新
        match_ICD10_api.pre_load(self.source_dic, CACHE_PATH, TMP_PATH, {"region": "部位", "core": "中心词"})

        self.icd_list = self.load_cache_files(self.source_dic.keys())

        self.digits_dic = match_ICD10_api.build_digits()
        self.syn_dict = match_ICD10_api.build_syn_dic1(syn_file_path)

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
            icd[source]["region"] = json.load(open("{0}{1}_icd_region.json".format(CACHE_PATH, source)))
            icd[source]["core"] = json.load(open("{0}{1}_icd_core.json".format(CACHE_PATH, source)))

            icd[source]["icd"] = json.load(open("{0}{1}_icdcode_dict.csv".format(CACHE_PATH, source)))
        return icd

    def get_matched_dis(self, res):
        matched_dis = []
        for k, v in res.iteritems():
            if len(v) == self.MATCH_COUNT:
                matched_dis.append(k)
        return matched_dis

    def matched_dis(self, dis_list, source_list, size):
        '''

        :param dis_list: 诊断，[诊断1，诊断2...]
        :param source_list: 匹配源，如临床版，国标版 [source1,source2...]
        :return:
        '''
        self.MATCH_COUNT = size
        res = {}

        return self.match_region_core(dis_list, source_list, res)

    def matched_dis_icd(self, dis_sentence, source_list, size):
        '''

        :param dis_sentence: list
        :return:
        '''

        self.MATCH_COUNT = size

        # 按code查找
        res = match_ICD10_api.get_terms_with_same_icd3(self.icd_list, dis_sentence, source_list, pos=3)

        rest_dis = {}  # {icd:code} 按code没找到的
        for dis in dis_sentence.keys():
            if len(res[dis]) < self.MATCH_COUNT:
                rest_dis[dis] = dis_sentence[dis]

        return self.match_region_core(dis_sentence, source_list, rest_dis)

    def keywords_subtitude(self, sentence):
        RULES = [
            ["AFP", "甲胎蛋白"],
            ["BARRETT", "巴雷特"],
            ["CA", "CEA"],
            ["CIN", "子宫颈上皮内瘤变"],
            ["CKD", "慢性肾脏病"],
            ["CPK", "血清磷酸肌酸激酶"],
            ["CK", "血清磷酸肌酸激酶"],
            ["COPD", "慢性阻塞性肺疾病"],
            ["ESS", "鼻内镜外科技术"],
            ["HPV", "人类乳头瘤病毒"],
            ["HP", "幽门螺旋杆菌"],
            ["IBS", "肠易激综合征"],
            ["IGT", "糖耐量减低"],
            ["MDS", "骨髓增生异常综合征"],
            ["PCI", "经皮冠状动脉介入治疗"],
            ["PCOS", "多囊卵巢综合征"],
            ["PICC", "外周穿刺置入中心静脉导管"],
            ["TIA", "短暂性脑缺血发作"],
            ["VVC", "外阴阴道假丝酵母菌病"],
            ["WBC", "白细胞"]
        ]

        def replace(d):
            for rule in RULES:
                d = d.upper()
                d = d.replace(rule[0], rule[1])

                d = re.sub(re.compile("C\d"), "颈椎", d)
                d = re.sub(re.compile("T\d"), "胸椎", d)
                d = re.sub(re.compile("L\d"), "腰椎", d)
                d = re.sub(re.compile("S\d"), "骶椎", d)

            d = match_ICD10_api.replace_punctuation(d)
            d = match_ICD10_api.remove_punctuation(d)
            d = d.split(" ")[0]

            return d

        sentence = map(replace, sentence)
        return sentence

    def match_region_core(self, catalog, source_list, rest_dis=""):
        '''

        :param catalog: 输入编目
        :param source_list: 选取来源
        :param rest_dis:
        :return:
        '''
        catalog = self.keywords_subtitude(catalog)
        if rest_dis:
            catalog = rest_dis.keys()

        def merge(a):
            res = set()
            for i in range(len(a)):
                for j in range(i + 1, len(a) + 1):
                    res.add("".join(a[i:j]))
            return res

        catalog_syns = {}  # 输入编目的同义词替换结果
        all_items = []  # 编目&同义词，都在一个数组中
        terms_dict = requests.post(utils.SERVICE_URL_ZD_SEG, data=json.dumps({"diag": catalog}),
                                   headers=utils.HEADERS).content.decode('utf8')
        terms_dict = eval(terms_dict)
        for item in terms_dict["diag"]:
            syns_item = []
            all_segs = merge(item[1])  # [肺动脉栓塞，肺血栓栓塞……]
            for a in all_segs:
                try:
                    for s in self.syn_dict[a]:
                        syns_item.add(item[0].replace(a, s))
                except:
                    pass
            syns_item.append(item[0])  # 添加编目本身，分词标注用
            syns_item.extend(map(self.add_custom_syn_terms,set(syns_item)))
            syns_item=list(set(syns_item))
            catalog_syns[item[0]] = syns_item
            all_items.extend(syns_item)

        # 诊断标注，提取key=原文，部位，中心词
        terms_dict = requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"diag": all_items}),
                                   headers=utils.HEADERS).content.decode('utf8')
        terms_dict = eval(terms_dict)

        # 把输入整理成如下格式,{输入编目：{同义词:[部位]}}，便于判断部位是否相同
        # syn:{左拇指甲沟炎：{左拇指甲沟炎：[部位1，部位2...],拇指甲沟炎：[部位1，部位2...]}}
        for s in catalog_syns.keys(): #输入编目原文
            new_s = {}
            for term in terms_dict:
                for s1 in catalog_syns[s]:
                    if s1==term["原文"]:
                        try:
                            new_s[s]=term["部位"]
                        except:
                            new_s[s] = []

            catalog_syns[s]=new_s

        res = []  # 匹配结果,[编目，[匹配列表]]
        for k, v in catalog_syns.iteritems(): #k:输入编目，包括部位替换后
            size = len(v.keys())
            # 获得某条编目包含的部位/中心词
            term_by_region = []
            term_by_core = []
            for suged in terms_dict[:size]:
                if "部位" in suged.keys():
                    term_by_region.extend(suged["部位"])
                if "中心词" in suged.keys():
                    term_by_core.extend(suged["中心词"])

            term_by_region = set(term_by_region)
            term_by_core = set(term_by_core)

            # 按部位匹配，返回带有该部位的icd
            icds1 = self.get_same_region(term_by_region, source_list)
            # 按中心词匹配
            icds2 = self.get_same_core(term_by_core, source_list)

            # 合并按部位匹配和按中心词匹配的结果
            icds1.extend(icds2)

            icd_list = []
            for m in icds1:
                # 中心词icd文件带有部位，要保证部位与输入编目的部位相同，或不包含任何部位
                # k:输入文本，m:icd缓存
                if len(m) >= 4 and self.core_with_same_region(k,v, m[3],ft=False):
                    if m not in icd_list:
                        icd_list.append(m)
                elif len(m) == 3:
                    if m not in icd_list:
                        icd_list.append(m)

            matched = self.get_highest_similarity(k, icd_list, catalog_syns[k], self.ACCURACY)
            res.append([k, matched])

        # rr = []
        # for dis in dis_sentence:
        #     # 没有找到结果的，用es匹配
        #     if dis in diag:
        #         r = match_ICD10_api.es_search(dis,map(self.source_reflection,source_list),self.MATCH_COUNT)
        #         rr.append([dis,map(self.rewrite_search,r)])

        return res

    def source_reflection(self, source):
        return "zd-icd-" + source.lower()

    def es_reflection(self, source):
        return self.source_dic[source[-2:].upper()]

    def rewrite_search(self, res):
        '''
        es搜索到的整理成对应的形式
        :param res_list:
        :return:
        '''
        return [res["_source"]["icd"], res["_source"]["code"], res["_score"], self.es_reflection(res["_index"])]

    def match_all_code(self, code_list, source_list, size):
        '''
        只输入编码，按编码匹配
        完全一样的，返回；没有完全一样的，返回前3位对应的所有条目
        :param code: [code1,code2...]
        :return: list，[icd,code] [[icd1,code1],[icd2,code2]...]
        '''
        return match_ICD10_api.match_all_code(self.icd_list, code_list, source_list, 3, size)

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

    def get_same_region(self, term, source_list):
        '''
        按部位匹配
        :param term:
        :param source_list:
        :return:
        '''
        icd_region_file = {}
        for s in source_list:
            tmp = deepcopy(self.icd_list[s]["region"])
            icd_region_file = self.add_icd_items(icd_region_file, tmp)

        icds = self.get_matched_icds(term, icd_region_file)
        return icds

    def get_same_core(self, term, source_list):
        '''
        按中心词匹配
        :param term:
        :param source_list:
        :return:
        '''
        icd_core_file = {}
        for s in source_list:
            tmp = deepcopy(self.icd_list[s]["core"])
            icd_core_file = self.add_icd_items(icd_core_file, tmp)

        icds = self.get_matched_icds(term, icd_core_file)

        return icds

    def get_matched_icds(self, terms, icd_file):
        '''

        :param dis_sentence:
        :param type:
        :param icd_file:
        :param icd_file2:
        :return:
        '''
        icd_list = []
        for term in terms:  # 要匹配的关键字
            if term in icd_file:
                icd_list.extend(icd_file[term])

        return icd_list

    def get_syn_items(self, source_list):
        '''
        按特征词匹配
        :param dis_sentence:
        :return:
        '''
        icd_type_file = {}
        for s in source_list:
            icd_type_file = self.add_icd_items(icd_type_file, self.icd_list[s]["type"])
        return icd_type_file

    def add_custom_syn_terms(self, item):
        '''
        自定义同义词规则
        :param items:
        :return:
        '''
        for p in ["左侧", "右侧", "双侧", "左", "右", "前", "后", "双", "上", "下", "部", "内"]:
            item = item.replace(p, "")
        for i in ["病", "症", "征","炎"]:
            item = item.replace(i, "")
        if "恶性肿瘤" in item:
            item = item.replace("恶性肿瘤", "癌")
        elif "癌" in item:
            item = item.replace("癌", "恶性肿瘤")

        return item

    def core_with_same_region(self, catalog,regions, icd, ft=False):
        '''
        判断icd的部位是否在输入的文本中出现
        :param catalog:输入编目
        :param regions:输入编目的部位，数组
        :param icd:匹配的icd的部位，数组
        :param ft:是否使用ft识别部位的相似度
        :return:
        '''

        # 不包含部位（只有中心词）,可以
        if not icd:
            return True

        icd_copy=deepcopy(icd)
        # special这些不是特指的部位，如胸部皮肤，腹部皮肤，不能以这些为判定标准
        # 如果icd只包含特指部位，可以
        # 否则要去掉这些，比较剩余部位是否相似
        for special in ["皮肤","关节","组织","肌肉","肌","动脉","静脉","运动","精神"]:
            if special in icd_copy:
                icd_copy.remove(special)
        if icd_copy:
            icd=icd_copy
        for i in icd:
            if i in catalog:
                return True
            if ft:
                for r in regions:
                    if utils.compare_word_similarity(i,r)>0.5:
                        return True
        return False

    def add_syn_terms(self, diagnose, term, icd_list, icd_file, icd_file2=[]):
        '''
        根据同义词词典，将诊断的同义词添加到同义词组中
        :param term:
        :return:
        '''

        def syn_replace(old_term, new_term):
            # 原文中同义词替换
            return diagnose.replace(old_term, new_term)

        term_list = []

        if term in self.syn_dict.keys():
            term_list.extend(map(syn_replace, [term] * len(self.syn_dict[term]), self.syn_dict[term]))

            # syn_term分词，
            segs = requests.post(utils.SERVICE_URL_ZD, data=json.dumps({"diag": self.syn_dict[term]}),
                                 headers=utils.HEADERS).content.decode('utf8')
            segs = eval(segs)
            tags_region, tags_core = [], []
            for s in segs:
                if "部位" in s.keys():
                    tags_region.extend(s["部位"])
                elif "中心词" in s.keys():
                    tags_core.extend(s["中心词"])

            if tags_region:
                for t in tags_region:
                    icd_list.extend(icd_file[t] if t in icd_file else [])
            elif tags_core:
                for t in tags_core:
                    if t in icd_file2:
                        for i_regions in icd_file2[t]:
                            icd_list.append(i_regions)
        return icd_list, term_list

    def get_highest_similarity(self, catalog, icd_list, syn_term_list, threshold):
        '''
        相似度计算
        :param catalog: 编目名称
        :param icd_list: 可能匹配的icd列表
        :param syn_term_list:输入编目的同义词替换，如"左侧肺动脉栓塞"=>[左侧肺栓塞，左侧肺血栓栓塞]
        :param threshold: 相似度阈值
        :return:[["肾损害","M34",42],["硬皮病肾损害","N28",38]...]
        '''

        targets = dict()  # 所有符合的icd:ratio
        # 去掉诊断中的数字，特殊字符
        catalog_rep = match_ICD10_api.remove_digits_with_serial(catalog)
        catalog_rep = match_ICD10_api.remove_para(match_ICD10_api.replace_digits(catalog_rep, self.digits_dic))
        pattern = re.compile("\d+")
        catalog_digits = re.findall(pattern, catalog_rep)

        icd_list = list(icd_list)

        # icd_list.sort(key=lambda x: len(x))

        def build(icds):
            icd = icds[0]
            icd_rep = match_ICD10_api.remove_para(match_ICD10_api.replace_digits(icd))

            # 如果icd/dis中有数字,如icd=第1肋骨骨折,dis=第2,3肋骨骨折,不对
            flag = True
            icd_digits = re.findall(pattern, icd_rep)
            if len(icd_digits) > 0:
                # icd的数字要都在dis中出现
                for digit in icd_digits:
                    if digit not in catalog_digits:
                        flag = False
            # icd在dis中,icd长度<=dis
            if flag:
                types = ["0_core_term", "1_region_term", "2_type_term", "3_judge_term", "4_connect_term",
                         "5_others_term", "dummy_term"]
                # 使用partio_ratio?先排序？
                if len(icd) <= len(catalog) and match_ICD10_api.icd_part_in_dis(self.icd_list, catalog, icd, icds[2], types):
                    # 类似2型糖尿病和糖尿病2型,字相同,顺序不同,一定是最匹配的(此时完全一样的已经去掉)
                    # 排序相同，避免icd_part_in_dis中未知词造成的干扰（此处不包括未知的匹配，只判断主要成分）
                    # 如药物性皮炎&染发性皮炎，染发性是未知，这样的一组词就进入了这里，实际不相似
                    if sorted(catalog) == sorted(icd):
                        targets[icd + " " + icds[2]] = [icds[1], 105, icds[2]]
                    # 其他情况,icd所有词都在dis中,相似度+5
                    # 计算2个相似度,去掉括号内内容和不去掉的
                    else:
                        new_ratio = max(fuzz.ratio(match_ICD10_api.remove_content_in_para(catalog), icd_rep),
                                        fuzz.ratio(catalog_rep, icd_rep))
                        if new_ratio >= threshold:
                            targets[icd + " " + icds[2]] = [icds[1], new_ratio + 15, icds[2]]

                else:
                    ratio = fuzz.ratio(catalog_rep, icd_rep)
                    if syn_term_list:
                        ratio = max(ratio, max(fuzz.ratio(x, icd_rep) for x in syn_term_list))
                    # 相似度不高,但是dis包含了icd,可以考虑
                    if ratio > threshold:
                        targets[icd + " " + icds[2]] = [icds[1], ratio, icds[2]]

        map(build, icd_list)

        results = []
        count = 0
        # 符合的icd由相似度最高到最低,返回最匹配的
        targets_sorted = sorted(targets.keys(), key=lambda d: targets[d][1], reverse=True)
        for t in targets_sorted:
            count += 1
            results.append([t[:t.rindex(" ")], targets[t][0], targets[t][1], targets[t][2]])
            if count == self.MATCH_COUNT:
                break

        return results


m_icd = MatchingICD()


# 按icd查找
def icd_service(data, source_list, size=MATCH_COUNT, is_enable_ft=False, ):
    '''

    :param data: json格式的诊断，{diag:[]}
    :param is_enable_ft:是否使用fasttext猜词
    :return:
    '''

    res = m_icd.matched_dis(data, source_list, size)
    for k in res:
        print k[0]
        for icd in k[1]:
            print icd[0], icd[1], icd[2], icd[3]
        print "-----"

    return res


# 按icd和code查找（icd可以为空）
def icd_code_service(data, source_list, size=MATCH_COUNT):
    if isinstance(data, dict):
        res = m_icd.matched_dis_icd(data, source_list, size)
    else:
        r = m_icd.match_all_code(data, source_list, size)
        res = {}
        for i in range(len(data)):
            res[data[i]] = r[i]
    # for k, v in res.iteritems():
    #     print k
    #     for icd in v:
    #         print icd[0], icd[1], icd[-1]
    #     print "-----"
    return res


# icd_service(["左侧胁肋部疼痛"], ["LC"], size=5)
# icd_code_service(["R23.1","R24"], ["BJ","GB","LC"])

'''
icd部位提取，用分词结果
如 肩关节=>肩&关节&肩关节，如果输入的是踝关节，关节对上了，这样不对
其中分词属于**前/后/左/右/上/下/部，把后面的词去掉
icd的部位如果带有左右，对不上，那不行


修改：
部位/中心词的部位都用分词结果
遍历所有部位，提取出a in b的组合（如 踝关节&关节），制定"同义词"
可以添加其他"同义词"，如手=四肢
判断部位是否相同时，如果中心词的部位都不在输入的文本里，使用同义词

icd tmp记录具体的小类，如 踝关节->踝关节，分词是什么就用什么
输入的使用同义词，如 踝关节->踝关节&关节，以后添加细节，可以 手=四肢
匹配可以 踝关节肿胀->关节肿胀，但是不能 关节肿胀->踝关节肿胀

特征词添加模型比较相似度
'''
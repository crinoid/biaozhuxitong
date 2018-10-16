# encoding=utf8
import re
from utils import SEG_SPLIT
from collections import OrderedDict
import pymongo
from pymongo import MongoClient

import copy

import sys
class Sug4Category(object):
    suffix_words = u'症$|后$|型$|期$|史$|程$|级$|性$|区$|周$|天$'

    def __init__(self, word_category_path):
        self.word_category = {w: c for w, c in self.load_word_category(word_category_path)}

    def load_word_category(self, word_category_path):
        if isinstance(word_category_path, str):
            with open(word_category_path, 'r') as f:
                for l in f.readlines():
                    yield (l.split('\t')[0].decode('utf8'), l.split('\t')[1].strip().decode('utf8'))
        elif isinstance(word_category_path, pymongo.cursor.Cursor):
            for line in word_category_path:
                seg, sug = line["seg"], line["sug"]
                # for seg, sug in line.iteritems():
                #     if seg != "_id" and seg != "state" and seg != "source" and seg != "count":
                if isinstance(seg, str):
                    seg = seg.decode("utf8")
                    sug = sug.decode("utf8")
                yield (seg.upper(), sug.upper())

    def sug_by_dict(self, word):
        return self.word_category.get(word, None)

    def sug_by_dict_strip_suffix(self, word):
        return self.word_category.get(re.sub(self.suffix_words, "", word), None)

    def sug(self, sentence, sep=SEG_SPLIT):
        for word in sentence.strip().split(sep):
            word_upper = word.upper()
            if isinstance(word, str):
                word_upper = word.decode('utf8')
            category = self.sug_by_dict(word_upper) or self.sug_by_dict_strip_suffix(word_upper)
            yield (word, category)


def update_suggestion():  # data:cursor数据库
    conn = MongoClient('localhost', 27017)
    db = conn.bzxt
    data = db.zd_suggest.find({"state": "已存"})  # cursor数据库
    data2 = copy.deepcopy(data)

    try:
        suggestion = Sug4Category(data2)
        return suggestion
    except Exception,e:
        return e.message


# 所有分词-标注
def get_sug_dic():
    global sug_dic
    return sug_dic  # dic:{分词:标注}


# 系统所用标注服务
def sug_sentence(sentences,suggestion):
    # {高血压2级:高血压/2级,肋骨骨折:肋骨/骨折}
    # 用数组避免key有重复(分词有重复)
    try:
        result_dic = {}
        sug_list = []  # [高血压/2级,糖尿病,肋骨/骨折...]
        for msg, sentence in sentences.iteritems():
            msg_dic = {}
            for item in suggestion.sug(sentence):
                # print item[0], item[1]
                if item[1] == None:  # 不在词库中
                    sug_list.append([item[0], ""])
                else:
                    sug_list.append([item[0], item[1]])
            msg_dic[msg] = sug_list
        result_dic["sug"] = msg_dic
        return result_dic  # {高血压2级:[[高血压,中心词],[2级,分型]],肋骨骨折:[...]}
    except Exception,e:
        return e.message


# 分词-标注一体的服务
def sugss(items,suggestion,is_xml=False,is_encode=False):
    '''

    :param items: {diag: [高血压2级, [高血压, 2级]}]}
    :param suggestion:
    :return: [原文:高血压2级，中心词:[高血压]，特征词:[2级]]
    '''
    # {key:{高血压2级:[高血压,2级]}}}
    # items:
    result_dic = []
    try:
        xml_text=""
        for item in items["diag"]:
            if is_encode:
                sug_dic = {}
                sug_dic['原文'] = item[0]
                for sugs in suggestion.sug(";".join(item[1])):
                    value = sugs[0]
                    if sugs[1] == None:  # 不在词库中
                        key = "未知"
                    else:
                        key = sugs[1].encode('utf8')
                    if key not in sug_dic.keys():
                        sug_dic[key] = []
                    sug_dic[key].append(value)
                result_dic.append(sug_dic)

                return result_dic



            sug_dic = {}
            # 写个转unicode的方法
            if type(item[0]) == str:
                item[0] = item[0].decode('utf8')
            sug_dic[u'原文'] = item[0]
            for sugs in suggestion.sug(";".join(item[1])):
                value = sugs[0]
                if type(value)==str:
                    value=value.decode('utf8')
                if sugs[1] == None:  # 不在词库中
                    key = u"未知"
                else:
                    key = sugs[1]
                if key not in sug_dic.keys():
                    sug_dic[key] = []
                sug_dic[key].append(value)
            result_dic.append(sug_dic)


            reflection={
                # "原文":"source",
                u"部位":"region",
                u"中心词":"core",
                u"特征词": "feature",
                u"判断词": "judgement",
                u"连接词": "connection",
                u"病因": "pathogeny",
                u"病理": "pathology",
                u"药品": "medicine",
                u"其他": "others",
                u"未知": "unknown",
            }
            if is_xml:
                # 不要用unicode，用str(ascii)
                xml_text="<source>"+sug_dic[u"原文"]
                for sug,terms in sug_dic.iteritems():
                    if sug!=u"原文":
                        sug = reflection[sug]
                        for term in terms:
                            xml_text+="<"+sug+">"+term
                        xml_text+="<"+sug+"/>"
                xml_text+="</source>"
        if is_xml:
            return xml_text


    except Exception,e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        f = open("error.txt","w")
        f.write(e.message)
        f.write(str(exc_tb.tb_lineno))
        return str(exc_tb.tb_lineno)
    return result_dic

# 判断分词-标注是否已存在
def check_sug(data):
    if isinstance(data, unicode):
        data = data.encode('utf8')
    seg, sug = data.split(",")
    if seg not in sug_dic:
        return False
    else:
        return sug in sug_dic[seg]


# encoding=utf8
import re
from utils import SEG_SPLIT
from collections import OrderedDict
import pymongo
from pymongo import MongoClient

import copy


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
def sugss(items,suggestion):
    # {key:{高血压2级:[高血压,2级]}}}
    result_dic = {}
    sentence_dic = {}
    sug_dic = OrderedDict()

    def build(sentence):
        segs=sentences[sentence]
        sug_dic = OrderedDict()
        # map(build2,segs)
        sug_dic['原文'] = sentence
        for seg in segs:
            for sugs in suggestion.sug(seg):
                value = sugs[0]
                if sugs[1] == None:  # 不在词库中
                    key = "未知"
                else:
                    if type(sugs[1])==unicode:
                        key = sugs[1].encode('utf8')
                    else:
                        key = sugs[1]
                if key not in sug_dic.keys():
                    sug_dic[key] = []
                sug_dic[key].append(value)
        s_list.append(sug_dic)

    def build2(seg):
        map(build3,suggestion.sug(seg))

    def build3(sugs):
        global sug_dic
        value = sugs[0]
        if sugs[1] == None:  # 不在词库中
            key = "未知"
        else:
            key = sugs[1]
        if key not in sug_dic.keys():
            sug_dic[key] = []
        sug_dic[key].append(value)


    for k, sentences in items.iteritems():
        s_list = []
        map(build,sentences.keys())
        # for sentence, segs in sentences.iteritems():
        #     sug_dic = OrderedDict()
        #     sug_dic[u'原文'] = sentence
        #     for seg in segs:
        #         for sugs in suggestion.sug(seg):
        #             value = sugs[0]
        #             if sugs[1] == None:  # 不在词库中
        #                 key = u"未知"
        #             else:
        #                 key = sugs[1]
        #             if key not in sug_dic.keys():
        #                 sug_dic[key] = []
        #             sug_dic[key].append(value)
        #     s_list.append(sug_dic)
        result_dic[k] = s_list
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


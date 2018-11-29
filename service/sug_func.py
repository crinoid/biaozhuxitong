# encoding=utf8
import re
from utils import SEG_SPLIT,auto_match
from collections import OrderedDict
import pymongo
from pymongo import MongoClient

import copy
import sys

conn = MongoClient('localhost', 27017)
db = conn.bzxt

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
        # 这个先不使用，就是以suffix结尾的词如果是未知，就使用去掉suffix word的词作为标注结果
        return self.word_category.get(re.sub(self.suffix_words, "", word), None)

    def sug(self, sentence, database,is_auto_match,sep=SEG_SPLIT):
        for word in sentence.strip().split(sep):
            # word_upper = word.upper() #大小写过后再说
            word_utf8 = word
            if isinstance(word, str):
                word_utf8 = word.decode('utf8')
            if isinstance(word, unicode):
                word = word.encode('utf8')
            category = self.sug_by_dict(word_utf8)
            if is_auto_match and category == None:
                category = auto_match(word, database)

            # 不建议去掉前缀查找中心词
            # category = self.sug_by_dict(word_upper) or self.sug_by_dict_strip_suffix(word_upper)
            yield (word, category)


def update_suggestion(data):  # data:cursor数据库
    conn = MongoClient('localhost', 27017)
    db = conn.bzxt
    if data=="zhenduan":
        data_zd = db.zd_suggest.find({"state": "已存"})  # cursor数据库
        data_new = copy.deepcopy(data_zd)
    elif data=="zhenduan_sm":
        data_zd = db.zd_suggest.find({"state": "已存"})  # cursor数据库
        data_new = copy.deepcopy(data_zd)
    elif data=="shoushu":
        data_ss = db.ss_suggest.find({"state": "已存"})  # cursor数据库
        data_new = copy.deepcopy(data_ss)

    try:
        suggestion = Sug4Category(data_new)
        return suggestion
    except Exception,e:
        return e.message


# 所有分词-标注
def get_sug_dic():
    global sug_dic
    return sug_dic  # dic:{分词:标注}


# 系统所用标注服务
def sug_sentence(sentences,suggestion,database,is_auto_match):
    # {高血压2级:高血压/2级,肋骨骨折:肋骨/骨折}
    # 用数组避免key有重复(分词有重复)
    try:
        result_dic = {}
        msg_dic = []
        # [高血压/2级,糖尿病,肋骨/骨折...]
        for item in sentences: #["扩张性心脏病",["扩张性","心脏病"]]
            if type(item[0])==unicode:
                item[0]=item[0].encode('utf8')
            sug_list = []
            for sugs in suggestion.sug(";".join(item[1]),is_auto_match=is_auto_match,database=database):
                # print item[0], item[1]
                if sugs[1] == None:  # 不在词库中
                    sug_list.append([sugs[0], ""])
                else:
                    sug_list.append([sugs[0], sugs[1].encode('utf8')])
            msg_dic.append([item[0],sug_list])
        # result_dic["sug"] = msg_dic
        return msg_dic  # {高血压2级:[[高血压,中心词],[2级,分型]],肋骨骨折:[...]}
    except Exception,e:
        return e.message


# 分词-标注一体的服务
def sugss(items,suggestion,database,is_auto_match=False):
    '''

    :param items: [[高血压2级, [高血压, 2级]}],[]]
    :param suggestion:
    :param is_auto_match:是否使用fasttext猜测未知词
    :return: [原文:高血压2级，中心词:[高血压]，特征词:[2级]]
    '''
    # {key:{高血压2级:[高血压,2级]}}}
    # items:
    result_dic = []
    try:
        for item in items:
            sug_dic = {}
            # 写个转unicode的方法
            if type(item[0]) == str:
                item[0] = item[0].decode('utf8')
            sug_dic[u'原文'] = item[0]
            for sugs in suggestion.sug(";".join(item[1]),database,is_auto_match):
                value = sugs[0]
                if type(value)==str:
                    value=value.decode('utf8')
                if sugs[1] == None:  # 不在词库中
                    # if is_auto_match:
                    #     key=auto_match(value,database)
                    # else:
                    key = u"未知"
                else:
                    key = sugs[1]
                if key not in sug_dic.keys():
                    sug_dic[key] = []
                sug_dic[key].append(value)
            result_dic.append(sug_dic)

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


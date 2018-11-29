# encoding=utf8

import jieba
import pymongo
import re

from utils import JiebaTuning as JT
from utils import PreClean as Clean
from utils import numerical_type
from utils import combiner as func_combiner
from utils import re_INTEGER

from pymongo import MongoClient
import copy

replace_punctuation = Clean.replace_punctuation
replace_negative_positive = Clean.replace_negative_positive
rm_digits_dis = Clean.rm_dis_digits


class SegSingleSentence(object):
    def __init__(self, usr_dict_path, usr_suggest_path, stop_words_path,dict_origin_path,usr_delete_path,  HMM=False, SUFFIX=True):
        self.__tuning_jieba(usr_suggest_path,dict_origin_path,usr_delete_path,usr_dict_path)
        self.stop_words = set(w for w in self.loading_stop_words(stop_words_path)) if stop_words_path else None
        self.HMM = HMM
        self.clean_pipe = self.build_clean_pipe()
        self.seg_pipe = self.build_seg_pipe(SUFFIX)

    def build_seg_pipe(self, suffix):
        if suffix:
            return func_combiner(
                reversed([self.clean, self.word_seg, self.conn_time_word, self.conn_suffix_word]))
        else:
            return func_combiner(reversed([self.clean, self.word_seg, self.conn_time_word]))

    def build_clean_pipe(self):
        return func_combiner([replace_negative_positive, replace_punctuation, rm_digits_dis])

    @classmethod
    def __tuning_jieba(cls, usr_suggest_path,dict_origin_path,usr_delete_path,usr_dict_path):
        #按这个顺序
        if usr_suggest_path:
            if isinstance(usr_suggest_path, str):
                JT.suggest_usr_dict(usr_suggest_path, sep='\t')
            elif isinstance(usr_suggest_path, list):
                for usp in usr_suggest_path:
                    JT.suggest_usr_dict(usp, sep='\t')
            else:
                raise TypeError('usr_suggest_path %s wrong type' % usr_suggest_path)
        if usr_delete_path:
            # 主要是去掉"性肺炎，性肝炎"
            JT.delete_usr_dict(usr_delete_path)
        if usr_dict_path:
            # 添加词库中的词
            if isinstance(usr_dict_path, str):
                JT.add_usr_dict(usr_dict_path, sep='\t')
            elif isinstance(usr_dict_path, list):
                for udp in usr_dict_path:
                    JT.add_usr_dict(udp, sep='\t')
            elif isinstance(usr_dict_path, pymongo.cursor.Cursor):
                JT.add_usr_db(usr_dict_path)
            else:
                raise TypeError('usr_dict_path %s wrong type' % usr_dict_path)
        if dict_origin_path:
            # 重写词库原有的词，以免修改freq造成分词不准
            JT.add_origin_dict(dict_origin_path)

    def loading_stop_words(self, path):
        stop_words = []
        with open(path, 'rb') as f:
            stop_words.extend([l.strip() for l in f.readlines()])
        stop_words.append(" ")
        for l in stop_words:
            yield l.decode('utf-8')

    def clean(self, content):
        if isinstance(content, numerical_type):
            return str(numerical_type).decode('utf8')
        return self.clean_pipe(content.decode('utf8'))

    def word_seg(self, sentence):
        if self.stop_words:
            return filter(self.word_seg_filter, [k for k in jieba.cut(sentence, HMM=self.HMM)])
        else:
            return [k for k in jieba.cut(sentence, HMM=self.HMM)]

    def word_seg_filter(self, term):
        if term in self.stop_words:
            return False
        return True

    suffix_words = (
        u'病', u'症', u'后', u'型', u'期', u'史', u'程', u'级',
        u'性', u'区', u'周', u'天', u'方案', u'分', u'度'
    )

    time_words = (
        u'余年', u'年余',
        u'余月', u'月余', u'个月',
        u'余周', u'周余',
        u'余天', u'天余',
        u'余日', u'日余',
        u'年前', u'月前', u'天前', u'余前',
        u'小时', u'分钟', u'分', u'次',
        u'年', u'周', u'天', u'月', u'日'
    )

    unit_words = (
        u"%", u"℃", u"cm"
    )

    def conn_suffix_word(self, sentence):
        ret = []
        for i, c in enumerate(sentence):
            if c in self.suffix_words and i > 0:
                ret[-1] += c
            else:
                ret.append(c)

        return ret

    def conn_time_word(self, sentence):
        # conn = []
        i = 0
        # while i < len(sentence):
        #     tmp = sentence[i]
        #     cur_tmp = tmp
        #     if i + 1 < len(sentence):
        #         j = i + 1
        #
        #         tmp += sentence[j]
        #         while tmp in self.time_words and j < len(sentence):
        #             cur_tmp = tmp
        #             j += 1
        #             tmp += sentence[j]
        #         i = j
        #     else:
        #         i += 1
        #     conn.append(cur_tmp)
        #
        ret = []
        for i, c in enumerate(sentence):
            if c in self.time_words and i > 0:
                ret[-1] += c
            # elif i > 0 and c == u"前" or c == u"后" and re_INTEGER.match(ret[-1]):
            #     ret[-1] += c
            else:
                ret.append(c)

        # while i < len(sentence):
        #     if i>0 and sentence[i] in self.time_words and re_INTEGER.match(ret[-1]):
        #         if i + 1 < len(sentence) and sentence[i + 1] in self.time_words:
        #             ret[-1] += sentence[i]
        #             ret[-1] += sentence[i + 1]
        #             i += 1
        #         else:
        #             ret[-1] += sentence[i]
        #     elif i>0 and sentence[i]==u"前" or sentence[i]==u"后" and re_INTEGER.match(ret[-1]):
        #         ret[-1] += sentence[i]
        #     else:
        #         ret.append(sentence[i])
        #     i += 1

        return ret

    def conn_unit_word(self, sentence):
        ret = []
        for i, c in enumerate(sentence):
            if c in self.unit_words and i > 0:
                ret[-1] += c
            else:
                ret.append(c)

        return ret

    def seg(self, sentence):
        return self.seg_pipe(sentence)


def update_segment():
    conn = MongoClient('localhost', 27017)
    db = conn.bzxt
    data = db.zd_suggest.find({"state": "已存"})
    data2 = copy.deepcopy(data)

    path = 'data/'

    segment = SegSingleSentence(data2,"", "", path + 'stop_words_zhenduan.csv')
    return segment


# 所有分词-标注
def get_seg_dic():
    global seg_dic
    return seg_dic  # dic:{分词:标注}


def seg_sentence(sentences, segment, seg_para=True):
    '''

    :param sentences:
    :param seg_para:
    :return: {"diag":[(高血压2级,[高血压，2级]),(肋骨骨折,[肋骨，骨折])]}
    '''
    # output_dic = {}
    result_dic = []  # 一个类别下的分词

    for sentence in sentences:  # [高血压2级,多根肋骨骨折...]
        if isinstance(sentence, unicode):
            sentence = sentence.encode("utf8")
        post_sentence = sentence
        if not seg_para:
            # 去掉括号的内容
            post_sentence = re.sub("\(.*?\)", "", post_sentence)
        result = []
        segs = segment.seg(post_sentence)
        r = map(upper_lower, [sentence] * len(segs), segs)
        result.extend(r)
        result_dic.append([sentence, result])  # 高血压2级:[高血压,2级]

    # output_dic["diag"] = result_dic  # 诊断:{高血压2级:[高血压,2级],多根肋骨骨折:[多根,肋骨骨折]}

    return result_dic

def upper_lower(origin, seg):
    seg = seg.encode('utf8')
    start_idx = origin.upper().find(seg.upper())
    end_idx = start_idx + len(seg)
    return origin[start_idx:end_idx]


# 判断分词是否已存在(用于新增分词写入数据库,若已存在,不写入)
def check_seg(seg):
    # 用str格式
    if isinstance(seg["data"], unicode):
        seg["data"] = seg["data"].encode('utf8')

    flag = seg["data"].strip() in seg_dic
    return flag

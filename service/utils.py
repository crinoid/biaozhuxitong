# encoding=utf8

import jieba
import re
import types
import functools
from pyfasttext import FastText

numerical_type = (types.IntType, types.FloatType, types.LongType, types.ComplexType)
CLRF = '\n'
SEG_SPLIT = ';'
re_INTEGER = re.compile('^[-+]?[0-9]+$')

ft_model=FastText()
ft_model.load_model('../model/bcjl_model.bin')
# ft_model=""

class JiebaTuning(object):
    @staticmethod
    def add_usr_dict(path, sep=','):
        with open(path, 'r') as f:
            for l in f.xreadlines():
                items = l.split(sep)
                if len(items) == 3:
                    jieba.add_word(items[0].rstrip().lower(), int(items[1].rstrip()), items[2].rstrip())
                elif len(items) == 2:
                    jieba.add_word(items[0].rstrip().lower(), int(items[1].rstrip()))
                elif len(items) == 1:
                    jieba.add_word(items[0].rstrip().lower())
                else:
                    raise ValueError('too less number of word info \'%s\'' % (l.strip()))

    @staticmethod
    def delete_usr_dict(path):
        with open(path, 'r') as f:
            for l in f.xreadlines():
                jieba.del_word(l.strip())

    @staticmethod
    def add_usr_db(data,freq=100):
        for d in data:
            jieba.add_word(d["seg"],freq=freq)


    @staticmethod
    def suggest_usr_dict(path, sep=','):
        with open(path, 'r') as f:
            for l in f.xreadlines():
                word1, word2 = l.split(sep)[0].rstrip(), l.split(sep)[1].rstrip()
                jieba.suggest_freq((word1, word2), True)

    @staticmethod
    def add_origin_dict(path, sep=' '):
        with open(path, 'r') as f:
            for l in f.xreadlines():
                items = l.split(sep)
                if len(items) == 3:
                    jieba.add_word(items[0].rstrip().lower(), int(items[1].rstrip()), items[2].rstrip())
                else:
                    raise ValueError('too less number of word info \'%s\'' % (l.strip()))


def create_multi_replace_re(replace_dict):
    return re.compile('|'.join(map(re.escape, replace_dict)))


def combiner(flow):
    return functools.reduce(lambda f1, f2: lambda x: f1(f2(x)), flow, lambda x: x)


class PreClean(object):
    ch_eng = {
        u'，': u',', u'、': u',', u'（': u'(',
        u'）': u')', u'。': u'.', u'；': u';',
        u'：': u':', u'“': u'"', u"”": u'"',
        u'－': u'-', u'Ca': u'癌',
        # u' ': u'',
    }
    re_ch_eng = create_multi_replace_re(ch_eng)

    @classmethod
    def replace_punctuation(cls, content):
        return cls.re_ch_eng.sub(lambda m: cls.ch_eng[m.group(0)], content)

    sym_neg_pos = {u'(-)': u'阴性', u'(+)': u'阳性'}
    re_sym_neg_pos = create_multi_replace_re(sym_neg_pos)

    @classmethod
    def replace_negative_positive(cls, content):
        return cls.re_sym_neg_pos.sub(lambda m: cls.sym_neg_pos[m.group(0)], content)

    @classmethod
    def rm_dis_digits(cls, dis):
        return re.sub("\d*[.,]", "", dis)

def auto_match(term,database, size=10):
    '''
    找到跟某个未知的词相关的size个，预测成分
    :param term: 输入的词
    :param database: 数据库
    :param size:
    :return: 成分
    '''
    dic = {u"部位": 0, u"中心词": 0, u"病因": 0, u"病理": 0, u"特征词": 0, u"连接词": 0, u"判断词": 0, u"其他": 0, u"未知": 0}
    similarity = {}
    weight = 2
    i = 0
    if type(term)==unicode:
        term = term.encode('utf8')
    for m in ft_model.nearest_neighbors(term, k=size):
        weight -= 0.2
        try:
            a = database.find_one({"seg":(m[0])})
            dic[a["sug"]] += m[1] + weight
            similarity[str(i)] = [m[0], a["sug"], round(m[1], 4)]
            i += 1
        except:
            # 降低未知的权值，保证如果有识别出的成分，选择那个成分
            dic[u"未知"] += m[1] + weight * 0.001
            similarity[str(i)] = [m[0], u"未知", round(m[1], 4)]
            i += 1

    sug = sorted(dic.items(), key=lambda x: x[1], reverse=True)[0]
    return sug[0]

# coding=utf8

from seg_func import SegSingleSentence
from pymongo import MongoClient
import copy

from seg_func import seg_sentences as seg_sent
from seg_func import seg_sentences_array as seg_sent_arr
from seg_func import update_segment as update_seg
from seg_func import get_seg_dic as get_seg_d


def seg_sentences(sentences):
    return seg_sent(sentences, segment)


def seg_sentences_array(sentences):
    return seg_sent_arr(sentences, segment)


def update_segment():
    global segment
    segment = update_seg()


def get_seg_dic():
    return get_seg_d()


conn = MongoClient('localhost', 27017)
db = conn.bzxt
data = db.ss_suggest.find({"state": "已存"})
data2 = copy.deepcopy(data)

path = 'data/'

segment = SegSingleSentence(usr_dict_path=data2, usr_suggest_path="", stop_words_path=path + 'stop_words_zhenduan.csv',
                            dict_origin_path=path + "dict.txt", usr_delete_path=path + "terms_for_remove.csv")

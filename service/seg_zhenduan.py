#coding=utf8

from seg_func import SegSingleSentence
from pymongo import MongoClient
import copy

from seg_func import seg_sentences as seg_sent
from seg_func import seg_sentences_array as seg_sent_arr
from seg_func import update_segment as update_seg
from seg_func import get_seg_dic as get_seg_d

def seg_sentences(sentences,seg_para=True):
    return seg_sent(sentences,segment,seg_para)

def seg_sentences_array(sentences):
    return seg_sent_arr(sentences,segment)

def update_segment():
    global segment
    segment = update_seg()

def get_seg_dic():
    return get_seg_d()

conn = MongoClient('localhost', 27017)
db = conn.bzxt
data = db.zd_suggest.find({"state": "已存"})
data2 = copy.deepcopy(data)

path = 'seg_service/'

segment = SegSingleSentence(data2, "","",'data/stop_words_zhenduan.csv')


for k,v in seg_sentences([u"addison病"])["diag"].iteritems():
    print k
    for v1 in v:
        print v1

# update_segment()
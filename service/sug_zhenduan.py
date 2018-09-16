#coding=utf8

import copy
from sug_func import Sug4Category
from pymongo import MongoClient

from sug_func import sugss as sugs
from sug_func import sug_sentence as sug_sent
from sug_func import update_suggestion as update_sug
from sug_func import get_sug_dic as get_sug_d

def sugss(sentences):
    return sugs(sentences,suggestion)

def sug_sentence(sentences):
    return sug_sent(sentences,suggestion)

def update_suggestion():
    global suggestion
    suggestion = update_sug()

def get_sug_dic():
    return get_sug_d()

conn = MongoClient('localhost', 27017)
db = conn.bzxt
data = db.zd_suggest.find({"state": "已存"})  # cursor数据库
data2 = copy.deepcopy(data)

sug_dic = {}
for line in data:
    seg, sug = line["seg"], line["sug"]
    sug_dic[seg] = sug

suggestion = Sug4Category(data2)


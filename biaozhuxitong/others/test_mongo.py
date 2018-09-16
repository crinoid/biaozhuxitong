#coding=utf8
from pymongo import MongoClient
import pymongo

headers = {'content-type': 'application/json'}

conn = MongoClient('localhost', 27017)
db = conn.bzxt
suggest = db.zd_suggest

item = suggest.find({"seg":"骨折"})
for line in item:
    print line["seg_source"],line["sug_source"],line["sug"]
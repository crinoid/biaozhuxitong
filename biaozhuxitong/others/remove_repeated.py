# coding=utf8

from pymongo import MongoClient

conn = MongoClient('localhost', 27017)
db = conn.bzxt
zd_segment = db.zd_segment
zd_suggest = db.zd_suggest

ss_segment = db.ss_segment
ss_suggest = db.ss_suggest

ss_seg = set()
for s in ss_segment.find():
    if s["seg"] not in ss_seg:
        ss_seg.add(s["seg"])
    else:
        ss_segment.remove({"_id": s["_id"]})

ss_sug = set()
for s in ss_suggest.find():
    if s["seg"] not in ss_sug:
        ss_sug.add(s["seg"])
    else:
        ss_suggest.remove({"_id": s["_id"]})
# coding=utf8

from pymongo import MongoClient

conn = MongoClient('localhost', 27017)
db = conn.bzxt1
zd_segment = db.zd_segment
zd_suggest = db.zd_suggest
zd_ctg = db.zd_category
ss_segment = db.ss_segment
ss_suggest = db.ss_suggest
ss_ctg = db.ss_category


def remove_data():
    zd_segment.remove()
    zd_suggest.remove()
    zd_ctg.remove()
    ss_segment.remove()
    ss_suggest.remove()
    ss_ctg.remove()


# for line in open("service/seg_service/dict.csv").readlines():
#     seg = line.strip()
#     zd_segment.insert({"seg": seg, "source": "", "state": "已存", "count": 1})

def update_initial_data():
    for line in open("service/data/category.csv").readlines():
        seg, sug = line.strip().split("\t")
        zd_suggest.insert({"seg": seg, "sug": sug, "seg_source": "", "sug_source": "", "state": "已存", "count": 1})


def update_current_data(path, backup_path, table, start=0):
    # 如果有seg表，将seg表中的source插入到sug表中
    dic_seg = get_seg_source(path, "zd_seg_backup.csv", start=1)
    for line in open(path + backup_path).readlines()[start:]:
        line = line.strip()
        splits = split_by_quote(line)
        if len(splits) == 3:
            source = splits[1]
            seg, sug, _ = splits[0].split(",")
            _, state, count = splits[2].split(",")
        else:
            seg, sug, source, state, count = line.strip().split(",")
        if seg in dic_seg:
            source_seg = dic_seg[seg]
            if len(source_seg[0]) > source:
                source = source_seg[0]
                count = source_seg[1]
        table.insert(
            {"seg": seg, "sug": sug, "seg_source": source, "sug_source": source, "state": state, "count": count})


def get_seg_source(path, backup_path, start=0):
    dic_seg = {}
    for line in open(path + backup_path).readlines()[start:]:
        line = line.strip()
        splits = split_by_quote(line)
        if len(splits) == 3:
            source = splits[1]
            seg, _ = splits[0].split(",")
            _, state, count = splits[2].split(",")
        else:
            seg, source, state, count = line.strip().split(",")

        dic_seg[seg] = [source, count]
    return dic_seg


def update_current_ctg(path, ctg_path, table, start=0):
    for line in open(path + ctg_path).readlines()[start:]:
        table.insert({"category": line.strip()})


def split_by_quote(data):
    return data.split("\"")


remove_data()
path = "data/"

# update_current_data(path, "zd_sug_backup.csv", zd_suggest,1)
# update_current_data(path, "ss_sug_backup.csv", ss_suggest,1)
update_initial_data()

# update_current_ctg(path, "zd_ctg_backup.csv", zd_ctg,1)
# update_current_ctg(path, "ss_ctg_backup.csv", ss_ctg,1)

update_current_ctg(path, "distinct_category_zd.dat", zd_ctg)
update_current_ctg(path, "distinct_category_ss.dat", ss_ctg)

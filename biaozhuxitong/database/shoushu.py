# coding=utf8
from base import MongoDatabase

mongo = MongoDatabase()


class ShouShu():
    def __init__(self):
        # 症状诊断
        self.zd_segment = mongo.db.ss_segment  # 分词
        self.zd_suggest = mongo.db.ss_suggest  # 标注
        self.zd_file = mongo.db.ss_file
        self.zd_category = mongo.db.ss_category

    def get_files(self):
        return mongo.get_files(self.zd_file)

    def get_file_by_filecode(self, code):
        return mongo.get_file_by_filecode(self.zd_file, code)

    def insert_file(self, data):
        mongo.insert_file(self.zd_file, data)

    def update_file_checked_seg(self, code, checked_number):
        mongo.update_file_checked_cut(self.zd_file, code, checked_number)

    def update_file_checked_sug(self, code, checked_number):
        mongo.update_file_checked_utility(self.zd_file, code, checked_number)

    def delete_file(self, code):
        mongo.delete_file(self.zd_file, code)

    def get_categories(self):
        return mongo.get_categories(self.zd_category)

    def update_categories(self, category):
        mongo.update_categories(self.zd_category, category)

    def add_categories(self, category):
        mongo.add_categories(self.zd_category, category)

    def delete_category(self, category):
        mongo.delete_category(self.zd_category, category)

    # def get_segments(self):
    #     return mongo.get_segments(self.zd_segment)

    def get_suggests(self):
        return mongo.get_suggests(self.zd_suggest)

    # def get_new_segments(self):
    #     return mongo.get_new_segments(self.zd_segment)

    def get_new_suggests(self):
        return mongo.get_new_suggests(self.zd_suggest)

    # def insert_segments(self, data):
    #     mongo.insert_segments(self.zd_segment, data)
    def is_sug_exist(self,seg,sug):
        return mongo.is_sug_exist(self.zd_suggest,seg,sug)

    def insert_suggests(self, data, cover=False):
        return mongo.insert_suggests(self.zd_suggest, data, cover)

    def update_seg_source(self, seg, sug, origin_msg):
        mongo.update_seg_source(self.zd_segment, seg, sug, origin_msg)

    def update_sug_source(self, seg, sug, origin_msg):
        mongo.update_sug_source(self.zd_suggest, seg, sug, origin_msg)

    # def update_seg_state(self, seg):
    #     mongo.update_seg_state(self.zd_segment, seg)

    def update_sug_state(self, sug):
        return mongo.update_sug_state(self.zd_suggest, sug)

    def update_sug_category(self, dict):
        mongo.update_sug_category(self.zd_suggest, dict)

    def update_single_sug_category(self, dict):
        mongo.update_single_sug_category(self.zd_segment, self.zd_suggest, dict)

    def get_seg_source(self, segs, max):
        return mongo.get_seg_source(self.zd_segment, segs, max)

    def get_sug_source(self, terms, max):
        return mongo.get_sug_source(self.zd_suggest, terms, max)

    # def save_segments(self, seg):
    #     mongo.save_segments(self.zd_segment, seg)
    #
    # def save_suggests(self, seg, sug):
    #     mongo.save_suggests(self.zd_file, seg, sug)

    # def delete_segments(self, segs):
    #     mongo.delete_segments(self.zd_segment, segs)

    def delete_suggests(self, items):
        mongo.delete_suggests(self.zd_suggest, items)

    def delete_items_by_sug(self, items):
        mongo.delete_items_by_sug(self.zd_suggest, items)

    def delete_all(self):
        mongo.delete_all(self.zd_segment, self.zd_suggest, self.zd_file)

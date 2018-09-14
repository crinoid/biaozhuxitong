# coding=utf8
from __future__ import unicode_literals

from pymongo import MongoClient
import multiprocessing
from utils import dbinfo as utils


class MongoDatabase:
    def __init__(self):
        conn = MongoClient('localhost', 27017)
        self.db = conn.bzxt  # 连接mydb数据库，没有则自动创建
        self.my_diag=self.db.diag_files
        self.my_icd = self.db.icd_match
        self.lock = multiprocessing.Lock()

    def get_files(self, my_file):
        return my_file.find().sort(utils.FILE_DATE)

    def get_file_by_filecode(self, my_file, code):
        return my_file.find({utils.FILE_CODE: code})

    def insert_file(self, my_file, data):  # data:dict
        my_file.insert(data)

    def update_file_checked_cut(self, my_file, code, checked_number):
        my_file.update({utils.FILE_CODE: code}, {'$set': {utils.FILE_CHECKED: checked_number}})

    # def update_file_checked_utility(self, my_file, code, checked_number):
    #     my_file.update({utils.FILE_CODE: code}, {'$set': {utils.: checked_number}})

    def delete_file(self, my_file, code):
        my_file.remove({utils.FILE_CODE: code})

    def get_categories(self, my_ctg):
        ctg_list = []
        for c in my_ctg.find():
            ctg_list.append(c[utils.CATEGORY])
        return ctg_list

    # 标注更新:替换之前的保留,如果替换之后的是新增数据,添加上
    def update_categories(self, my_ctg, category):
        # items = my_ctg.find()
        # all_categories = [c['category'] for c in items]
        #
        # for k,v in category.iteritems():
        #     if k not in all_categories:
        #         my_ctg.insert({"category": k})
        #     if v not in all_categories:
        #         my_ctg.insert({"category": v})
        #
        # for c in items:
        #     if c['category'] in category.keys():
        #         if category[c['category']] not in all_categories:
        #             my_ctg.insert({"category": c['category']})

        my_ctg.insert({utils.CATEGORY: category})

    def add_categories(self, my_ctg, category):  # category数组
        for c in category:
            my_ctg.insert({utils.CATEGORY: c})

    def delete_category(self, my_ctg, category):
        my_ctg.remove({utils.CATEGORY: category})

    # 已存数据
    # def get_segments(self, my_seg):
    #     return my_seg.find({utils.SEG_STATE: utils.SAVED}).sort([(utils.SEG_SEG, 1)])

    #根据分词找标注类型
    def get_suggest_from_seg(self,my_sug,seg):
        return my_sug.find({utils.SUG_SEG:seg})

    def get_suggests(self, my_sug):
        return my_sug.find({utils.SUG_STATE: utils.SAVED})

    # 新增数据
    # def get_new_segments(self, my_seg):
    #     return my_seg.find({utils.SEG_STATE: utils.UNSAVED}).sort([(utils.SEG_COUNT, -1)])

    def get_new_suggests(self, my_sug):
        return my_sug.find({utils.SUG_STATE: utils.UNSAVED}).sort([(utils.SUG_COUNT, -1)])

    # 插入分词的时候要判断分词是否已存在
    # def insert_segments(self, my_seg, data):
    #     if data[utils.SEG_STATE] == utils.SAVED:
    #         target = my_seg.find_one({utils.SEG_STATE: data[utils.SEG_STATE]})
    #         if target:
    #             return ""
    #     my_seg.insert(data)

    # 插入标注要判断分词是否已存在,分词-标注是否已存在
    def insert_suggests(self, my_sug, data, cover=False):
        '''

        :param my_sug: 数据库表
        :param data: 一组分词-标注数据
        :param cover: 存在相同的分词，是否覆盖数据
        :return:
        '''
        if data[utils.SUG_STATE] == utils.SAVED:
            target = my_sug.find_one({utils.SUG_SEG: data[utils.SUG_SEG]})
            if target:
                # 存在相同的分词,但是标注不同
                # 此时前台提示是否覆盖
                # 注意unicode，data--str,target--unicode
                if isinstance(data[utils.SUG_SUG],str):
                    target[utils.SUG_SUG] = target[utils.SUG_SUG].encode('utf8')
                if target[utils.SUG_SUG] != data[utils.SUG_SUG]:
                    # my_sug.remove({"_id": target["_id"]})
                    # 插入的分词在数据库存在，但是标注不同，判断是否覆盖
                    if not cover:
                        return target
                    else: #替换数据
                        my_sug.update({utils.SUG_SEG: data[utils.SUG_SEG]},
                              {'$set': {utils.SUG_SUG:data[utils.SUG_SUG]}})
                else:  # 插入的标注在数据库中存在，不做操作
                    return ""
            my_sug.insert(data)
        return ""

    # 添加分词,更新source和count
    def update_seg_source(self, my_sug, seg, sug, origin_msg):
        with self.lock:
            self.update_source(my_sug, seg, sug, origin_msg, utils.SEG_SOURCE)

    def update_sug_source(self, my_sug, seg, sug, origin_msg):
        # if isinstance(seg, str):
        #     seg = seg.decode('utf8')
        #     sug = sug.decode('utf8')
        with self.lock:
            self.update_source(my_sug, seg, sug, origin_msg, utils.SUG_SOURCE)

    def update_source(self, my_sug, seg, sug, origin_msg, updates):
        '''

        :param my_sug:
        :param seg: 分词
        :param sug: 标注
        :param origin_msg: 数据来源
        :param updates: 要更新的字段--seg_source或sug_source
        :return:
        '''
        # 已有分词，不同标注,删除原有的，更新标注
        # if my_sug.count({utils.SUG_SEG: seg}) > 1:
        #     my_sug.remove({utils.SUG_SEG: seg, utils.SUG_STATE: utils.SAVED})
        #     my_sug.update({utils.SUG_SEG: seg, utils.SUG_SUG: sug},
        #                   {'$set': {updates: origin_msg, utils.SUG_STATE: utils.SAVED, utils.SUG_COUNT: 1}})
        target = my_sug.find_one({utils.SUG_SEG: seg, utils.SUG_SUG: sug})
        if target:
            cur_count = int(target[utils.SUG_COUNT]) + 1
            source = target[utils.SUG_SOURCE].split(",")
            if origin_msg not in source:
                source.insert(0, origin_msg)  # 新的来源添加到最前面
            if seg:
                my_sug.update({utils.SUG_SEG: seg, utils.SUG_SUG: sug},
                              {'$set': {utils.SEG_SOURCE: ",".join(source), utils.SUG_SOURCE: ",".join(source),
                                        utils.SUG_COUNT: cur_count}})
        # 新增数据，state=新增
        else:
            my_sug.insert(
                {utils.SUG_SEG: seg, utils.SUG_SUG: sug, utils.SEG_SOURCE: origin_msg, utils.SUG_SOURCE: origin_msg,
                 utils.SUG_STATE: utils.UNSAVED,
                 utils.SUG_COUNT: 1})

    def update_seg_state(self, my_seg, segs):
        if isinstance(segs, list):
            for s in segs:
                my_seg.update({utils.SEG_SEG: s}, {'$set': {utils.SEG_STATE: utils.SAVED}})
        else:
            for s in segs.split(","):
                my_seg.update({utils.SEG_SEG: s}, {'$set': {utils.SEG_STATE: utils.SAVED}})

    def update_sug_state(self, my_sug, items, isCover=True):
        if isinstance(items, str) or isinstance(items, unicode):
            for s in items.split(","):
                # print s
                if s:
                    idx = s.rfind("-")  # 最后一个"-"是分隔分词与标注
                    seg, sug = s[:idx], s[idx + 1:len(s)]
                    # 一个分词只能有一个标注,先删除该分词,再添加标注
                    if isCover:
                        my_sug.remove({utils.SUG_SEG: seg, utils.SUG_STATE: utils.SAVED})
                    my_sug.update({utils.SUG_SEG: seg, utils.SUG_SUG: sug}, {'$set': {utils.SUG_STATE: utils.SAVED}})
        else:
            for seg, sug in items:
                # 一个分词只能有一个标注,先删除该分词,再添加标注
                if isCover:
                    my_sug.remove({utils.SUG_SEG: seg, utils.SUG_STATE: utils.SAVED})
                my_sug.update({utils.SUG_SEG: seg, utils.SUG_SUG: sug}, {'$set': {utils.SUG_STATE: utils.SAVED}})

    # 标注重命名后,更新该标注下的分词对应的标注
    def update_sug_category(self, my_sug, dict):
        for old_sug, new_sug in dict.iteritems():
            for item in my_sug.find({utils.SUG_SUG: old_sug}):
                my_sug.update({utils.SUG_SEG: item[utils.SUG_SEG]}, {'$set': {utils.SUG_SUG: new_sug}})

    # 单个分词的标注替换,分词-标注 一对一
    def update_single_sug_category(self, my_seg, my_sug, dict):
        for seg, sug in dict.iteritems():
            if sug == "无" or sug.decode('utf8') == '无':
                my_seg.remove({utils.SEG_SEG: seg})
            else:
                # 分词-标注中已有
                if my_sug.find_one({utils.SUG_SEG: seg}):
                    my_sug.update({utils.SUG_SEG: seg}, {'$set': {utils.SUG_SUG: sug}})
                # 在分词中(不能没出现过)
                else:
                    # print "not exists"
                    # target = my_seg.find_one({"seg": seg})
                    # source, count = target["source"], target["count"]
                    my_sug.insert(
                        {utils.SUG_SEG: seg, utils.SUG_SUG: sug, utils.SUG_SOURCE: "", utils.SUG_STATE: utils.SAVED,
                         utils.SUG_COUNT: 1})

    # 获取分词来源,前max个,max=0表示所有
    def get_seg_source(self, my_sug, seg_list, max=0):
        '''

        :param my_seg:
        :param seg_list:一组分词，二维数组
        :param max:返回的来源个数
        :return: {分词1:{来源1,来源2...},分词2:{...}}
        '''

        j = 0
        dic = {}
        for segs in seg_list:
            source_dic = {}
            for seg in segs:  # [高血压，2级]
                sources = []
                item = my_sug.find_one({utils.SUG_SEG: seg})
                # 有的分词不在词库中,即item有可能是None,此时需要判断
                if item:
                    sources = item[utils.SEG_SOURCE].split(",")
                    max = len(sources) if max == 0 else max
                    sources = sources[:max]
                    for i in range(len(sources)):
                        sources[i] = sources[i].split("/")
                else:
                    sources.append("")
                source_dic[seg] = sources
            dic[j] = source_dic
            j += 1
        return dic

    # 获取标注来源,前max个,max=0表示所有
    def get_sug_source(self, my_sug, term_list, max=0):
        '''

        :param my_sug:
        :param term_list:数组，每个元素是一条文本[{分词1：标注1，分词2：标注2}，{分词3：标注3，分词4：标注4}]
        :param max:返回多少个source
        :return:
        '''

        def split_word(data):
            return data

        dic = {}

        j = 0
        for terms in term_list:
            source_dic = {}
            for seg, sug in terms.iteritems():
                sources = []
                item = my_sug.find_one({utils.SUG_SEG: seg, utils.SUG_SUG: sug})
                # 有的分词不在词库中,即item有可能是None,此时需要判断
                if item:
                    sources = item[utils.SUG_SOURCE].split(",")
                    max = len(sources) if max == 0 else max
                    sources = sources[:max]
                    for i in range(len(sources)):
                        # 去掉split后的空格
                        sources[i] = filter(split_word,sources[i].split("/"))
                else:
                    sources.append("")
                source_dic[seg + "-" + sug] = sources
            dic[j] = source_dic
            j += 1
        return dic

    def delete_segments(self, my_seg, segs):
        if isinstance(segs, list):
            for s in segs:
                my_seg.remove({utils.SEG_SEG: s})
        else:
            for s in segs.split(","):
                my_seg.remove({utils.SEG_SEG: s})

    def delete_suggests(self, my_sug, items):
        '''
        删除一组分词-标注
        :param my_sug:
        :param items: '胶质瘤-中心词，低级别-分型'
        :return:
        '''
        # 从新增数据删除
        my_sug.remove({utils.SUG_SEG: items[utils.SUG_SEG], utils.SUG_SUG: items[utils.SUG_SUG]})

    def delete_items_by_sug(self, my_sug, sug):
        '''
        删除指定标注类型的数据
        :param my_sug:
        :param sug: 某个标注类型
        :return:
        '''
        my_sug.remove({utils.SUG_SUG: sug})

    def delete_all(self, my_seg, my_sug, my_file):
        my_sug.remove()
        my_file.remove()

    def insert_diag_file(self,data):
        '''
        插入诊断文件，用于匹配icd
        :param data:
        :return:
        '''
        self.my_diag.insert(data)

    def get_diag_file(self):
        return self.my_diag.find()

    def get_diag_file_by_code(self,code):
        file = self.my_diag.find_one({"code":code})
        if file:
            return file["file"]
        return ""

    def delete_diag_file(self,code):
        '''
        删除诊断文件
        :param code: 诊断文件随机码
        :return:
        '''
        self.my_diag.remove({"code":code})

    def insert_icd_match(self,data):
        '''
        插入诊断-icd匹配内容,key存在，添加，否则新增
        :param my_icd:
        :param data: {diag:高血压,match:{lc:{高血压:I10},gb:{高原性高血压:T10}}
        :return:
        '''
        diag = data[utils.DIAG]
        target = self.my_icd.find_one({utils.DIAG:diag})
        if target:
            for k,v in data[utils.MATCH].iteritems():
                if k in target[utils.MATCH].keys():
                    target[utils.MATCH][k]=dict(target[utils.MATCH][k],**data[utils.MATCH][k])
            self.my_icd.update({utils.DIAG:diag}, {'$set': {utils.MATCH:target[utils.MATCH]}})
        else:
            self.my_icd.insert(data)

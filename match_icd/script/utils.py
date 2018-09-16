# coding=utf8

import hashlib
import commands
import os

from pymongo import MongoClient
from pyfasttext import FastText


import jieba


SERVICE_URL_SS = "http://127.0.0.1:8001/service"
SERVICE_URL_ZD2 = "http://127.0.0.1:8002/service" #大粒度
SERVICE_URL_ZD = "http://127.0.0.1:8006/service" #小粒度
# SERVICE_URL_SS = "http://172.19.91.91:8001/service"
# SERVICE_URL_ZD = "http://172.19.91.91:8002/service"

HEADERS = {'content-type': 'application/json'}


#bcjl_model:分词粒度大（如 肾积水），bcjl_model1:分词粒度小（如 肾/积水）
ft_model=FastText()
ft_model.load_model('../data/bcjl_model1.bin')


SYN_THRESHOLD=0.75
SIMILARITY_THRESHOLD=0.8

conn = MongoClient('localhost', 27017)
db = conn.bzxt1

def file_compare(f1_path,f2_path):
    # 比较两个文件是否相同
    def get_file_md5(f):
        m = hashlib.md5()
        while True:
            #如果不用二进制打开文件，则需要先编码
            #data = f.read(1024).encode('utf-8')
            data = f.read(1024)  #将文件分块读取
            if not data:
                break
            m.update(data)
        return m.hexdigest()

    if not os.path.exists(f2_path):
        return False

    with open(f1_path,'rb') as f1,open(f2_path,'rb') as f2:
        file1_md5 = get_file_md5(f1)
        file2_md5 = get_file_md5(f2)

        if file1_md5 != file2_md5:
            return False
        else:
            return True

def copy_file(f1_path,f2_path):
    commands.getoutput("cp "+ f1_path + " "+ f2_path)

def get_suggest(term):
    s = db.zd_suggest.find_one({"seg": term})
    if s:
        return s["sug"]
    return ""

def predict_category(term):

    if type(term) == unicode:
        term = term.encode('utf8')
    for m in ft_model.nearest_neighbors(term, k=10):
        # 相近的词需要在词库中，并且成分是部位/中心词
        print m[0], m[1]
        # category=get_suggest(m[0])
        # if category in ["部位","中心词"]:
        #     return category,m
    return "", ["", 0]

def predict_similarity(term1, term2):
    similarity = ft_model.similarity(term1, term2)
    return True if similarity > SIMILARITY_THRESHOLD else False

def get_similarity(term1,term2):
    return ft_model.similarity(term1, term2)

def split_corewords():
    '''
    拆分 部位+中心词 如 肾囊肿=>肾/囊肿
    :return:
    '''
    for line in open("corewords.txt").readlines()[-16:]:
        # print line
        all = db.zd_suggest.find()
        for a in all:
            if len(a["seg"])>2 and line.strip().decode('utf8') in a["seg"]:
                print a["seg"]
                # db.zd_suggest.remove({"seg":a["seg"]})

def split_specific_words():
    all = db.zd_suggest.find()
    for a in all:
        # if len(a["seg"])>5:
        #     print a["seg"]
        if a["sug"]==u"其他":
            print a["seg"]
        # if u"继发" in a["seg"] and len(a["seg"])>3:
        #     print a["seg"]
            # db.zd_suggest.remove({"seg": a["seg"]})

def split_feature_region():
    '''
    拆分特征词+部位，如 双侧肺=>双侧/肺
    :return:
    '''
    # for line in open("featurewords.txt").readlines():
    for line in ["左侧","右侧","两侧"]:
        all = db.zd_suggest.find()
        for a in all:
            if a["seg"]!=line.strip().decode('utf8') and a["seg"].find(line.strip().decode('utf8'))==0:
                print a["seg"]
                db.zd_suggest.remove({"seg":a["seg"]})

def split_feature_core():
    '''
    拆分特征词+中心词，如 慢性肝炎=>慢性/肝炎
    :return:
    '''
    for line in open("featurewords.txt").readlines():
        all = db.zd_suggest.find()
        for a in all:
            if a["seg"].find(line.strip().decode('utf8'))==0 and a["seg"]!=line.strip().decode('utf8'):
                print a["seg"]
                # db.zd_suggest.remove({"seg":a["seg"]})

def get_suggest():
    all = db.zd_suggest.find()
    for a in all:
        if a["sug"]==u"部位":
            print a["seg"]

def update_from_file():
    for line in open("updates.csv").readlines():
        print db.zd_suggest.remove({"seg": line.strip().decode("utf8")})
        # db.zd_suggest.update({"seg":line.strip()},{"$set":{"sug":u"特征词"}})

def get_features():
    all = db.zd_suggest.find()
    for a in all:
        if a["sug"]==u"特征词" and a["seg"][-1] in [u"性",u"型"]:

            print a["seg"]

def seg_cores():
    for i in jieba.cut("肘关节病"):
        print i
    # all = db.zd_suggest.find({"sug":u"中心词"})
    # for a in all:
    #     segs = jieba.cut(a["seg"])
    #     if len(list(segs))>1:
    #         print a["seg"]

def auto_match(term, size):
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

    term = term.encode('utf8')
    for m in ft_model.nearest_neighbors(term, k=size):
        weight -= 0.2
        try:
            # database = ZhenDuan()
            # if dbname == "shoushu":
            #     database = ShouShu()
            a = db.zd_suggest.find_one({"seg":(m[0])})
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

def most_similar_n(term,data_list,t,size,n=1):
    '''
    找出与某个词最相近的n个词，需要在数据库中已知，和类别一样
    :param term:
    :param data_list: 数据库中的词
    :param t: 分词类型
    :param size: 相似的前n个词
    :return:
    '''
    term = term.encode('utf8')

    res=[]
    for m in ft_model.nearest_neighbors(term, k=size):
        if m[0] in data_list:
            target = db.zd_suggest.find_one({"seg": (m[0])})
            if target and target["sug"]==t:
                res.append(m[0])
                if len(res)==n:
                    return res
    return res

# item不能包含exclude里的元素
def is_in(item,exclude):
    for e in exclude:
        if e in item[0]:
            return False
    return True


def add(match_group, icds, term):
    try:
        for item in icds[term]:
            # if is_in(item):
            # match_group[item[0]] = [item[1], item[2]]

            if item[0] in match_group[term].keys() and [item[1], item[2]] in match_group[term][item[0]]:
                pass
            else:
                try:
                    match_group[term][item[0]].append([item[1], item[2]])
                except:
                    match_group[term][item[0]] = [[item[1], item[2]]]
    except:
        pass
    return match_group

# split_corewords()
# get_suggest()
# split_specific_words()
# seg_cores()
# update_from_file()

# icd_service(["急性脑梗死"], ["LC"])
# icd_code_service(["R23","R24"], ["BJ","GB","LC"])

# print db.zd_suggest.find_one({"seg":"阑尾切除术"})

# predict_category("肩胛骨")
# t,r = predict_category("结节")
# print t,r[0],r[1]


# print ft_model.similarity("喉发炎", "麻疹并发喉炎")
# print ft_model.similarity("喉发炎", "急性咽喉炎")
# print ft_model.similarity("升结肠占位", "升结肠良性肿瘤")

# all= db.zd_suggest.find()

# print file_compare("../data/icd/cache/shoushu/BJ_icd_name.csv","../data/icd/tmp/shoushu/BJ_icd_name_shoushu.csv")

# from fuzzywuzzy import fuzz
# print fuzz.token_sort_ratio(u"喉 发 炎",u"麻 疹 并 发 喉 炎",force_ascii=False)
# print fuzz.token_sort_ratio(u"喉 发 炎",u"急 性 咽 喉 炎",force_ascii=False)
# print fuzz.token_set_ratio(u"肝 多 发 囊 肿",u"多 囊 肝 发 啊",force_ascii=False)
# print fuzz.token_sort_ratio(u"肝 多 发 囊 肿",u"多 囊 肝 发 啊",force_ascii=False)
# print fuzz.token_sort_ratio(u"肝 多 发 囊 肿",u"囊 肿 肝 多 发",force_ascii=False)


# print auto_match(u"面骨",5)

# print "pppp"

# db.zd_suggest.remove({"seg":"病率"})

# 给定一个未知词，从词库中找到最相似的
def get_top_similarity(term,term_list):
    res = ft_model.nearest_neighbors(term,10)
    for r in res:
        # if r[0] in term_list:
        print r[0],r[1]

def remove_space(a):
    return a.replace("\n","").decode('utf8')

# term_core=map(remove_space,open("cores.txt").readlines())
# term_region=map(remove_space,open("regions.txt").readlines())
# get_top_similarity("肝曲",term_region)
# get_top_similarity("肺部",term_core)

def to_string(a):
    return str(a)

# f=open("../data/bcjl_model1.vec","aw")
# f.write("夹层 ")
# f.write(" ".join(map(to_string,ft_model.get_numpy_vector("夹层"))))

# print ft_model.get_numpy_vector("无",normalized=True)

# from gensim.models.keyedvectors import KeyedVectors
# zh_vec_model = KeyedVectors.load_word2vec_format('../data/bcjl_model1.vec',binary=False)
# for i in zh_vec_model.most_similar(u"肺部"):
#     print i[0],i[1]

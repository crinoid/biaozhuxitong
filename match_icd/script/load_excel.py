#coding=utf8
from __future__ import unicode_literals

import pandas as pd
from copy import deepcopy

def replace_punc(txt):
    for r in ["；","（","）","：","？","、","。",",",".","(",")",":",";","?"]:
        txt = txt.replace(r,"")
    return txt

# 找出完全一样的诊断
def get_repetitive_diag(txt_list):
    repetitive_list=[]
    # 去掉特殊字符
    clear_list = map(replace_punc,txt_list)
    for txt in clear_list:
        cp_list = deepcopy(clear_list)
        cp_list.remove(txt)
        if txt in cp_list:
            repetitive_list.append(txt)
    return repetitive_list

# 除去错别字完全一样的
def get_mis_diag(txt_list):
    repetitive_list = []
    for i in range(len(txt_list)-1):
        for j in range(i+1,len(txt_list)):
            if len(txt_list[i])==len(txt_list[j]):
                if compare_words(txt_list[i],txt_list[j]):
                    repetitive_list.append([txt_list[i],txt_list[j]])
    return repetitive_list

# 两段文字只有同一个位置一个字不一样
def compare_words(a,b):
    not_equal = 0
    for i in range(len(a)):
        if a[i]!=b[i]:
            if a[i] in exclude_words() or b[i] in exclude_words():
                return False
            else:
                not_equal += 1
        if not_equal>1:
            return False
    #只能有一个字处于相同位置且不相同
    if not_equal==1:
        return True
    return False

def exclude_words():
    return ["左","右","前","后","上","下","中","双","内","外","急","慢","近","远","轻","重","高","低","恶","良","A","B","C","1","2","3","4"]

def compare_icd(path1,path2):
    df_sz = pd.read_excel(path1)
    df_gb = pd.read_excel(path2)

    dic_gb = {}
    dic_gb_icd={}
    for i in range(len(df_gb)):
        # if i%200==0:
        #     print i
        key,value = df_gb.iloc[i][2],df_gb.iloc[i][0]
        dic_gb[key]=value
        dic_gb_icd[value]=key

    # f_match = open("sz_match.csv","w")
    f_not_match = open("sz_not_match1.csv", "w")
    f_not_found = open("sz_not_found1.csv", "w")

    for i in range(len(df_sz)):
        dis, icd = df_sz.iloc[i][2], df_sz.iloc[i][3]
        if dis in dic_gb.keys():
            icd_gb=dic_gb[dis]
            try:
                if icd_gb[:3] and icd[:3]:
                    if icd_gb[:3]==icd[:3]:
                        line = dis+"\t"+icd+"\t"+icd_gb+"\n"
                        # f_match.write(line.encode('utf8'))
                        # print "match",dis,icd_gb,icd
                    else:
                        match_dis,match_icd, = get_best_dis_by_icd(icd,dic_gb_icd)
                        line = dis + "\t" + icd + "\t" + icd_gb +"\t"+ match_dis+"\t"+match_icd+"\n"
                        f_not_match.write(line.encode('utf8'))
                        # print "icd not match",dis,icd_gb,icd
            except:
                print dis
        else:
            try:
                match_dis, match_icd, = get_best_dis_by_icd(icd, dic_gb_icd)
                line = dis+"\t"+icd+"\t"+ match_dis+"\t"+match_icd+"\n"
                f_not_found.write(line.encode('utf8'))
            except:
                print dis
            # print "not found",dis,icd
        # if key not in dic_sz.keys():
        #     dic_sz[key] = []
        # dic_sz[key].append(value)

def get_best_dis_by_icd(icd,dic):
    for i in range(7,2,-1):
        if i!=4 and icd[:i] in dic.keys():
            return dic[icd[:i]],icd[:i]
    return "",""

compare_icd("../data/深圳/深圳临床诊断术语集.xlsx","../data/icd/疾病分类与代码国家临床版.xlsx")

# df = pd.read_excel("../data/深圳/深圳临床诊断术语集.xlsx")
#
# dic = {}
# for i in range(len(df)):
#     key,value = df.iloc[i][2],df.iloc[i][1]
#     if key not in dic.keys():
#         dic[key]=[]
#     dic[key].append(value)
#
# for k,v in dic.iteritems():
#     if len(v)>1:
#         res = get_mis_diag(v)
#         if len(res)==1:
#             print k
#             print "----------"
#             for v1 in res:
#                 print v1[0],v1[1]
#             print "=========="



# a=u"高血压"
# b=u"高血脂"
#
# print len(set(a)|set(b))

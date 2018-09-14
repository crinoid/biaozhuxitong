# coding=utf8
import codecs
import xlrd
import re


def simplify(txt):
    REMOVE_LIST=[u"其他",u",不可归类在他处者",u",未经细菌学或组织学所证实",u'特指的',u"未特指的",u"未特指部位的",u"疾病"]
    for r in REMOVE_LIST:
        txt=txt.replace(r,"")

    txt = txt.replace(u"[", u"和")
    txt = txt.replace(u"]", u"和")
    txt = txt.replace(u"及", u"和")
    txt = re.sub("\(.*?\)","",txt)
    arr_txt = txt.split(u"和")

    return arr_txt


with codecs.open("2016国标版.csv", "w", encoding='utf8') as f:
    wb = xlrd.open_workbook("../data/input/2016国标版.xlsx")
    ws = wb.sheet_by_name("Sheet1")
    for i in range(1,ws.nrows):
        value = ws.row_values(i)
        if int(value[3]) == 3:
            result = simplify(value[2])
            for r in result:
                if r:
                    f.write(r + "\t" + value[0] + "\n")

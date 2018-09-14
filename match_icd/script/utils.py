# coding=utf8

import hashlib
import commands
import os

# SERVICE_URL = "http://172.19.19.91:8002/service"
# SUG_SERVICE_URL = "http://172.19.91.91:8002/sugs"
SERVICE_URL_SS = "http://127.0.0.1:8001/service"
SERVICE_URL_ZD = "http://127.0.0.1:8002/service"
# SERVICE_URL_SS = "http://172.19.91.91:8001/service"
# SERVICE_URL_ZD = "http://172.19.91.91:8002/service"

HEADERS = {'content-type': 'application/json'}

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


# print file_compare("../data/icd/cache/shoushu/BJ_icd_name.csv","../data/icd/tmp/shoushu/BJ_icd_name_shoushu.csv")
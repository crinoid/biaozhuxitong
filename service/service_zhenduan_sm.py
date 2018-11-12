#coding=utf8

'''
诊断小粒度分词，用于编目匹配
'''

from flask import Flask, jsonify
from flask import abort
from flask import request

from seg_zhenduan_sm import seg_sentences, seg_sentences_array, update_segment, get_seg_dic
from sug_zhenduan_sm import sugss, sug_sentence, update_suggestion, get_sug_dic


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = '123456' #使用session要设置secret_key

@app.route('/service', methods=['POST'])
def service():
    if not request.json:
        abort(400)
    try:
        json = request.get_json()
        if "seg_para" in json.keys():
            result_seg = seg_sentences_array(json["diag"],json["seg_para"])
        else:
            result_seg = seg_sentences_array(json["diag"])
        result_sug = sugss(result_seg)
        # res = {"diag":result_sug}
        # print "res",res
    except:
        abort(400)

    return jsonify(result_sug)

#分词-标注一体的标注部分
@app.route('/sugs', methods=['POST'])
def sugs():
    if not request.json:
        abort(400)
    try:
        result_sug = sugss(request.get_json())
    except:
        abort(400)

    return jsonify(result_sug)

@app.route('/seg_service', methods=['POST'])
def seg_service():
    if not request.json:
        abort(400)
    try:
        json = request.get_json()
        if "seg_para" in json:
            result_seg = seg_sentences(json["diag"],json[["seg_para"]])
        else:
            result_seg = seg_sentences(json["diag"])
        # result_seg = seg_sentences(request.get_json())
    except:
        abort(400)

    return jsonify(result_seg)

@app.route('/seg', methods=['POST'])
def seg():
    # print "json",request.json
    if not request.json:
        abort(400)
    try:
        json = request.get_json()
        if "seg_para" in json:
            result_seg = seg_sentences_array(json["diag"],json[["seg_para"]])
        else:
            result_seg = seg_sentences_array(json["diag"])
        # result_seg = seg_sentences(request.get_json())
    except:
        abort(400)

    return jsonify(result_seg)

@app.route('/sug_service', methods=['POST'])
def sug_service():
    if not request.json:
        abort(400)
    try:
        result = sug_sentence(request.get_json())
        # print result, jsonify(result)
    except:
        abort(400)

    return jsonify(result)


@app.route('/update_seg', methods=['POST'])
def update_seg():
    try:
        update_segment()
    except:
        abort(400)

    return ""


@app.route('/update_sug', methods=['POST'])
def update_sug():
    try:
        update_suggestion()
    except:
        abort(400)

    return ""


@app.route('/get_seg_dic', methods=['POST'])
def get_segs():
    result = get_seg_dic()
    return jsonify(result)


@app.route('/get_sug_dic', methods=['POST'])
def get_sugs():
    result = get_sug_dic()
    return jsonify(result)


if __name__ == '__main__':
    app.run(
            # host='0.0.0.0',
            port=8006
    )

# result_seg = seg_sentences_array(["肺结核病"])
# print result_seg

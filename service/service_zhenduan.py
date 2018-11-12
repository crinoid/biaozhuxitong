#coding=utf8
from flask import Flask, jsonify
from flask import abort
from flask import request

from seg_zhenduan import seg_sentences, seg_sentences_array, update_segment, get_seg_dic
from sug_zhenduan import sugss, sug_sentence, update_suggestion, get_sug_dic

import base64
import json

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route('/service', methods=['POST'])
def service():
    if not request.json:
        abort(400)
    try:
        json_data = request.get_json()
        if "seg_para" in json_data.keys():
            result_seg = seg_sentences_array(json_data["diag"],json_data["seg_para"])
        else:
            result_seg = seg_sentences_array(json_data["diag"])
        # print result_seg
        if "encode" in json_data.keys():
            result_sug = sugss(result_seg,is_encode=True)
        else:
            result_sug = sugss(result_seg)
    except Exception,e:
        print e.message
        abort(400)
    if "encode" in json_data.keys():
        try:
            result_sug=json.dumps(result_sug, ensure_ascii=False)
            print result_sug
            result_sug=base64.b64encode(result_sug)
            print result_sug
        except Exception,e:
            print e.message
        # return result_sug
    return jsonify(result_sug)


@app.route('/service_xml', methods=['POST'])
def service_xml():
    if not request.json:
        abort(400)
    try:
        json_data = request.get_json()
        if "seg_para" in json.keys():
            result_seg = seg_sentences_array(json_data["diag"],json_data["seg_para"])
        else:
            result_seg = seg_sentences_array(json_data["diag"])
        result_sug = sugss(result_seg,is_xml=True)
    except:
        abort(400)

    return result_sug

@app.route('/sugs', methods=['POST'])
def sugs():
    if not request.json:
        abort(400)
    try:
        result_sug = sugss(request.get_json())
    except:
        abort(400)

    return jsonify(result_sug)

@app.route('/seg', methods=['POST'])
def seg():
    if not request.json:
        abort(400)
    try:
        json = request.get_json()
        if "seg_para" in json:
            result_seg = seg_sentences_array(json["diag"],json[["seg_para"]])
        else:
            result_seg = seg_sentences_array(json["diag"])
    except:
        abort(400)

    return jsonify(result_seg)

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
        print result_seg
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
        print update_suggestion()
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
            port=8002
    )

# result_seg = seg_sentences_array(["前臂骨折"])
# print result_seg
# result_seg={u"高血压":[u"2级"]}
# import json
# new_seg = json.dumps(result_seg, ensure_ascii=True)
# print type(new_seg)
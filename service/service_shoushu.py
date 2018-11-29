#coding=utf8
from flask import Flask, jsonify
from flask import abort
from flask import request

from seg_shoushu import seg_sentence, update_segment, get_seg_dic
from sug_shoushu import sugss, sug_sentence, update_suggestion, get_sug_dic

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route('/service', methods=['POST'])
def service():
    if not request.json:
        abort(400)
    try:
        json_data = request.get_json()
        if "seg_para" in json_data.keys():
            result_seg = seg_sentence(json_data["diag"], json_data["seg_para"])
        else:
            result_seg = seg_sentence(json_data["diag"])
        is_auto_match = False
        if "auto_match" in json_data.keys():
            is_auto_match = json_data["auto_match"]
        if "encode" in json_data.keys():
            result_sug = sugss(result_seg, is_encode=True, is_auto_match=is_auto_match)
        else:
            result_sug = sugss(result_seg,is_auto_match=is_auto_match)
    except Exception as e:
        abort(400)
    return jsonify(result_sug)


@app.route('/seg_service', methods=['POST'])
def seg_service():
    if not request.json:
        abort(400)
    try:
        json = request.get_json()
        if "seg_para" in json:
            result_seg = seg_sentence(json["diag"],json[["seg_para"]])
        else:
            result_seg = seg_sentence(json["diag"])
    except:
        abort(400)

    return jsonify(result_seg)


@app.route('/sug_service', methods=['POST'])
def sug_service():
    if not request.json:
        abort(400)
    try:
        json_data = request.get_json()
        if "auto_match" in json_data.keys():
            is_auto_match = json_data["auto_match"]
        result = sug_sentence(json_data["diag"],is_auto_match)
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
            port=8001
    )

# print sug_sentence([[u"肺结核性",[u"肺结核性"]]],is_auto_match=True)
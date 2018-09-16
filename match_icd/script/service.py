# coding=utf8
from flask import Flask, jsonify
from flask import abort
from flask import request

from match_ICD10_api_zhenduan import icd_service as zd_icd_service
from match_ICD10_api_zhenduan import icd_code_service as zd_icd_code_service
# from match_ICD10_api_zhenduan2 import icd_service as zd_icd_service
# from match_ICD10_api_zhenduan2 import icd_code_service as zd_icd_code_service
from match_ICD10_api_shoushu import icd_service as ss_icd_service
from match_ICD10_api_shoushu import icd_code_service as ss_icd_code_service
import json

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route('/match_icd', methods=['POST'])
def service1():
    if not request.json:
        abort(400)
    try:
        data = request.get_json()

        if data["dbname"] == "zhenduan":
            if "size" in data.keys():
                if int(data["size"]) <= 10 and int(data["size"]) >= 1:
                    result= zd_icd_service(data["diag"], data["source"], int(data["size"]))
            else:
                result = zd_icd_service(data["diag"], data["source"])
        elif data["dbname"] == "shoushu":
            if "size" in data.keys():
                if int(data["size"]) <= 10 and int(data["size"]) >= 1:
                    result= ss_icd_service(data["diag"], data["source"], int(data["size"]))
            else:
                result = ss_icd_service(data["diag"], data["source"])

    except:
        abort(400)

    return jsonify(result)


@app.route('/match_icd_with_code', methods=['POST'])
def service2():
    if not request.json:
        abort(400)
    try:
        data = request.get_json()

        if data["dbname"] == "zhenduan":
            if "size" in data.keys():
                if int(data["size"]) <= 10 and int(data["size"]) >= 1:
                    result= zd_icd_code_service(data["diag"], data["source"], int(data["size"]))
            else:
                result = zd_icd_code_service(data["diag"], data["source"])
        elif data["dbname"] == "shoushu":
            if "size" in data.keys():
                if int(data["size"]) <= 10 and int(data["size"]) >= 1:
                    result= ss_icd_code_service(data["diag"], data["source"], int(data["size"]))
            else:
                result = ss_icd_code_service(data["diag"], data["source"])
    except:
        abort(400)

    return jsonify(result)


if __name__ == '__main__':
    app.run(
        # host='0.0.0.0',
        port=8003
    )

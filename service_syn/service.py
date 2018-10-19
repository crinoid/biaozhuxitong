#coding=utf8
from flask import Flask, jsonify
from flask import abort
from flask import request

from syn_match import get_syn_words

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route('/match_syn', methods=['POST'])
def service():

    def unicode2ascii(data):
        return data.encode('utf8')

    if not request.json:
        abort(400)
    try:
        json = request.get_json()
        terms = map(unicode2ascii, json["term"])
        res={}
        for t in terms:
            res[t]=get_syn_words(t)
    except:
        abort(400)

    return jsonify(res)



if __name__ == '__main__':
    app.run(
            # host='0.0.0.0',
            port=8007
    )

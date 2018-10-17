import _JSON$stringify from 'babel-runtime/core-js/json/stringify';
var MatchICDCode = Vue.extend({
  template: '#match_with_code',
  props: ['id'],

  data: function data() {
    return {
      icds: "",
      source_list: {},
      ischeck: {}, //用于checkbox的v-model，是否选中
      match_result: "" //是否有返回值
    };
  },
  beforeMount: function beforeMount() {
    this.init(this.$route.params.id);
  },
  watch: {
    //默认Vue只在第一次加载初始化，watch用于检测Vue实例的数据是否发生了变化，变化后触发事件
    '$route': function $route(to, from) {
      //跳转的路径（to）
      db = to.path.split("/")[to.path.split("/").length - 1];
      this.init(db);
    }
  },
  components: {
    pg: Page
  },
  methods: {
    init: function init(db) {
      $("#icdname").val("");
      $("#code").val("");
      var _self = this;
      $.ajax({
        type: "post",
        url: "/load_source/",
        data: { db: db },
        success: function success(data) {
          _self.source_list = data["source"];
          _self.ischeck = data["ischeck"];
        }
      });
    },
    match: function match() {
      icd = "";
      code = $(this.$refs.code).val().trim();

      source_list = [];
      for (k in this.ischeck) {
        if (this.ischeck[k]) {
          source_list.push(k);
        }
      }
      if (vutils.jsonLength(source_list) > 0) {
        if (this.check_icd(code, this.$route.params.id)) {
          var _self = this;
          $.ajax({
            type: "post",
            url: "/match_icd_with_code/",
            data: { icd: icd, code: code, source_list: _JSON$stringify(source_list), db: _self.$route.params.id },
            success: function success(data) {
              if (icd != "") _self.icds = data[icd]; //list:[icd,code,ratio,match_index]*n
              else _self.icds = data;

              if (vutils.isEmptyObject(data)) {
                _self.match_result = "暂无结果";
              } else _self.match_result = "";
            }
          });
        } else {
          document.getElementById('code').focus();
          this.match_result = "暂无结果";
          this.icds = "";
          toastr.error("编码格式错误");
        }
      } else {
        this.match_result = "暂无结果";
        this.icds = "";
        toastr.error("请选择术语集来源");
      }
    },
    get_source: function get_source(arr) {
      if (arr.length == 3) return arr[2];else return arr[3];
    },
    has_element: function has_element(arr, b) {
      return vutils.has_element(arr[arr.length - 1], b);
    },
    get_index: function get_index(index) {
      return index + 1;
    },
    check_icd: function check_icd(code, type) {
      if (type == "zhenduan") {
        return this.check_icd_zhenduan(code);
      } else if (type == "shoushu") {
        return this.check_icd_shoushu(code);
      }
    },
    check_icd_zhenduan: function check_icd_zhenduan(code) {
      var reg = /^[A-Za-z][0-9][0-9]$/;
      if (code.length > 2 && code.length < 10) {
        if (reg.test(code.substring(0, 3))) {
          return true;
        }
      }
      return false;
    },
    check_icd_shoushu: function check_icd_shoushu(code) {
      // var reg = /^[0-9][0-9]$/;
      // if (code.length > 1 && code.length < 10) {
      //   if (reg.test(code.substring(0, 2))) {
      //     return true
      //   }
      // }
      // return false
      code = code.replace("x", ""); //有的手术带有x
      code = code.replace(" ", ""); //
      var regPos = /^\d+(\.\d+)?$/; //浮点数
      if (regPos.test(code)) {
        return true;
      } else {
        return false;
      }
    }

  }
});

//# sourceMappingURL=match_icd_with_code-compiled.js.map
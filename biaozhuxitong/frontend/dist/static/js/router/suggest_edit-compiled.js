import _JSON$stringify from 'babel-runtime/core-js/json/stringify';
var SuggestEdit = Vue.extend({
  template: '#suggestedit',

  data: function data() {
    return {
      suggests: [], //标注
      counts: [], //每个标注多少术语
      new_adds: [], //新添加的,删除这类词不需要进入后台
      updated_ctgs: {} //修改的标注
    };
  },

  created: function created() {
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
  methods: {
    init: function init(db) {
      var url = "/get_all_suggests/";
      var _self = this;

      var timeout = setTimeout(function () {
        alert("连接超时");
      }, 5000 //超时时间
      );
      //jquery版写法,还有vue-resource版
      $.ajax({
        type: "post",
        url: url,
        data: { db: db },
        async: false,
        success: function success(data) {
          if (timeout) {
            //清除定时器
            clearTimeout(timeout);
            timeout = null;
          }
          $("#floatLayer").hide();
          $("#liadloging").hide();

          _self.suggests = data['category'];
          _self.counts = data['counts'];
        }
      });
    },
    add_category: function add_category() {
      new_ctg = $("#ctg").val().trim();
      if (vutils.has_element(this.suggests, new_ctg)) {
        toastr.warning("请勿添加重复标注");
      } else if (this.suggests.length > 11) {
        toastr.warning("达到最大标注数量");
      } else if (new_ctg != "") {
        $("#floatLayer").show();
        $("#liadloging").show();
        var _self = this;
        url = '/add_category/';
        $.ajax({
          type: "post",
          url: url,
          data: { newctg: new_ctg },
          async: false,
          success: function success(data) {
            $("#floatLayer").hide();
            $("#liadloging").hide();
            toastr.success("添加成功");
            _self.init(_self.$route.params.id);
          }
          // error: function (XMLHttpRequest, textStatus, errorThrown) {
          //   console.log(textStatus);
          // }
        });
      }
    },
    edit_category: function edit_category(id) {
      $("#" + id).removeClass("input-display");
      $("#" + id).attr("disabled", false);
      $("#" + id).focus();
    },
    delete_category: function delete_category(id) {
      if (!window.confirm("确认删除?")) return false;
      target = $("#" + id).val();
      var _self = this;
      $.ajax({
        type: "post",
        url: '/delete_sug_category/',
        data: { category: target },
        success: function success(data) {
          _self.init(_self.$route.params.id);
          toastr.success("删除成功");
        },
        error: function error(XMLHttpRequest, textStatus, errorThrown) {
          console.log(textStatus);
        }
      });
    },
    // 找出新修改的标注
    update_option: function update_option() {
      updated_ctg = [];
      for (i in this.suggests) {
        updated_ctg.push($("#" + this.suggests[i]).val().trim());
      }
      return updated_ctg;
    },

    update_category: function update_category(id, index) {
      $("#" + id).addClass("input-display");
      $("#" + id).attr("disabled", true);

      if ($("#" + id).val().trim() == "") {
        $("#" + id).val(this.suggests[index]);
      } else if ($("#" + id).val().trim() != this.suggests[index]) {
        url = '/update_sug_category/';
        updated_ctg = this.update_option();
        var _self = this;
        $.ajax({
          type: "post",
          url: url,
          data: { origin_ctg: _JSON$stringify(this.suggests), new_ctg: _JSON$stringify(updated_ctg) },
          success: function success(data) {
            _self.init(_self.$route.params.id);
            toastr.success("保存成功");
          }
        });
      }
    },
    randomString: function randomString() {
      return vutils.randomString();
    }
  }
});

//# sourceMappingURL=suggest_edit-compiled.js.map
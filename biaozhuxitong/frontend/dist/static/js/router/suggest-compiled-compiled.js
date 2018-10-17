import _JSON$stringify from "babel-runtime/core-js/json/stringify";
import _Object$assign from "babel-runtime/core-js/object/assign";
import _Set from "babel-runtime/core-js/set";
var Suggest = Vue.extend({
  template: '#suggest',

  data: function data() {
    return {
      origin_msg: [],
      //origin_msg: "", //当前原文
      suggests: [], //修改的分词标注,总体,提交用
      //cur_suggests: [], //当前的分词
      origin_suggests: [], //原始的分词标注,总体
      cur_items: [], //当前的一组原文+分词标注,cur_items{"msg":..,"seg":...}
      allsuggests: null, //所有标注,标注名:颜色
      edit_index: "", //编辑过的index
      cur: "", //当前选择的分词
      source: [], //标注来源
      cur_source: [],
      save: 0, //选择了当前诊断的所有标注,可以保存(save=1),
      cur_index: 0,
      total: 0,

      total_page: 1, //当前分词总共多少页
      start_page: 1, //当前起始/终止的页数按钮(如1-10,11-20)
      page_arr: [],
      end_page: 0,
      BUTTON_PER_PAGE: 10, //每页多少个页数按钮
      ITEM_PER_PAGE: 20, //每页多少个分词
      select_page: 1, //选择了第几页
      is_prev: false,
      is_next: true
    };
  },

  created: function created() {},
  mounted: function mounted() {
    this.getData();
    vpage.updateStyle(1);
  },
  watch: {
    //默认Vue只在第一次加载初始化，watch用于检测Vue实例的数据是否发生了变化，变化后触发事件
    '$route': function $route(to, from) {
      db = to.path.split("/")[to.path.split("/").length - 1];
      this.init(db);
    }
  },
  components: {
    pg: Page
  },
  methods: {
    //更新标注类型
    init: function init(db) {
      var _self = this;
      $.ajax({
        type: "post",
        url: "/update_suggests/",
        async: false,
        data: { db: db },
        success: function success(data) {
          _self.allsuggests = data['all'];
        }
      });
    },
    getData: function getData() {
      var url = "/send_suggest/";
      var _self = this;

      $("#floatLayer").show();
      $("#liadloging").show();

      // var timeout = setTimeout(function () {
      //     alert("连接超时")
      //   },
      //   5000 //超时时间
      // );
      //jquery版写法,还有vue-resource版
      $.ajax({
        type: "post",
        url: url,
        data: {
          db: this.$route.params.id,
          new_cuts: localStorage.getItem("new_cuts"),
          edit_index: localStorage.getItem("edit_index"),
          origin: localStorage.getItem("msg")
        },
        async: false,
        success: function success(data) {

          // if (timeout) { //清除定时器
          //   clearTimeout(timeout);
          //   timeout = null;
          // }
          if (data == "") {
            //alert("请添加分词!")
            //window.location.href = "/"
          }

          _self.allsuggests = data['all'];

          for (m in data['mark']) {
            _self.total += 1;
            d = data['mark'][m]; //m=分词,d=每个诊断,包含多个分词
            //console.log(d)
            tmp = {};
            tmp2 = {}; //for origin_suggests
            combined_msg = "";
            for (v in d) {
              combined_msg += d[v][0];
              var color = _self.allsuggests[d[v][1]];
              //e.g."高血压"={}
              var text_color = "#000";
              if (d[v][1] == "未知" || d[v][1] == "其他") {
                text_color = "#F00";
              }
              tmp[d[v][0]] = { "items": [d[v][1]], "color": color, "selected": d[v][1], "text_color": text_color };
              tmp2[d[v][0]] = { "items": [d[v][1]], "color": color, "selected": d[v][1], "text_color": text_color };
            }
            _self.suggests.push(tmp);
            _self.origin_suggests.push(tmp2);
            _self.origin_msg.push(combined_msg);
          }
          _self.cur_suggests = _self.suggests[0];

          _self.source = data["source"];
          _self.cur_source = data["source"];

          _self.edit_index = new _Set();

          _self.total = vutils.jsonLength(_self.origin_suggests);
          _self.total_page = Math.ceil(vutils.jsonLength(_self.origin_suggests) / _self.ITEM_PER_PAGE);
          _self.end_page = vpage.getEndPage(_self.total_page);

          _self.page_arr = vpage.updatePageButton();
          //添加原文

          _self.updateItems();

          $("#floatLayer").hide();
          $("#liadloging").hide();
        }
      });
    },
    selectMark: function selectMark(event) {
      //点击分词

      $("div[name='cut-div']").each(function (i) {
        $(this).css("border", "1px solid #222");
      });

      a = event.target;
      this.cur_index = parseInt($(a).parent().parent().attr("id")) + (this.select_page - 1) * this.ITEM_PER_PAGE;
      par = $(a).parent(".cut-to-mark");
      par.css("border", "2px solid red");
      this.cur = $.trim($(par.children()[0]).text());
    },
    selectItem: function selectItem(event) {
      //选择标注,添加到分词上
      a = event.target;
      if ($(a).text() == "") {
        a = $(a).next();
      }
      cur_suggests = this.cur_items[this.cur_index % this.ITEM_PER_PAGE]["sug"];

      var color = this.allsuggests[$(a).text().trim()];
      Vue.set(cur_suggests[this.cur], "color", color);
      Vue.set(cur_suggests[this.cur], "selected", $(a).text().trim());

      this.cur_items[this.cur_index]["sug"] = cur_suggests;
      //数组/字典需要加上这句更新视图
      this.cur_items = _Object$assign({}, this.cur_items);

      this.edit_index.add(this.cur);
    },
    prevPage: function prevPage() {
      if (this.is_prev) {
        this.page_arr = vpage.prevPage();
        this.is_prev = vpage.isPrevEnable(this.page_arr[0]);
        this.updatePageItems();
        this.is_next = true;
      }
    },

    nextPage: function nextPage() {
      this.page_arr = vpage.nextPage();
      this.is_prev = vpage.isPrevEnable(this.page_arr[0]);
      this.updatePageItems();
    },

    updatePageItems: function updatePageItems() {
      //翻页后更新第一页的内容
      this.select_page = this.page_arr[0];
      this.updateItems(this.items_by_sug[this.cur_sug]);
    },

    changePage: function changePage(tar) {
      this.select_page = $(tar).text();
      vpage.changePage($(tar).text());
      this.updateItems();
      vpage.updateStyle("");
    },
    updateItems: function updateItems() {

      this.cur_items = {};

      end = this.select_page * this.ITEM_PER_PAGE;
      if (end > vutils.jsonLength(this.suggests)) {
        end = vutils.jsonLength(this.suggests);
      }
      dic_index = 0;
      for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
        dic = {};
        dic["msg"] = this.origin_msg[i];
        dic["sug"] = this.suggests[i];
        this.cur_items[dic_index] = dic;
        dic_index++;
      }
    },

    reset: function reset(event) {
      a = event.target;
      this.cur_index = parseInt($(a).attr("id")) + (this.select_page - 1) * this.ITEM_PER_PAGE;

      //遍历诊断的每一个分词
      d = this.cur_items[this.cur_index]["sug"]; //分词:标注&颜色
      //console.log(d) //单个分词
      for (k in d) {
        //console.log(k)
        color1 = this.origin_suggests[this.cur_index][k]["color"];

        this.cur_items[this.cur_index]["sug"][k]["color"] = color1;
        var selected = this.origin_suggests[this.cur_index][k]["selected"];
        this.cur_items[this.cur_index]["sug"][k]["selected"] = selected;
      }

      this.cur_items = vutils.deepCopy(this.cur_items);
    },
    saveSuggestion: function saveSuggestion() {
      this.select_page * this.ITEM_PER_PAGE < this.total ? end = this.select_page * this.ITEM_PER_PAGE : end = this.total;

      var j = 0;
      for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
        this.suggests[i] = this.cur_items[j]["sug"];
        this.edit_index.add(i);
        //this.changed_index.add(i)
        j++;
      }
      toastr.success("保存成功");
    },
    submitSuggestion: function submitSuggestion() {
      new_suggests = {};
      for (i in this.cur_items) {
        tmp = {};
        source = ""; //带有分词标记的术语原文
        for (j in this.cur_items[i]["sug"]) {
          //this.cur_items[i]["sug"][j]:一条诊断的分词+标注
          source += j + "/";
          tmp[j] = this.cur_items[i]["sug"][j]["selected"];
        }
        new_suggests[source] = tmp;
      }
      //console.log(origin)
      //console.log(new_suggests)
      //console.log(this.origin_msg)

      //localStorage.setItem("success", 1)
      var url = "/save_suggest/";
      $.post(url, { marks: _JSON$stringify(new_suggests) }, function (data) {

        app.set_router('/', '');
      });
    },
    is_contain: function is_contain(a, b) {
      // console.log(a, b)
      return a.indexOf(b);
    }

  }

});

//# sourceMappingURL=suggest-compiled.js.map

//# sourceMappingURL=suggest-compiled-compiled.js.map
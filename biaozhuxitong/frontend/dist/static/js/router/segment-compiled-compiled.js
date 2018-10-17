import _Set from 'babel-runtime/core-js/set';
var Segment = Vue.extend({
  template: '#segment',
  props: ['id'],

  data: function data() {
    return {
      origin_msg: [], //原始文本
      seg_items: [], //新的分词(用户修改)
      cur_items: {}, //当前的文本&分词,一组ITEM_PER_PAGE个,cur_items{"msg":..,"seg":...}
      new_cur_items: {}, //用于存储cur_items,deepcopy,
      origin_segs: [], //原始分词
      source: [], //分词来源
      total: 0,
      cur_source: [],

      edit_index: "", //编辑过的index
      changed_index: "", //新添加的编辑index
      //is_saved: 2, //当前诊断是否保存过 (未编辑,已编辑)
      //is_editing: 2, //当前诊断是否有修改 (有改动未保存显示*)

      total_page: 1, //当前分词总共多少页
      start_page: 1, //当前起始/终止的页数按钮(如1-10,11-20)
      page_arr: [],
      end_page: 0,
      BUTTON_PER_PAGE: 10, //每页多少个页数按钮
      ITEM_PER_PAGE: 20, //每页多少个分词
      select_page: 1, //选择了第几页
      is_prev: false,
      is_next: true,

      isenable: false
    };
  },

  created: function created() {},
  mounted: function mounted() {
    this.getData(this.$route.params.id);
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
    init: function init(db) {
      var _self = this;
      $.ajax({
        type: "post",
        url: "/update_db/",
        data: { db: db },
        success: function success(data) {}
      });
    },
    getData: function getData(dbname) {

      var url = "/send_segment/";
      var _self = this;

      $("#floatLayer").show();
      $("#liadloging").show();

      // var timeout = setTimeout(function () {
      //     alert("连接超时")
      //   },
      //   5000 //超时时间
      // );
      $.ajax({
        type: "post",
        url: url,
        async: false,
        data: {
          msg: localStorage.getItem("removed_msg"),
          db: dbname

        }, success: function success(data) {
          // if (timeout) { //清除定时器
          //   clearTimeout(timeout);
          //   timeout = null;
          // }
          //从文件读取,2层字典

          _self.edit_index = new _Set();
          _self.changed_index = new _Set();

          _self.origin_msg = [];
          for (i in data["origin"]) {
            _self.origin_msg.push(data["origin"][i]);
            //初始化，全部为空
            _self.seg_items[i] = "";
            _self.origin_segs[i] = "";

            _self.source[i] = "";
            _self.cur_source[i] = "";
          }
          //第一组数据添加进seg_items
          i = 0;
          for (d in data['cut']) {
            tmp = [];
            for (v in data['cut'][d]) {
              tmp.push(data['cut'][d][v]); //index从0开始
            }
            _self.seg_items[i] = tmp;
            _self.origin_segs[i] = tmp;

            _self.source[i] = data["source"][i];
            _self.cur_source[i] = data["source"][i];

            i += 1;
          }
          // console.log(data['cut'])

          //_self.cur_index = 0
          _self.total = data["origin"].length - 1;
          _self.updateItems(false);

          _self.cur_cuts = _self.origin_segs[0];

          _self.total = vutils.jsonLength(_self.origin_msg);
          _self.total_page = Math.ceil(vutils.jsonLength(_self.origin_msg) / _self.ITEM_PER_PAGE);

          _self.end_page = vpage.getEndPage(_self.total_page);
          _self.page_arr = vpage.updatePageButton();
          _self.new_cur_items = _self.cur_items;

          $("#floatLayer").hide();
          $("#liadloging").hide();
        }
      });
    },
    cutMerge: function cutMerge(event) {
      new_cut = [];
      a = event.target;
      div_id = $(a).parent().attr("id");
      span_id = $(a).attr("id");
      //console.log("ids", div_id, span_id)
      index = parseInt($(a).parent().parent().attr("id"));
      seg_index = (this.select_page - 1) * this.ITEM_PER_PAGE + index;
      //console.log(index)
      //每次换页,cur_item会重新赋值
      //console.log("cur_idx",this.cur_items)
      cur_seg = this.cur_items[index]["seg"];
      //console.log("cur_seg",cur_seg)

      if ($(a).prev().text()) {
        //点击的不是第一个,拆分
        for (k in cur_seg) {
          //k=0,1,2...
          new_item = [];
          for (c in cur_seg[k]) {
            //console.log(cur_seg[k])
            if (k == div_id && c == span_id) {
              //console.log(cur_seg[k][c],$.trim($(a).text()))
              new_cut.push(new_item);
              new_item = [];
            }
            new_item.push(cur_seg[k][c]);
          }
          new_cut.push(new_item);
        }
        this.cur_items[index]["seg"] = new_cut;
      } else {
        leng = 0;
        for (leng in cur_seg) {}
        for (var k = leng; k >= 0;) {
          if (cur_seg[k][0] == $.trim($(a).text()) && k == div_id) {
            new_item = [];
            if (k > 0) {
              for (v in cur_seg[k - 1]) {
                new_item.push(cur_seg[k - 1][v]);
              }
            }
            for (v in cur_seg[k]) {
              new_item.push(cur_seg[k][v]);
            }
            k--;
            k--;
            new_cut.unshift(new_item); //放在数组前面
          }
          if (k >= 0) {
            new_cut.unshift(cur_seg[k]);
            k--;
          }
        }
        this.cur_items[index]["seg"] = new_cut;
        this.seg_items[seg_index] = new_cut;
      }
      // deepcopy!! Object.assign()是浅拷贝
      this.cur_items = vutils.deepCopy(this.cur_items);
    },
    jump: function jump() {
      index = $("#item_index").val();
      this.cur_index = index - 1;
      this.updateItems(true);
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
      this.updateItems(true);
    },

    changePage: function changePage(tar) {
      this.select_page = $(tar).text();
      vpage.changePage($(tar).text());
      this.updateItems(true);
      vpage.updateStyle("");
    },
    updateItems: function updateItems(is_post) {
      //切换页面，重新加载分词，分词来源
      end = this.select_page * this.ITEM_PER_PAGE;
      if (end > vutils.jsonLength(this.origin_msg)) {
        end = vutils.jsonLength(this.origin_msg);
      }
      if (is_post) {
        terms = "";
        start = (this.select_page - 1) * this.ITEM_PER_PAGE;
        if (this.seg_items[start] == "") {
          //第一次进入的页，更新数据
          // console.log(start)
          for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
            terms += this.origin_msg[i];
            terms += ";";
          }
          var _self = this;
          $.ajax({
            type: "post",
            url: "/update_seg_source/",
            async: false,
            data: { terms: terms, is_seg: true },
            success: function success(data) {
              // console.log(data)
              start_idx = start;
              for (d in data['segs']) {
                tmp = [];
                for (v in data['segs'][d]) {
                  tmp.push(data['segs'][d][v]); //index从0开始
                }
                _self.seg_items[start_idx] = tmp;
                _self.origin_segs[start_idx] = tmp;
                start_idx += 1;
              }
              start_idx = start;
              for (d in data["sources"]) {
                _self.source[start_idx] = data["sources"][d];
                _self.cur_source[start_idx] = data["sources"][d];
                start_idx += 1;
              }
              // console.log(_self.seg_items)
            }
          });
        }
      }

      this.cur_items = {};
      this.cur_source = {};

      dic_index = 0;
      j = 0;
      for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
        dic = {};
        dic["msg"] = this.origin_msg[i];
        dic["seg"] = this.seg_items[i];
        j += 1;
        this.cur_items[dic_index] = dic;
        this.cur_source[dic_index] = this.source[i];
        dic_index++;
      }
    },
    resign: function resign(event) {
      a = event.target;
      index = parseInt($(a).attr("id")) + (this.select_page - 1) * this.ITEM_PER_PAGE;
      // console.log(this.origin_segs[index])
      // console.log(this.cur_cuts)

      this.cur_cuts = this.origin_segs[index];
      this.cur_items[index]["seg"] = this.cur_cuts;
      this.cur_items = vutils.deepCopy(this.cur_items);
      //this.is_editing = 1
    },
    saveCuts: function saveCuts() {
      this.select_page * this.ITEM_PER_PAGE < this.total ? end = this.select_page * this.ITEM_PER_PAGE : end = this.total;
      var j = 0;
      for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
        this.seg_items[i] = this.cur_items[j]["seg"];
        this.edit_index.add(i);
        this.changed_index.add(i);
        j++;
      }
      toastr.success("保存成功");
    },
    getCuts: function getCuts() {
      if (this.changed_index.size == 0) {
        alert("您还没有保存分词!");
        return false;
      }
      ////这里用edit_index是因为有些已经编辑过了,只考虑没编辑的有没有提交
      //else if (this.edit_index.size < this.origin_segs.length) {
      //    if (!window.confirm("您还有未完成的分词,确认提交吗?"))
      //        return false
      //}

      //console.log("editidx",this.edit_index)
      //console.log(this.seg_items)
      new_cuts = "";
      //console.log("newitems",this.cur_items)
      for (i = 0; i < this.seg_items.length; i++) {
        //tmp = []
        if (this.edit_index.has(i)) {
          t = "";
          //console.log(i,this.seg_items[i]["seg"])
          for (j in this.seg_items[i]) {
            //console.log("j=",j,this.cuts[i]["seg"][j])
            for (k in this.seg_items[i][j]) {
              t += this.seg_items[i][j][k];
              //console.log(k,this.cuts[i]["seg"][j][k])
            }
            t += ",";
          }
          new_cuts += t;
          if (t != "") new_cuts += ";";
        }
      }

      new_msg = [];
      //new_origin_cuts = ""
      //console.log(new_cuts)
      for (i = 0; i < this.origin_msg.length; i++) {
        if (this.changed_index.has(i)) {
          new_msg.push(this.origin_msg[i]);
        }
      }

      //console.log("msg",new_msg)
      // console.log(new_cuts)
      //console.log(this.edit_index)

      new_edit_index = "";
      this.changed_index.forEach(function (element, index, array) {
        new_edit_index += element;
        new_edit_index += ",";
      });

      localStorage.setItem("edit_index", new_edit_index);
      localStorage.setItem("msg", new_msg);
      //new_cuts:右侧,锁骨下动脉,斑块,形成,;低磷性,骨软化症,;
      //不同诊断分号隔开
      localStorage.setItem("new_cuts", new_cuts); //新的分词,写入数据库用


      app.second_path = "zhenduan/";
      app.set_router("suggest/", "");
    }
  }
});

//# sourceMappingURL=segment-compiled.js.map

//# sourceMappingURL=segment-compiled-compiled.js.map
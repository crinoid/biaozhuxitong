import _JSON$stringify from 'babel-runtime/core-js/json/stringify';
var Datafile = Vue.extend({
  template: '#datafile',

  data: function data() {
    return {
      sugs: {}
    };
  },

  created: function created() {},
  mounted: function mounted() {
    this.init(this.$route.params.id);
    vpage.updateStyle($("li[name='page']")[0]);
  },
  watch: {
    //默认Vue只在第一次加载初始化，watch用于检测Vue实例的数据是否发生了变化，变化后触发事件
    '$route': function $route(to, from) {
      db = to.path.split("/")[to.path.split("/").length - 1];
      this.init(db);
    }
  },
  methods: {
    init: function init(db) {
      var _self = this;
      $("#floatLayer").show();
      $("#liadloging").show();

      $.ajax({
        type: "post",
        url: "/get_data/",
        data: { db: db },
        async: false,
        success: function success(data) {
          //if (timeout) { //清除定时器
          //  clearTimeout(timeout);
          //  timeout = null;
          //}

          _self.sugs = data["sugs"];

          $("#floatLayer").hide();
          $("#liadloging").hide();
        }
      });
    },
    addData: function addData() {
      data = this.getSelectedData();
      if (data["sug"]) {
        this.modify("/add_segs_sugs/", data);
      }
      toastr.success("保存成功");
    },
    deleteData: function deleteData() {
      data = this.getSelectedData();
      if (data["sug"]) {
        if (!window.confirm("确认删除?")) return false;
        this.modify("/delete_segs_sugs/", data);
      }
      toastr.success("删除成功");
    },
    getSelectedData: function getSelectedData() {
      data = {};
      data["sug"] = this.get_seleted_items($("#table2 tbody .warning td")); //item1-中心词,item2-部位...
      return data;
    },
    modify: function modify(url, data) {
      var _self = this;
      $.post(url, { msg: _JSON$stringify(data) }, function (data) {
        if (data.hasOwnProperty("sugs")) {
          _self.sugs = data["sugs"];
        } else if (data.hasOwnProperty("items")) {
          _self.sugs = data["items"];
        }

        clear_checkbox($('#table2 thead tr'), $('#table2 tbody tr'));
      });
    },
    get_seleted_items: function get_seleted_items(items) {
      contents = "";
      $.each(items, function (i, item) {
        if (i % 4 === 1) {
          contents += item.innerText + ",";
        }
      });
      return contents;
    },
    downloadSug: function downloadSug() {
      url = "/download_sug/";
      var _self = this;
      $.post(url, function (data) {
        if (data) _self.funDownload(data, "sug.csv");
      });
    },

    // 下载文件
    funDownload: function funDownload(content, filename) {
      var eleLink = document.createElement('a');
      eleLink.download = filename;
      eleLink.style.display = 'none';
      // 字符内容转变成blob地址
      var blob = new Blob([content]);
      eleLink.href = URL.createObjectURL(blob);
      // 触发点击
      document.body.appendChild(eleLink);
      eleLink.click();
      // 然后移除
      document.body.removeChild(eleLink);
    },

    initTableCheckbox: function initTableCheckbox() {
      this.initBox($('#table2 thead tr'), $('#table2 tbody tr'));
    },

    initBox: function initBox($thr, $tbr) {
      var $checkAllTh = $('<th><input type="checkbox" id="checkAll" name="checkAll" /></th>');
      //console.log($checkAllTh)
      //console.log($thr)
      /*将全选/反选复选框添加到表头最前，即增加一列*/
      $thr.prepend($checkAllTh);

      /*“全选/反选”复选框*/
      var $checkAll = $thr.find('input');
      $checkAll.click(function (event) {
        console.log("click");
        /*将所有行的选中状态设成全选框的选中状态*/
        $tbr.find('input').prop('checked', $(this).prop('checked'));
        /*并调整所有选中行的CSS样式*/
        if ($(this).prop('checked')) {
          $tbr.find('input').parent().parent().addClass('warning');
        } else {
          $tbr.find('input').parent().parent().removeClass('warning');
        }
        /*阻止向上冒泡，以防再次触发点击操作*/
        event.stopPropagation();
      });
      /*点击全选框所在单元格时也触发全选框的点击操作*/
      $checkAllTh.click(function () {
        console.log("click1");
        $(this).find('input').click();
      });

      var $checkItemTd = $('<td><input type="checkbox" name="checkItem" /></td>');
      /*每一行都在最前面插入一个选中复选框的单元格*/
      console.log($('table tbody tr'));
      $tbr.prepend($checkItemTd);
      console.log($tbr);
      /*点击每一行的选中复选框时*/
      $tbr.find('input').click(function (event) {
        //console.log("click3")
        /*调整选中行的CSS样式*/
        $(this).parent().parent().toggleClass('warning');
        /*如果已经被选中行的行数等于表格的数据行数，将全选框设为选中状态，否则设为未选中状态*/
        $checkAll.prop('checked', $tbr.find('input:checked').length == $tbr.length ? true : false);
        /*阻止向上冒泡，以防再次触发点击操作*/
        event.stopPropagation();
      });
      /*点击每一行时也触发该行的选中操作*/
      $tbr.click(function () {
        //console.log("click2")
        $(this).find('input').click();
      });
    }
  }
});

function clear_checkbox($thr, $tbr) {
  $tbr.find('input').prop('checked', false);
  $tbr.find('input').parent().parent().removeClass('warning');
  $thr.find('input').prop('checked', false);
}

//# sourceMappingURL=datafile-compiled.js.map
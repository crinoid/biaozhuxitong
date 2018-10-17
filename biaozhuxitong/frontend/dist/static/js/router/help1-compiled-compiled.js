var AllFiles = Vue.extend({
  template: '#allfiles',

  data: function data() {
    return {
      files: {},
      cur_files: {},

      total: 0,
      total_page: 1, //当前分词总共多少页
      start_page: 1, //当前起始/终止的页数按钮(如1-10,11-20)
      end_page: 0,
      page_arr: [],
      BUTTON_PER_PAGE: 10, //每页多少个页数按钮
      ITEM_PER_PAGE: 10, //每页多少个数据
      select_page: 1, //选择了第几页
      is_prev: false,
      is_next: true

    };
  },

  created: function created() {
    this.init(this.$route.params.id);
  },
  mounted: function mounted() {
    vpage.updateStyle(1);
  },
  components: {
    pg: Page
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
      var url = "/get_files/";
      var _self = this;
      $.ajax({
        type: "post",
        url: url,
        data: { db: db },
        async: false,
        success: function success(data) {
          _self.files = data["files"];
          _self.updatePageInfo();
        },
        error: function error(XMLHttpRequest, textStatus, errorThrown) {
          console.log(textStatus);
        }
      });
    },
    updatePageInfo: function updatePageInfo() {
      this.total = vutils.jsonLength(this.files);
      this.total_page = Math.ceil(vutils.jsonLength(this.files) / this.ITEM_PER_PAGE);
      this.end_page = vpage.getEndPage(this.total_page);
      this.updateItems();
      this.page_arr = vpage.updatePageButton();
    },
    selectFile: function selectFile(event) {
      a = event.target;
      filename = $(a).next().text();
      var url = "/select_file/";
      $.post(url, { file: filename }, function (data) {
        app.set_router("segment/", "", "");
      });
    },
    deleteFile: function deleteFile(event) {
      if (!window.confirm("确认删除吗?")) return false;
      a = event.target;
      filename = $(a).prev().text();
      var url = "/delete_file/";
      var _self = this;
      $.post(url, { file: filename }, function (data) {
        _self.files = data["files"];
        _self.updatePageInfo();
        toastr.success("删除成功");
      });
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
      this.updateItems();
    },

    changePage: function changePage(tar) {
      this.select_page = $(tar).text();
      vpage.changePage($(tar).text());
      this.updateItems();
      vpage.updateStyle("");
    },
    updateItems: function updateItems() {
      this.cur_files = {};

      end = this.select_page * this.ITEM_PER_PAGE;
      if (end > vutils.jsonLength(this.files)) {
        end = vutils.jsonLength(this.files);
      }
      j = 0;
      for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
        this.cur_files[j] = vutils.deepCopy(this.files[i]);
        j++;
      }
    }
  }
});

//# sourceMappingURL=help-compiled.jsmap

//# sourceMappingURL=help1-compiled-compiled.js.map
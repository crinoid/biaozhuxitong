var LogManagement = Vue.extend({
  template: '#logmanagement',
  props: ['id'],

  data: function () {
    return {
      origin_msg: [],
      denglu: {},
      shuju:{},
      biaozhu: {},
      wenjian:{},

      cur_type: 'denglu',
      cur_items: [], //当前页显示的内容
      cur_source: [], //数据类型(登录,分词,标注等)

      total: 0,
      total_page: 1, //当前分词总共多少页
      start_page: 1,  //当前起始/终止的页数按钮(如1-10,11-20)
      end_page: 0,
      page_arr: [],
      BUTTON_PER_PAGE: 10, //每页多少个页数按钮
      ITEM_PER_PAGE: 10, //每页多少个分词
      select_page: 1, //选择了第几页
      is_prev: false,
      is_next: true,
    }
  },

  created: function () {

  },
  beforeMount:function(){
    this.init(this.$route.params.id)
  },
  mounted: function () {
    vpage.updateStyle(1)
  },
    watch: { //默认Vue只在第一次加载初始化，watch用于检测Vue实例的数据是否发生了变化，变化后触发事件
    '$route'(to, from){
      db = to.path.split("/")[to.path.split("/").length - 1]
      this.init(db)
    }
  },
  components: {
    pg: Page,
  },
  methods: {
    init: function (db) {
      url = "/get_log_info/"
      var _self = this;
      $("#floatLayer").show()
      $("#liadloging").show()
      // var timeout = setTimeout(function () {
      //     alert("连接超时")
      //   },
      //   5000 //超时时间
      // );
      $.ajax({
        type: "post",
        url: url,
        data: {db: db},
        async: false,
        success: function (data) {
          // if (timeout) { //清除定时器
          //   clearTimeout(timeout);
          //   timeout = null;
          // }
          _self.denglu = data["denglu"]
          _self.shuju = data["shuju"]
          _self.biaozhu = data["biaozhu"]
          _self.wenjian = data["wenjian"]

          _self.cur_source = _self.denglu

          _self.total = vutils.jsonLength(_self.cur_source)
          _self.total_page = Math.ceil(vutils.jsonLength(_self.cur_source) / _self.ITEM_PER_PAGE)
          vpage.setPageCount(data['page_count'])
          _self.ITEM_PER_PAGE=data['page_count']
          _self.end_page = vpage.getEndPage(_self.total_page)
          _self.updateItems()
          _self.page_arr=vpage.updatePageButton()
          _self.new_cur_items = _self.cur_items

          $("#floatLayer").hide()
          $("#liadloging").hide()
        }
      })
    },
    changeType: function (event) {
      a = event.target
      this.cur_type = $(a).attr("id")

      $(a).siblings().each(function () {
        if ($(this).hasClass("btn-info")) {
          $(this).removeClass("btn-info")
          $(this).addClass("btn-default")
        }
      });
      $(a).removeClass("btn-default")
      $(a).addClass("btn-info")

      if (this.cur_type == "denglu") {
        this.cur_source = this.denglu
      } else if (this.cur_type == "shuju") {
        this.cur_source = this.shuju
      } else if (this.cur_type == "biaozhu") {
        this.cur_source = this.biaozhu
      } else if (this.cur_type == "wenjian") {
        this.cur_source = this.wenjian
      }

      this.total = vutils.jsonLength(this.cur_source)
      this.total_page = Math.ceil(vutils.jsonLength(this.cur_source) / this.ITEM_PER_PAGE)

      this.start_page = 1
      this.end_page = vpage.getEndPage(this.total_page)
      this.select_page = 1
      vpage.changePage(this.select_page)
      this.updateItems()
      this.page_arr=vpage.updatePageButton(this.start_page, this.end_page)
      vpage.updateStyle(1)
    },
    prevPage: function () {
      if (this.is_prev) {
        this.page_arr = vpage.prevPage()
        this.is_prev = vpage.isPrevEnable(this.page_arr[0])
        this.updatePageItems()
        this.is_next=true
      }
    }
    ,
    nextPage: function () {
      this.page_arr = vpage.nextPage()
      this.is_prev = vpage.isPrevEnable(this.page_arr[0])
      this.updatePageItems()
    }
    ,
    updatePageItems(){ //翻页后更新第一页的内容
      this.select_page = this.page_arr[0]
      this.updateItems()
    },
    changePage: function (tar) {
      this.select_page = $(tar).text()
      vpage.changePage($(tar).text())
      this.updateItems()
      vpage.updateStyle("")

    },
    updateItems: function () {
      this.cur_items = {}

      end = this.select_page * this.ITEM_PER_PAGE
      if (end > vutils.jsonLength(this.cur_source)) {
        end = vutils.jsonLength(this.cur_source)
      }
      var j = 0
      for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
        this.cur_items[j] = vutils.deepCopy(this.cur_source[i])
        j += 1
      }

    }
  }

})

var Page = Vue.extend({
  template: '#page',
  props: ['page_arr', 'total', 'total_page', 'isenable'],
  methods: {
    // getVue: function () {
    //   if (!("undefined" == typeof Origindata))
    //     return Origindata
    //   else if (!("undefined" == typeof Datafile))
    //     return Datafile
    //   return ""
    // },
    prevPage: function () {
      // 父组件调用子组件的方法
      this.$emit('prev_page')
    },
    nextPage: function () {
      this.$emit('next_page')
    },
    // updateItems: function (event) {
    //   this.$emit('update_items')
    // },
    changePage: function (event) {
      this.$emit('change_page', event.target)
    },

  }
})

var vpage = new Vue({
  data: {
    total: 0, //选择分词的个数
    total_page: 1, //当前分词总共多少页
    start_page: 1,  //当前起始/终止的页数按钮(如1-10,11-20)
    page_list: [],
    end_page: 1,
    BUTTON_PER_PAGE: 10, //每页多少个页数按钮
    ITEM_PER_PAGE: 10, //每页多少个分词
    select_page: 1, //选择了第几页
  },
  created: function () {

  },
  methods: {
    setPageCount: function (page) {
      this.ITEM_PER_PAGE = page
    },
    setStartPage:function(page){
      this.start_page=page
    },
    getEndPage: function (total_page) {
      this.total_page = total_page
      this.end_page = this.BUTTON_PER_PAGE
      if (total_page < this.BUTTON_PER_PAGE) {
        this.end_page = total_page
      }
      return this.end_page
    },
    prevPage: function () {
      if (this.start_page > 1) {
        this.start_page -= this.BUTTON_PER_PAGE
        if (this.start_page < 1) {
          this.start_page = 1
        }
        this.end_page = this.start_page + this.BUTTON_PER_PAGE - 1
        if (this.end_page > this.total_page) {
          this.end_page = this.total_page
        }

        this.updatePageButton("", "")
        this.updateStyle(1)
      }
      return this.page_list

    },
    nextPage: function () {
      if (this.end_page < this.total_page) {
        this.start_page += this.BUTTON_PER_PAGE
        this.end_page += this.BUTTON_PER_PAGE
        if (this.end_page > this.total_page) {
          this.end_page = this.total_page
        }
        this.updatePageButton("", "")
        this.updateStyle(1)
      }
      return this.page_list
    },
    updatePageButton: function (start_page, end_page) {
      if (start_page && end_page) {
        this.start_page = start_page
        this.end_page = end_page
      }
      this.page_list = []
      for (i = this.start_page; i <= this.end_page; i++) {
        this.page_list.push(i)
      }
      return this.page_list
    },
    changePage: function (page) {
      // changePage: function (page, cur_sug, items, cur_items, items_by_sug) {
      //a = event.target
      this.select_page = page
      //$(a).parent().addClass("active")
      // this.updateStyle($("li[name='page']")[this.select_page % 10 == 0 ? 9 : this.select_page % 10 - 1])
      // if (cur_sug == "所有")
      //   this.updateItemsAll(items, cur_sug)
      // else
      // item = this.updateItems(items_by_sug, cur_sug)

      // this.updateStyle($("li[name='page']")[this.select_page % 10 == 0 ? 9 : this.select_page % 10 - 1])

      // return item
      // if (!this.is_tmp) {
      //   if (this.cur_sug == "所有")
      //     this.updateItemsAll(this.items)
      //   else
      //     this.updateItems(this.items_by_sug[this.cur_sug])
      // } else {
      //   this.updateItemsAll(this.tmp_items)
      // }

    },
    isPrevEnable: function (page_num) {
      if (page_num == 1) {
        return false
      }
      return true
    },

    updateItems: function (items_by_sug, cur_sug) {
      tmp_items = []
      //当前分词数小于每页的个数,取分词数
      end = this.select_page * this.ITEM_PER_PAGE
      if (end > vutils.jsonLength(items_by_sug[cur_sug])) {
        end = vutils.jsonLength(items_by_sug[cur_sug])
      }
      for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
        tmp_items.push({"seg": items_by_sug[cur_sug][i], "sug": cur_sug})

      }
      return tmp_items
      // this.cur_items = Object.assign({}, cur_items)

    },
    updateStyle: function (select_page) {
      if (select_page) {
        this.select_page = select_page
      }
      pages = $("li[name='page']")
      $.each(pages, function (i, n) {
        $(pages[i]).removeClass("active")
      });
      // console.log($($("li[name='page']")[this.select_page % 10 == 0 ? 9 : this.select_page % 10 - 1]))
      $($("li[name='page']")[this.select_page % 10 == 0 ? 9 : this.select_page % 10 - 1]).addClass("active")
    },
    // deepCopy: function (source) {
    //   var result = {}
    //   for (var key in source) {
    //     result[key] = typeof source[key] === 'object' ? this.deepCopy(source[key]) : source[key];
    //   }
    //   return result;
    // }
  }
})

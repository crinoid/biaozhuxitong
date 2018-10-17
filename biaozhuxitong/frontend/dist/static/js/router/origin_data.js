var Origindata = Vue.extend({
  template: '#origindata',
  props: ['id'],

  data: function () {
    return {
      items: {}, //所有分词
      cur_items: {}, //当前页的分词
      items_by_sug: {}, //某个标注的分词 {中心词:[],部位:[],}
      tmp_items: {},//查找的所有分词
      is_tmp: false,
      cur_sug: "", //查看的标注
      all_sugs: [], //所有标注
      selected_items: [], //选择的(要删除的)分词
      updated_sugs: {}, //更新标注的 {sug:seg}
      is_ok: 0, //上传数据是否都符合规范

      total: 0, //选择分词的个数
      total_page: 1, //当前分词总共多少页
      start_page: 1,  //当前起始/终止的页数按钮(如1-10,11-20)
      page_arr: [],
      end_page: 0,
      BUTTON_PER_PAGE: 10, //每页多少个页数按钮
      ITEM_PER_PAGE: 10, //每页多少个分词
      select_page: 1, //选择了第几页
      is_prev: false,
      is_next: true,

      new_data: {}, //新增数据
      old_data: {}, //覆盖的数据
    }
  },

  created: function () {

  },
  beforeMount: function () {
    this.init(this.$route.params.id)
  },
  mounted: function () {
    $("#alert").hide()
    vpage.updateStyle(1)
  },
  watch: { //默认Vue只在第一次加载初始化，watch用于检测Vue实例的数据是否发生了变化，变化后触发事件
    '$route'(to, from){
      //跳转的路径（to）
      db = to.path.split("/")[to.path.split("/").length - 1]
      this.init(db)
    }
  },
  components: {
    pg: Page,
  },
  methods: {
    init: function (db) {
      var url = "/get_origin_data/";
      var _self = this;
      // var timeout = setTimeout(function () {
      //     alert("连接超时")
      //   },
      //   5000 //超时时间
      // );
      $("#floatLayer").show()
      $("#liadloging").show()

      $.ajax({
        type: "post",
        url: url,
        async: false,
        data: {db: db},
        success: function (data) {
          // if (timeout) { //清除定时器
          //   clearTimeout(timeout);
          //   timeout = null;
          // }

          _self.items = data["items"]
          _self.all_sugs = data["all_sug"]
          _self.cur_sug = "所有"

          vpage.setPageCount(data['page_count'])
          _self.ITEM_PER_PAGE = data['page_count']

          for (i in data["all_sug"]) {
            _self.items_by_sug[data["all_sug"][i]] = []

          }

          for (i in data["items"]) {
            try { //有时手动修改数据导致标注在标注列表中不存在，这样会报错
              _self.items_by_sug[data["items"][i]["sug"]].push(data["items"][i]["seg"])
            } catch (error) {
              console.log("sug not exist",data["items"][i]["seg"])
            }
          }

          _self.changePageButton()

          $("#floatLayer").hide()
          $("#liadloging").hide()
        }
      })
    },
    refreshItem: function () {
      this.select_page = 1
      this.total_page = Math.ceil(vutils.jsonLength(this.items_by_sug[this.cur_sug]) / this.ITEM_PER_PAGE)
      // this.updateItems(this.items_by_sug[this.cur_sug])
      this.updateItemsAll(this.items)
      this.total = vutils.jsonLength(this.items_by_sug[this.cur_sug])
      this.start_page = 1
      this.end_page = vpage.getEndPage(this.total_page)
      this.page_arr = vpage.updatePageButton(this.start_page, this.end_page)

    },
    checkFile: function () { //检查上传的数据是否有不规范的
      var formData = new FormData();
      formData.append("myfile", document.getElementById("targetFile").files[0]);

      var _self = this
      $.ajax({
        url: "/check_file/",
        type: "POST",
        data: formData,
        contentType: false,
        processData: false,
        success: function (data) {
          $("#floatLayer").hide()
          $("#liadloging").hide()
          _self.old_data = data
          if (data["error"].length == 0 && vutils.isEmptyObject(data["duplicate"]) && data["types"].length == 0) {
            _self.is_ok = 1
          }

        }
      })
    },
    uploadNewfile: function () {
      $("#floatLayer").show()
      $("#liadloging").show()
      selected_type = ""

      // var formData = new FormData();
      // formData.append("myfile", document.getElementById("targetFile").files[0]);
      if ($("#is_cover_cbk").prop("checked")) {
        checked = 1
      } else {
        checked = 0
      }

      var _self = this
      $.ajax({
        url: "/upload_data_file/",
        type: "POST",
        data: {checked: checked},
        success: function (data) {
          $("#floatLayer").hide()
          $("#liadloging").hide()
          _self.old_data = data

          $('#myModal').modal('hide');
          toastr.success("上传成功");

          _self.items = data["items"]
          _self.all_sugs = data["all_sug"]
          _self.cur_sug = _self.all_sugs[0]

          for (i in data["all_sug"]) {
            _self.items_by_sug[data["all_sug"][i]] = []

          }

          for (i in data["items"]) {
            _self.items_by_sug[data["items"][i]["sug"]].push(data["items"][i]["seg"])
          }

          _self.refreshItem()
        }
      })
    },
    searchItem: function () {
      searchText = $(this.$refs.searchTxt).val().trim()

      $("#floatLayer").show()
      $("#liadloging").show()

      var url = "/search_item/";
      var _self = this
      $.post(url, {msg: searchText, type: _self.cur_sug}, function (data) {
        data = eval(data)
        _self.tmp_items = []

        for (k in data) {
          for (i in _self.items) {
            if (data[k] == _self.items[i]["seg"]) {
              _self.tmp_items.push(_self.items[i])
            }
          }
        }
        _self.is_tmp = true

        _self.total = vutils.jsonLength(_self.tmp_items)
        _self.total_page = Math.ceil(vutils.jsonLength(_self.tmp_items) / _self.ITEM_PER_PAGE)

        _self.end_page = vpage.getEndPage(_self.total_page)

        // _self.start_page = 1
        // _self.end_page = _self.BUTTON_PER_PAGE
        // if (_self.total_page < _self.BUTTON_PER_PAGE) {
        //   _self.end_page = _self.total_page
        // }

        _self.cur_items = []
        end = _self.total > _self.ITEM_PER_PAGE ? _self.ITEM_PER_PAGE : _self.total
        for (i = 0; i < end; i++) {
          _self.cur_items.push(_self.tmp_items[i])
        }
        _self.cur_items = Object.assign({}, _self.cur_items)
        _self.page_arr = vpage.updatePageButton(_self.start_page, _self.end_page)
        // _self.refreshItem()
        vpage.updateStyle(1)

        $("#floatLayer").hide()
        $("#liadloging").hide()
      })
    },
    combineSegSug: function (seg, sug, index) {
      return seg + "-" + sug[index]
    },
    rewriteData: function () {
      var _self = this
      new_data = []
      for (var seg in this.old_data["duplicate"]) {
        new_data.push([seg, this.old_data["duplicate"][seg][1]])
      }
      $.ajax({
        type: "post",
        url: "/update_duplicate_data/",
        data: {
          msg: JSON.stringify(new_data)
        }, success: function () {
          $("#alert").hide()
          toastr.success("上传成功");
        }
      })
    },
    cancel: function () {
      $("#alert").hide()
    },
    changeType: function (event) {
      this.selected_items = []
      a = event.target
      this.is_tmp = false
      this.cur_sug = $(a).text().trim()

      this.changePageButton()
    },
    changePageButton: function () {
      this.start_page = 1
      this.select_page = 1
      if (this.cur_sug == "所有") {
        this.total_page = Math.ceil(vutils.jsonLength(this.items) / this.ITEM_PER_PAGE)
        this.updateItemsAll(this.items)
        this.total = vutils.jsonLength(this.items)
      }
      else {
        this.total_page = Math.ceil(vutils.jsonLength(this.items_by_sug[this.cur_sug]) / this.ITEM_PER_PAGE)
        this.updateItems(this.items_by_sug[this.cur_sug])
        this.total = vutils.jsonLength(this.items_by_sug[this.cur_sug])
      }
      this.end_page = vpage.getEndPage(this.total_page)

      this.page_arr = vpage.updatePageButton(this.start_page, this.end_page)
      vpage.updateStyle(1)

      //切换分类，取消选中checkbox
      $tbr = $('#table tbody tr')
      $tbr.find('input').prop('checked', false);
      /*并调整所有选中行的CSS样式*/
      // if ($(obj).prop('checked')) {
      //   $tbr.find('input').parent().parent().addClass('warning');
      // } else {
      //   $tbr.find('input').parent().parent().removeClass('warning');
      // }
    },
    // 切换标注类型,更新数据
    updateDataByType: function () {
      this.select_page = 1
      this.total_page = Math.ceil(vutils.jsonLength(this.items_by_sug[this.cur_sug]) / this.ITEM_PER_PAGE)
      if (this.cur_sug == "所有") {
        this.total_page = Math.ceil(vutils.jsonLength(this.items) / this.ITEM_PER_PAGE)
        this.updateItemsAll(this.items)
        this.total = vutils.jsonLength(this.items)
      }
      else {
        this.updateItems(this.items_by_sug[this.cur_sug])
        this.total = vutils.jsonLength(this.items_by_sug[this.cur_sug])
      }
      // this.updateItems(this.items_by_sug[this.cur_sug])
      // this.total = vutils.jsonLength(this.items_by_sug[this.cur_sug])

      // this.start_page = 1
      // this.end_page = this.BUTTON_PER_PAGE
      // if (this.total_page < this.BUTTON_PER_PAGE) {
      //   this.end_page = this.total_page
      // }
      this.end_page = vpage.getEndPage(this.total_page)

      // this.updatePageButton()
      this.page_arr = vpage.updatePageButton(this.start_page, this.end_page)
      vpage.updateStyle("")

      $tbr = $('#table tbody tr')
      $tbr.find('input').prop('checked', false);

    },
    prevPage: function () {
      if (this.is_prev) {
        this.page_arr = vpage.prevPage()
        this.is_prev = vpage.isPrevEnable(this.page_arr[0])
        this.updatePageItems()
        this.is_next = true
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
      // this.updateItems(this.items_by_sug[this.cur_sug])
      if (!this.is_tmp) {
        if (this.cur_sug == "所有")
          this.updateItemsAll(this.items)
        else
          this.updateItems(this.items_by_sug[this.cur_sug])
      } else {
        this.updateItemsAll(this.tmp_items)
      }
    },
    // updatePageButton: function () {
    //   this.page_arr = []
    //   for (i = this.start_page; i <= this.end_page; i++) {
    //     this.page_arr.push(i)
    //   }
    // }
    // ,
    changePage: function (tar) {
      // this.select_page = $(a).text()
      // $(a).parent().addClass("active")
      // //从select中选取


      this.select_page = $(tar).text()
      vpage.changePage($(tar).text())
      if (!this.is_tmp) {
        if (this.cur_sug == "所有")
          this.updateItemsAll(this.items)
        else
          this.updateItems(this.items_by_sug[this.cur_sug])
      } else {
        this.updateItemsAll(this.tmp_items)
      }
      // this.updateItems(this.items_by_sug[this.cur_sug])
      this.update_selected_items()
      vpage.updateStyle("")

      //$checkAll = $thr.find('input')
      ///*如果已经被选中行的行数等于表格的数据行数，将全选框设为选中状态，否则设为未选中状态*/
      //$checkAll.prop('checked', $tbr.find('input:checked').length == $tbr.length ? true : false);

    }
    ,
    updateItemsAll: function (item) {
      this.cur_items = []
      //当前分词数小于每页的个数,取分词数
      end = this.select_page * this.ITEM_PER_PAGE
      if (end > vutils.jsonLength(item)) {
        end = vutils.jsonLength(item)
      }
      for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
        this.cur_items.push(item[i])

      }
      this.cur_items = Object.assign({}, this.cur_items)
    }
    ,
    updateItems: function (item) {
      this.cur_items = []
      //当前分词数小于每页的个数,取分词数
      end = this.select_page * this.ITEM_PER_PAGE
      if (end > vutils.jsonLength(item)) {
        end = vutils.jsonLength(item)
      }
      for (i = (this.select_page - 1) * this.ITEM_PER_PAGE; i < end; i++) {
        this.cur_items.push({"seg": item[i], "sug": this.cur_sug})

      }
      this.cur_items = Object.assign({}, this.cur_items)

    },
    save_items: function () {
      $("#floatLayer").show()
      $("#liadloging").show()
      url = "/update_segs_sugs/"
      var _self = this
      $.post(url, {msg: JSON.stringify(this.updated_sugs)}, function (data) {
        for (i in data["all_sug"]) {
          _self.items_by_sug[data["all_sug"][i]] = []
        }
        for (i in data["items"]) {
          _self.items_by_sug[data["items"][i]["sug"]].push(data["items"][i]["seg"])
        }
        _self.updateDataByType()
        $("#floatLayer").hide()
        $("#liadloging").hide()
        toastr.success("更新成功");

        $("#checkAll").prop('checked', false)
        $tbr = $('#table tbody tr')
        $tbr.find('input').prop('checked', false);
        $tbr.find('input').parent().parent().removeClass('warning');
      })
    }
    ,
    delete_items: function () {
      if (this.selected_items.length > 0) {
        items = this.update_items()
        if (!window.confirm("确认删除?"))
          return false
        $("#floatLayer").show()
        $("#liadloging").show()
        url = "/delete_segs_sugs/"
        var _self = this
        $.post(url, {msg: JSON.stringify(items), source: "现有文件"}, function (data) {
          for (i in data["all_sug"]) {
            _self.items_by_sug[data["all_sug"][i]] = []
          }
          _self.items = data["items"]
          for (i in data["items"]) {
              _self.items_by_sug[data["items"][i]["sug"]].push(data["items"][i]["seg"])
              _self.items_by_sug = Object.assign({}, _self.items_by_sug)
          }
          _self.updateDataByType()
          vpage.updateStyle(1)
          $("#floatLayer").hide()
          $("#liadloging").hide()
          toastr.success("删除成功");

          $("#checkAll").prop('checked', false)
          $tbr = $('#table tbody tr')
          $tbr.find('input').prop('checked', false);
          $tbr.find('input').parent().parent().removeClass('warning');
        })
      }
    }
    ,
    checkAllTable: function (event) {
      obj = event.target
      if ($(obj).prop('checked')) {
        for (i = 0; i < this.BUTTON_PER_PAGE; i++) {
          this.selected_items.push(i + (this.select_page - 1) * this.BUTTON_PER_PAGE)
        }
      } else {
        for (i = 0; i < this.BUTTON_PER_PAGE; i++) {
          vutils.removeByValue(this.selected_items, i + (this.select_page - 1) * this.BUTTON_PER_PAGE)
        }
      }
      $tbr = $('#table tbody tr')
      $tbr.find('input').prop('checked', $(obj).prop('checked'));
      /*并调整所有选中行的CSS样式*/
      if ($(obj).prop('checked')) {
        $tbr.find('input').parent().parent().addClass('warning');
      } else {
        $tbr.find('input').parent().parent().removeClass('warning');
      }
    }
    ,
    selectItemTable: function (event, $thr, $tbr) {
      obj = event.target
      $thr = $('#table thead tr')
      $tbr = $('#table tbody tr')

      id = $(obj).parent().parent().attr("id")
      id = parseInt(id) + (this.select_page - 1) * this.ITEM_PER_PAGE
      if ($(obj).parent().parent().hasClass('warning')) {
        vutils.removeByValue(this.selected_items, id)
      }
      else {
        this.selected_items.push(id)
      }
      $(obj).parent().parent().toggleClass('warning')
      // console.log(this.selected_items)

    }
    ,
//上一页选中的id
    get_seleted_items: function () {
      contents = []
      $.each($("#table tbody .warning td"), function (i, item) {
        if (i % 3 === 1) {
          contents.push($(item).parent().attr("id"))
        }
      })
      return contents
    }
    ,
    update_selected_items: function () {
      //换页后,将上一页选中的添加到selected_item里
      s_items = this.selected_items

      $tbr = $('#table tbody tr')
      var _self = this
      is_check_all = true //是否全选
      $.each($tbr, function (idx, obj) { //此时obj是上一页内容,这里只是获取checkbox,跟内容无关
        item = $(obj).next().text().split(" ")[1]
        idx = idx + (_self.select_page - 1) * _self.BUTTON_PER_PAGE
        //console.log(idx, _self.selected_items)

        // 上一页此节点选中,但是这一页对应的没有选过,去掉check
        if ($(obj).find('input').is(':checked')) {
          $(obj).find('input').prop("checked", false)
          $(obj).removeClass('warning');
        }
        if (vutils.has_element(_self.selected_items, idx)) { //这个节点的内容已经选过,添加check
          $(obj).find('input').prop("checked", true)
          $(obj).addClass('warning');
        }
        is_check_all = $(obj).find('input').prop("checked") ? is_check_all : false
      })
      $("#checkAll").prop('checked', is_check_all);
    },

    update_items: function () {
      if (!this.is_tmp) {
        if (this.cur_sug == "所有")
          items = this.items
        else
          items = this.items_by_sug[this.cur_sug]
      } else {
        items = this.tmp_items
      }

      count = this.selected_items.length
      find_count = 0
      find_segs = {}
      for (k in items) {

        if (vutils.has_element(this.selected_items, k)) {
          tmp = {}

          if (this.cur_sug == "所有" && !this.is_tmp) {
            find_segs[find_count] = items[k]
          }
          else if (this.is_tmp) {
            find_segs[find_count] = items[k]
          }
          else {
            tmp = {}
            tmp["seg"] = items[k]
            tmp["sug"] = this.cur_sug
            find_segs[find_count] = tmp
          }

          find_count++
          if (find_count == count) {
            return find_segs
          }
        }
      }
      return find_segs
    }
    ,
//修改标注类型
    update_option: function (event) {
      obj = event.target
      //console.log($(obj).parent().prev().text())
      //if ($(obj).val() != this.cur_sug) {
      this.updated_sugs[$(obj).parent().prev().text()] = $(obj).val()
      //}
      //console.log(this.updated_sugs)
    },
    is_empty: function (obj) {
      return vutils.isEmptyObject(obj)
    }

  }
})


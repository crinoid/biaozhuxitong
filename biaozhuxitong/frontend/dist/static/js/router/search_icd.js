var SearchICD = Vue.extend({
  template: '#search_icd',
  props: ['id'],

  data: function () {
    return {
      diag_files: {}, //所有诊断文件
      diag_list: [], //上传的诊断内容
      cur_diag: "", //当前处理的诊断
      cur_diag_idx: 0,
      hints: {}, //提示 {高血压:I00}
      diag_match: {}, //诊断匹配结果
      source_dic: {}, //icd来源 {国标版：GB}
      selected_value: "", //radio选中值
      ischeck: {}, //radio选中情况 true/false
      result: {}, //查询结果
    }
  },

  created: function () {

  },
  beforeMount: function () {
    this.init(this.$route.params.id)
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
      var _self = this
      this.hints={}
      this.result={}
      $.ajax({
        type: "post",
        url: "/load_source/",
        data: {db: db, radio: 1},
        success: function (data) {
          _self.source_dic = data["source"]
          _self.ischeck = data["ischeck"]
          _self.diag_files = data["diag_files"]
          for (i in _self.ischeck) {
            if (_self.ischeck[i] == "checked")
              _self.selected_value = i
          }
        }
      })
    },
    changeInput: function (index) {
      for (i in this.ischeck) {
        if (i == index) {
          this.ischeck[i] = "checked"
          this.selected_value = i
        }
        else
          this.ischeck[i] = ""
      }
      this.result = {} //清空搜索列表
    },
    changeKeyword: function () { //输入关键字
      var _self = this

      index = "icd-" + this.selected_value.toLowerCase()

      $.ajax({
        url: "/show_hint/",
        type: "POST",
        data: {
          prefix:this.$route.params.id,
          index:index,
          keyword: $("#keyword").val().trim()},
        success: function (data) {
          _self.hints = data["res"]
        }
      })
    },
    upload: function () { //上传文件
      var formData = new FormData();
      formData.append("myfile", document.getElementById("f_upload").files[0]);

      var _self = this

      $.ajax({
        url: "/upload_diag/",
        type: "POST",
        data: formData,
        contentType: false,
        processData: false,
        success: function (data) {
          _self.update_file_info(data)
        }
      })
    },
    select_file: function (code) {
      var _self = this
      $.ajax({
        url: "/show_diag_file/",
        data: {code: code},
        type: "POST",
        success: function (data) {
          _self.update_file_info(data)
        }
      })
    },
    update_file_info: function (data) {
      this.diag_list = data["diag"]
      for (i in data["diag"]) {
        tmp = {}
        for (j in this.source_dic) {
          tmp[this.source_dic[j]] = {"icd": "", code: ""}
        }
        this.diag_match[data["diag"][i]] = tmp
      }
    },
    //删除匹配文件
    delete_file: function (code) {
      var _self = this
      $.ajax({
        url: "/delete_diag_file/",
        data: {code: code},
        type: "POST",
        success: function (data) {
          _self.diag_files = data["diag_files"]
        }
      })
    },
    hide_box:function()
    {
      this.hints={}
    },
    prev_diag: function () {
      if (this.cur_diag_idx > 0)
        this.cur_diag_idx--
    },
    next_diag: function () {
      if (this.cur_diag_idx < this.diag_list.length - 1)
        this.cur_diag_idx++
    },
    search_keyword: function () {
      var _self = this;
      url = "/search_from_keyword/"

      index = "icd-" + this.selected_value.toLowerCase()

      $.ajax({
        type: "post",
        url: url,
        data: {
          prefix:this.$route.params.id,
          index: index, //icd-gb,icd-lc等
          keyword: $("#keyword").val().trim()
        }, success: function (data) {
          _self.result = data["res"]
        }
      })
      this.hints = ""
    },
    //从提示中选择
    update: function (icd, code) {
      this.hints = ""
      if (vutils.jsonLength(this.diag_match) > 0) {
        this.diag_match[this.diag_list[this.cur_diag_idx]][this.selected_value]["icd"] = icd
        this.diag_match[this.diag_list[this.cur_diag_idx]][this.selected_value]["code"] = code
        this.diag_match = vutils.deepCopy(this.diag_match)
      }
    },
    // 选择icd,添加到诊断对应中
    update_icd: function (item) {
      if (vutils.jsonLength(this.diag_match) > 0) {
        this.diag_match[this.diag_list[this.cur_diag_idx]][this.selected_value]["icd"] = item[0]
        this.diag_match[this.diag_list[this.cur_diag_idx]][this.selected_value]["code"] = item[1]
        this.diag_match = vutils.deepCopy(this.diag_match)
      }

      // console.log(this.diag_match)
    },
    submit_icd: function () {
      var _self = this
      $.ajax({
        type: "post",
        url: "/submit_icd/",
        async: false,
        data: {
          match: JSON.stringify(this.diag_match), //匹配结果，dict

        }, success: function (data) {
            _self.diag_list=[]
            _self.cur_diag=""
            _self.cur_diag_idx=0
          toastr.success("提交成功");
        }
      })
    },
    get_length:function(data){
      return vutils.isEmptyObject(data)
    }

  }
})

var Main = Vue.extend({
  template: '#main',

  data: function data() {
    return {
      msg: null,
      placeholder: "",
      myFile: ""
    };
  },
  created: function created() {
    localStorage.clear();
    this.init(this.$route.params.id);
  },
  mounted: function mounted() {
    $('#f_upload').fileinput({
      theme: 'fa',
      language: 'zh',
      showUpload: true,
      showCaption: false,
      enctype: 'multipart/form-data',
      uploadUrl: 'upload/',
      isAjaxUpload: true,
      allowedFileExtensions: ['csv', 'txt', 'xlsx', 'xls'],
      dropZoneTitle: "拖拽文件到这里"
    });
    $(".fileinput-upload").click(function () {
      $('#f_upload').fileinput('upload');
    });
    $('#f_upload').on("fileuploaded", function (event, data, previewId, index) {
      app.set_router("segment/", "", "");
    });
  },
  watch: {
    //默认Vue只在第一次加载初始化，watch用于检测Vue实例的数据是否发生了变化，变化后触发事件
    '$route': function $route(to, from) {
      //跳转的路径（to）
      //获得选择的术语集（疾病诊断，症状体征等）
      db = to.path.split("/")[to.path.split("/").length - 1];
      this.init(db);
    },

    myFile: function myFile() {
      console.log("change");
      $("#submit").attr("disabled", false);
    }
  },
  beforeDestroy: function beforeDestroy() {
    $("#f_upload").fileinput('destroy');
  },
  methods: {
    init: function init(db) {
      var _self = this;
      $.ajax({
        type: "post",
        url: '/get_session/',
        data: { db: db },
        success: function success(data) {
          if (data['active_zd']) _self.placeholder = "请输入诊断文本";else if (data['active_ss']) _self.placeholder = "请输入手术文本";
          if (data['auth_log'] == '0') {
            $("#logdata").hide();
          }
          if (data['auth_new_data'] == '0') {
            $("#newdata").hide();
          }
          if (data['auth_origin_data'] == '0') {
            $("#origindata").hide();
          }
        }
      });
    },
    getMessage: function getMessage() {
      msg = $("#txt").val().trim(); //ref
      if (msg != "") {
        localStorage.setItem("msg", msg); //原始文本
        localStorage.setItem("removed_msg", msg); //去掉特殊字符的文本

        $.ajax({
          type: "post",
          url: "clear_session/",
          success: function success() {
            app.set_router("segment/", "", "");
          }
        });
      } else {
        toastr.error("请输入文本");
      }
    },
    upload: function upload() {
      var formData = new FormData();
      formData.append("myfile", document.getElementById("f_upload").files[0]);

      $.ajax({
        url: "/upload/",
        type: "POST",
        data: formData,
        contentType: false,
        processData: false,
        success: function success(data) {
          app.set_router("segment/", "", "");
        }
      });
    },
    filechange: function filechange() {
      //filesize = obj.files[0].size
      //size = filesize / 1024
      //console.log(size)
      //
      //if (size < 10000) {
      //  console.log(size)
      $("#submit").attr("disabled", false);
      //}
      //else {
      //  alert("上传的文件不能超过1M!")
      //}
    }
  }
});

//# sourceMappingURL=main-compiled.js.map
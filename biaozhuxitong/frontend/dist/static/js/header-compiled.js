var Header = Vue.extend({
  template: "<div class='title-div'>" + "<div class='title'><h2><a href='/'>标注系统</a></h2></div>" + "<div class='user-info'><div style='height: 24px;'>" + "<div style='float: right'>欢迎,{{ username }}<a id='logout' href='/logout/'>登出</a></div></div>" + "<ul id='top' style='cursor: pointer'><li @click=\"update_style('zhenduan')\" v-bind:class='{active: is_active_zd}'>" + "<a v-bind:style='{color:color_zd}'>疾病诊断</a></li>" + "<li @click=\"update_style('shoushu')\" v-bind:class='{ active: is_active_ss}'>" + "<a v-bind:style='{color:color_ss}'>手术操作</a></li><li><a href='#'>症状体征</a></li>" + "<li><a href='#'>检验检查</a></li><li><a href='#'>用药</a></li></ul></div></div>",

  props: ["username", "is_active_zd", "color_zd", "is_active_ss", "color_ss"],

  data: function data() {
    return {
      //username: "",
      //isActive_zd: "",
      //color_zd: "",
      //isActive_ss: "",
      //color_ss: ""
    };
  },
  mounted: function mounted() {//相当于document.ready
    //this.update_style("")
  },
  methods: {
    update_style: function update_style(db) {
      //var _self = this
      //$.ajax({
      //  type: "get",
      //  url: "/update_category/",
      //  data:{db:db},
      //  async: false,
      //  success: function (data) {
      //    //var json = res.body;
      //    //data = eval("(" + json + ")")
      //    _self.$set(_self, "username", data["username"])
      //    _self.$set(_self, "color_zd", data["color_zd"])
      //    _self.$set(_self, "isActive_zd", data["active_zd"])
      //    _self.$set(_self, "color_ss", data["color_ss"])
      //    _self.$set(_self, "isActive_ss", data["active_ss"])
      //  }
      //})
      //if (flag)
      vm.init(db);
    }
  }
});

//# sourceMappingURL=header-compiled.js.map
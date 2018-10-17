//$('#sub-btn').append("<div style='background-color: #eee;width: 100%;padding:10px 0 10px" +
//  " 20px;margin-bottom:20px;color: white;'>" +
//            "<button class='btn btn-default' onclick=\"window.location.href='/all_files'\"> 查看上传文件 </button>" +
//            "<button id='newdata' class='btn btn-default'" +
//  "  onclick=\"window.location.href='/datafile'\">查看新增数据</button>" +
//            "<button id='origindata' class='btn btn-default'" +
//  " onclick=\"window.location.href='/origin_data'\">查看原始数据</button>" +
//            "<button id='logdata' class='btn btn-default'" +
//  " onclick=\"window.location.href='/log_management'\">日志管理</button>" +
//      "<button class='btn btn-default' onclick=\"window.location.href='/suggest_edit'\">编辑标注</button>" +
//            "</div>"
//)
var SubItems = Vue.extend({
  template: "<div style='background-color: #eee;width: 100%;padding:10px 0 10px" + " 20px;margin-bottom:20px;color: white;'>" + "<button class='btn btn-default' onclick=\"window.location.href='/all_files'\"> 查看上传文件 </button>" + "<button id='newdata' class='btn btn-default'" + "  onclick=\"window.location.href='/datafile'\">查看新增数据</button>" + "<button id='origindata' class='btn btn-default'" + " onclick=\"window.location.href='/origin_data'\">查看原始数据</button>" + "<button id='logdata' class='btn btn-default'" + " onclick=\"window.location.href='/log_management'\">日志管理</button>" + "<button class='btn btn-default' onclick=\"window.location.href='/suggest_edit'\">编辑标注</button>" + "</div>"
  //data:function(){
  //  return {
  //    title:"aaa"
  //  }
  //},
  //mounted:function(){ //相当于document.ready
  //   this.$set(this,"title",'bbb')
  //},
});

//# sourceMappingURL=sub-btn-compiled.js.map
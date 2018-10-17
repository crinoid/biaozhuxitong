var vm = new Vue({
  el: '#app',
  data: {
    total: 22,
    total_page: 3
  },
  components: {
    "pagebutton": {
      template: '<div style="padding: 20px 0;margin: 0 auto;width: 60%">' + '<ul class="pagination">' + '<li><a disabled="disabled" ref="prevBtn"">&laquo;</a></li>' + '<li name="page" v-for="page in page_arr"><a>' + '{{ page }}</a></li>' + '<li><a ref="nextBtn">&raquo;</a></li>' + '</ul></div>',
      data: function data() {
        return { page_arr: [1, 2, 3, 4, 5] };
      }
    },
    "total": {
      template: "<div>共{{ total }}条," + "{{ total_page }}页 </div>",
      data: function data() {
        return { total: 22, total_page: 3 };
      }
    }
  }
});

//# sourceMappingURL=test-compiled.js.map

//# sourceMappingURL=test-compiled-compiled.js.map
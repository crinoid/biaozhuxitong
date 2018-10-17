import _typeof from 'babel-runtime/helpers/typeof';
var vutils = new Vue({
  methods: {
    //a是否包含b字符串
    is_contain: function is_contain(a, b) {
      return a.indexOf(b);
    },
    has_element: function has_element(arr, value) {
      if ((typeof arr === 'undefined' ? 'undefined' : _typeof(arr)) == "object") {
        for (var i in arr) {
          if (arr[i] === value || arr[i] == value.toString()) {
            return true;
          }
        }
        return false;
      } else {
        for (var i = 0; i < arr.length; i++) {
          if (arr[i] === value || arr[i] == value.toString()) {
            return true;
          }
        }
        return false;
      }
    },
    jsonLength: function jsonLength(json2) {
      var jslength = 0;

      for (var js2 in json2) {
        jslength++;
      }
      return jslength;
    },
    deepCopy: function deepCopy(source) {
      var result = {};
      for (var key in source) {
        result[key] = _typeof(source[key]) === 'object' ? this.deepCopy(source[key]) : source[key];
      }
      return result;
    },
    removeByValue: function removeByValue(arr, val) {
      for (var i = 0; i < arr.length; i++) {
        if (arr[i] == val) {
          arr.splice(i, 1);
          break;
        }
      }
    },
    randomString: function randomString(len) {
      len = len || 8; //默认8位
      var $chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
      var maxPos = $chars.length;
      var pwd = '';
      for (i = 0; i < len; i++) {
        pwd += $chars.charAt(Math.floor(Math.random() * maxPos));
      }
      return pwd;
    },
    // 判断字典是否为空
    isEmptyObject: function isEmptyObject(obj) {
      for (var n in obj) {
        return false;
      }
      return true;
    }

  }
});

//# sourceMappingURL=utils-compiled.js.map
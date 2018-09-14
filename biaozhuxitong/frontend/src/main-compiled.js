import Vue from 'vue';
import App from './App';
import router from './router';

Vue.config.productionTip = false;

/* eslint-disable no-new */
new Vue({
  el: '#app',
  router: router,
  render: function render(h) {
    return h(App);
  }
});

//# sourceMappingURL=main-compiled.js.map
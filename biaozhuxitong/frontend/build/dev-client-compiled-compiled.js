/* eslint-disable */
'use strict';

require('eventsource-polyfill');
var hotClient = require('webpack-hot-middleware/client?noInfo=true&reload=true');

hotClient.subscribe(function (event) {
  if (event.action === 'reload') {
    window.location.reload();
  }
});

//# sourceMappingURL=dev-client-compiled.js.map

//# sourceMappingURL=dev-client-compiled-compiled.js.map
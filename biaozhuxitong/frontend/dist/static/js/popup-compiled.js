var prompt = function prompt(message, style, time) {
    style = style === undefined ? 'alert-success' : style;
    time = time === undefined ? 1200 : time;
    $("<div style='width:80px; text-align:center; margin:0 auto;position: relative;'>").appendTo('body').addClass('alert ' + style).html(message).fadeIn().delay(time).fadeOut();
};

// 成功提示
var success_prompt = function success_prompt(message, time) {
    prompt(message, 'alert-success', time);
};

//# sourceMappingURL=popup-compiled.js.map
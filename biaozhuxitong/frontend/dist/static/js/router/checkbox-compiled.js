function checkAllTable(obj, $tbr) {
  $tbr.find('input').prop('checked', $(obj).prop('checked'));
  /*并调整所有选中行的CSS样式*/
  if ($(obj).prop('checked')) {
    $tbr.find('input').parent().parent().addClass('warning');
  } else {
    $tbr.find('input').parent().parent().removeClass('warning');
  }
  /*阻止向上冒泡，以防再次触发点击操作*/
  //event.stopPropagation();
}

//点击一个checkbox
function selectItemTable(obj, $thr, $tbr, target_table) {
  $(obj).parent().parent().toggleClass('warning');
  $checkAll = $thr.find('input');
  // syn_item($(obj).parent().next().text().split("-")[0], target_table, $(obj).prop("checked"))
  /*如果已经被选中行的行数等于表格的数据行数，将全选框设为选中状态，否则设为未选中状态*/
  $checkAll.prop('checked', $tbr.find('input:checked').length == $tbr.length ? true : false);
  /*阻止向上冒泡，以防再次触发点击操作*/
  //event.stopPropagation();
}

//选择一个分词,对应的标注也选上
// function syn_item(term, tbr, state) {
//   $.each(tbr, function (i, item) {
//     if (i % 4 == 1) {
//       seg = item.innerText.split("-")[0]
//       if (seg == term) {
//         $(item).parent().find('td input').prop("checked", state)
//         $(item).parent().toggleClass('warning')
//       }
//     }
//   })
// }

//# sourceMappingURL=checkbox-compiled.js.map
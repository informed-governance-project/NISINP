document.querySelectorAll('.is-valid').forEach(function (element) {
    element.classList.remove('is-valid');
});


// initialize all tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl, {delay:200})
})


$('.select_so_standard').on( "click", function() {
  var $popup = $("#select_so_standard");
  var popup_url = '/securityobjectives/select_so_standard';

  $(".modal-dialog", $popup).load(popup_url, function () {
      $popup.modal("show");
  });
});

$('.import_so_declaration').on( "click", function() {
  var $popup = $("#import_so_declaration");
  var popup_url = '/securityobjectives/import';

  $(".modal-dialog", $popup).load(popup_url, function () {
      $popup.modal("show");
  });
});

document.querySelectorAll('.is-valid').forEach(function (element) {
    element.classList.remove('is-valid');
});


// initialize all tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl, {delay:200})
})

$(document).ready(function () {
  $('.create_so_declaration').on( "click", function() {
    var $popup = $("#create_so_declaration");
    var popup_url = '/securityobjectives/create';

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
})


window.check_task_status = function(){
  load_spinner()

  const url = '/task_status';
  const pollInterval = setInterval(() => {
      $.get(url, function (response) {
          if (response.status === "completed") {
              clearInterval(pollInterval);
              setTimeout(() => {
                  $('#loading-spinner').fadeOut().addClass('d-none');
              }, 100);
          }
      });
  }, 1000);
}

window.load_spinner = function(){
  $('#loading-spinner').removeClass('d-none').fadeIn();
}

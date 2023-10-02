document.querySelectorAll('.is-valid').forEach(function (element) {
    element.classList.remove('is-valid');
});


// initialize all tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl, {delay:200})
})

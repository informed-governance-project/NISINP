$(document).ready(function () {
    $('#language_selector').change(function () {
        $(this).closest('form').submit();
    });
});

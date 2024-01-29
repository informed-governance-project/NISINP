document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("language_selector").onchange(function () {
        document.getElementById("language_selector").parent().submit();
    })
});

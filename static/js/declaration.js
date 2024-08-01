// populate the value in selctpickers

const selectpickers = document.getElementsByClassName("selectpicker");

for(selectpicker of selectpickers) {
    var i;
    values = [];
    if (selectpicker.hasAttribute("id")){
        id = selectpicker.getAttribute("id")
        for (i = 0; i < selectpicker.length; i++) {
            if (selectpicker[i].hasAttribute("checked")) {
                if(selectpicker[i].value != ''){
                    values.push(selectpicker[i].value)
                }
            }
        }
        $('#'+id).selectpicker('val', values);
    }
}
$(document).ready(function () {
    $(".incident_detection_date").parent().on("dp.change", function (e) {
        if ( $('.incident_starting_date').parent().data("DateTimePicker")){
            $('.incident_starting_date').parent().data("DateTimePicker").clear();
            $('.incident_starting_date').parent().data("DateTimePicker").maxDate(e.date);
        }
    });

    let allTextarea = $('textarea');

    if (allTextarea.length > 0) {
        allTextarea.each(function() {
            if ($(this).prop('disabled')) $(this).attr('rows', '10');
        });

        allTextarea.on('focus', function() {
            if (!$(this).prop('disabled')) $(this).attr('rows', '10');
        });

        allTextarea.on('blur', function() {
            if (!$(this).prop('disabled')) $(this).attr('rows', '3');
        });
    }
});

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


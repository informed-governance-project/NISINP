function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function onChangeIncident(value, id) {
    const csrftoken = getCookie('csrftoken');
    let formdata = $(value).serialize();

    $.ajax({
        type: "POST",
        url: "incident/" + id,
        data: formdata,
        headers: {
            "X-CSRFToken": csrftoken
        },
        traditional: true,
        success: function (response) {
            let newReviewStatus = response.review_status;
            let incident_id = response.id;
            let $tdElement = $('#review_status_' + incident_id);
            let newClass = getReviewStatusClass(newReviewStatus);
            $tdElement.removeClass();
            $tdElement.addClass(newClass);
        },
        error: function (error) {
            console.log(error);
        }
    });
}

function onChangeWorkflowStatus(value,id,workflow_id) {
    const csrftoken = getCookie('csrftoken');

    let formdata = $(value).serialize();

    $.ajax({
        type: "POST",
        url: "incident/" + id + "?workflow_id=" + workflow_id,
        data: formdata,
        headers: {
            "X-CSRFToken": csrftoken
        },
        traditional: true,
        success: function (response) {
            let newReviewStatus = response.review_status;
            let workflow_id = response.id;
            let $tdElement = $('#workflow_review_status_' + workflow_id);
            let newClass = getReviewStatusClass(newReviewStatus);
            $tdElement.removeClass();
            $tdElement.addClass(newClass);
        },
        error: function (error) {
            console.log(error);
        }
    });
}

function getReviewStatusClass(reviewStatus) {
    switch (reviewStatus) {
        case "PASS":
            return "table-success";
        case "FAIL":
            return "table-danger";
        case "DELIV":
            return "table-info";
        case "OUT":
            return "table-dark";
        default:
            return "";
    }
}

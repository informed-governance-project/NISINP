$('#incidents-table').DataTable( {
    paging: false,
    searching: false,
    order: [[0, 'dsc']],
    columnDefs: [
        {
            targets: 0,
            type: 'date'
        },
        {
            targets: 6,
            orderable: false,
        },
        {
            targets: 7,
            orderable: false,
        },
        {
            targets: 8,
            orderable: false,
        },
    ]
});

$(document).ready(function () {
    $('.access_log').click(function() {
        var $popup = $("#access_log");
        var popup_url = 'access_log/' + $(this).data("incident-id");

        $(".modal-dialog", $popup).load(popup_url, function () {
            $popup.modal("show");
        });
    });
});

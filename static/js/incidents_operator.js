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
    $('.workflow_comment').on( "click", function() {
        let $this = $(this);
        let workflowComment = $this.data('workflow-comment');
        let $modalWorkflowComment = $('#modal-workflow-comment');
        $modalWorkflowComment.text(workflowComment);
    });
});

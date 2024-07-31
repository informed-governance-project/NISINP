$(document).ready(function () {
    $('.workflow_comment').on( "click", function() {
        let $this = $(this);
        let workflowComment = $this.data('workflow-comment');
        let $modalWorkflowComment = $('#modal-workflow-comment');
        $modalWorkflowComment.text(workflowComment);
    });
});

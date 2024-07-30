$(document).ready(function () {
    $('.access_log').on( "click", function() {
        var $popup = $("#access_log");
        var popup_url = 'access_log/' + $(this).data("incident-id");

        $(".modal-dialog", $popup).load(popup_url, function () {
            $popup.modal("show");
        });
    });

    $('.report_versions').on( "click", function() {
        let $this = $(this);
        let incidentRef = $this.data('report');
        let reportId = $this.data('incident-ref');
        let workflows = $this.data('workflows');
        let reviewUrlBase = $this.data('review-url');
        let downloadUrlBase = $this.data('download-url');
        let $modalReportName = $('#modal-report-name');
        let $modalincidentRef = $('#modal-incident-ref');
        let $modalWorkflowRows = $('#modal-workflow-rows');


        $modalReportName.text(reportId);
        $modalincidentRef.text(incidentRef);
        $modalWorkflowRows.empty();

        workflows.forEach(function(workflow) {
            let reviewUrl = reviewUrlBase + workflow.id;
            let downloadUrl = downloadUrlBase.replace('0', workflow.id);
            let date = new Date(workflow.timestamp);
            let formattedDate = date.toLocaleDateString('en-GB', {
                day: '2-digit',
                month: 'short',
                year: 'numeric'
            });
            let formattedTime = date.toLocaleTimeString('en-GB', {
                hour: '2-digit',
                minute: '2-digit'
            });
            let formattedDateTime = formattedDate + ', ' + formattedTime;

            let row = `
                <tr>
                    <td>${formattedDateTime}</td>
                    <td>
                        <a class="btn text-primary p-0 border-0" href="${reviewUrl}" title="Review">
                            <i class="bi bi-binoculars"></i>
                        </a>
                        <a class="btn text-secondary p-0 border-0" href="${downloadUrl}" title="Download">
                            <i class="bi bi-filetype-pdf"></i>
                        </a>
                    </td>
                </tr>
            `;
            $modalWorkflowRows.append(row);
        });
    });

    $('.delete_incident').on( "click", function() {
        let $this = $(this);
        let modalDeleteButton = $("#modal-delete-button");
        let deleteUrlBase = $this.data('delete-url');
        let incidentId = $this.data('incident-id');
        let deleteUrl = deleteUrlBase.replace('0', incidentId);
        modalDeleteButton.attr('href', deleteUrl);
    });
});

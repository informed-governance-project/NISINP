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

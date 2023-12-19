$('#incidents-table').DataTable( {
    paging: false,
    columnDefs: [
        {
            targets: 0,
            type: 'mydate'
        },
        {
            targets: 7,
            orderable: false,
        },
        {
            targets: 8,
            orderable: false,
        },
        {
            targets: 9,
            orderable: false,
        },
    ]
} );
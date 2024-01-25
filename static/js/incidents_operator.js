$('#incidents-table').DataTable( {
    paging: false,
    searching: false,
    order: [[0, 'mydate-desc']],
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
    ]
} );

Object.assign($.fn.DataTable.ext.oSort, {
    'mydate-asc': (a,b) => new Date(a) - new Date(b),
    'mydate-desc': (a,b) => new Date(b) - new Date(a)
  });

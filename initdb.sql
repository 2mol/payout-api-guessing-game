create table data (
    id integer primary key autoincrement,
    data text,
    has_been_broadcast bool default false
);

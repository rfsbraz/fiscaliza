-- Site views over a parlamento-aberto release. sync.py runs this file right after the
-- seating macros (seating.sql), so seated_on exists. Requests
-- read these instead of repeating the rules.

-- The day each legislature is read on: its last day once it has ended, the AR extract
-- date while it is open.
create or replace view legislature_days as
select
    legislature,
    legislature_id,
    start_date,
    end_date,
    extract_date,
    coalesce(end_date, extract_date) as ref_day,
    end_date is null as is_open
from legislatures;

-- The legislature the site shows by default: the open one, else the latest.
create or replace view current_legislature as
select * from legislature_days
order by is_open desc, start_date desc
limit 1;

-- seated_detail(d): seated_on(d) with each deputy's circle and parliamentary group on day d.
-- The group is the membership that covers d, else the person's latest one in that
-- legislature.
create or replace macro seated_detail(d) as table
select
    s.legislature,
    s.cadastro_id,
    s.deputy_id,
    s.circle_id,
    c.name as circle,
    s.situation,
    g.group_acronym
from seated_on(d) s
left join electoral_circles c
  on c.legislature = s.legislature and c.circle_id = s.circle_id
left join (
    select
        legislature,
        cadastro_id,
        group_acronym,
        row_number() over (
            partition by legislature, cadastro_id
            order by
                (start_date <= d::date and (end_date is null or end_date >= d::date)) desc,
                start_date desc
        ) as rn
    from group_memberships
) g
  on g.legislature = s.legislature and g.cadastro_id = s.cadastro_id and g.rn = 1;

-- deputy_current: who holds a seat in the current legislature on its reference day.
create or replace view deputy_current as
select *
from seated_detail((select ref_day from current_legislature))
where legislature = (select legislature from current_legislature);

-- party_seats: seats per parliamentary group in the current legislature.
create or replace view party_seats as
select
    c.legislature,
    c.group_acronym,
    g.name,
    count(*) as seats
from deputy_current c
left join parliamentary_groups g
  on g.legislature = c.legislature and g.group_acronym = c.group_acronym
group by all;

-- deputy_legislatures: one row per person and legislature in which they held a seat at some
-- point, with their latest situation, circle and group in it.
create or replace view deputy_legislatures as
with m as (
    select
        legislature,
        cadastro_id,
        arg_max(deputy_id, struct_pack(s := start_date, e := coalesce(end_date, date '9999-12-31'))) as deputy_id,
        arg_max(circle_id, struct_pack(s := start_date, e := coalesce(end_date, date '9999-12-31'))) as circle_id,
        arg_max(situation, struct_pack(s := start_date, e := coalesce(end_date, date '9999-12-31'))) as situation
    from mandates
    group by legislature, cadastro_id
    having bool_or(is_effective)
),
g as (
    select legislature, cadastro_id, arg_max(group_acronym, start_date) as group_acronym
    from group_memberships
    group by legislature, cadastro_id
)
select
    m.legislature,
    m.cadastro_id,
    m.deputy_id,
    m.circle_id,
    c.name as circle,
    m.situation,
    g.group_acronym,
    l.start_date as legislature_start,
    l.end_date as legislature_end,
    l.is_open
from m
join legislature_days l on l.legislature = m.legislature
left join electoral_circles c on c.legislature = m.legislature and c.circle_id = m.circle_id
left join g on g.legislature = m.legislature and g.cadastro_id = m.cadastro_id;

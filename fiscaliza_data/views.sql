-- Site views over a parlamento-aberto release. sync.py runs this file right after the
-- seating macros (the release's macros.sql, or seating.sql), so seated_on exists. Requests
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

-- deputy_vote_positions: one row per plenary vote and deputy seated on its day (the seating
-- rule), with their group that day and their position: the position the vote detail names
-- them with, else their group's position as a whole. Unknown (null) when the vote has no
-- published positions, or when the group split by counts (as in 2-PS) that the named deputies
-- do not account for, and the deputy is not named. The AR usually names the deputies behind a
-- count, so a count matched by as many named deputies of the group with that position does not
-- make the rest unknown. A table, not a view: it is millions of rows and requests read it by
-- deputy.
create or replace table deputy_vote_positions as
with plenary as (
    select vote_id, legislature, date from votes where body = 'plenary'
),
seated as (
    select s.day, s.legislature, s.cadastro_id
    from seated_during((select min(date) from plenary), (select max(date) from plenary)) s
    semi join (select distinct date from plenary) d on d.date = s.day
),
base as (
    select p.vote_id, p.legislature, p.date, s.cadastro_id
    from plenary p
    join seated s on s.day = p.date and s.legislature = p.legislature
),
-- The membership that covers the day, else the person's latest one in that legislature.
groups as (
    select b.vote_id, b.cadastro_id,
        arg_max(g.group_acronym, struct_pack(
            covers := g.start_date <= b.date and (g.end_date is null or g.end_date >= b.date),
            since := g.start_date
        )) as group_acronym
    from base b
    join group_memberships g on g.legislature = b.legislature and g.cadastro_id = b.cadastro_id
    group by b.vote_id, b.cadastro_id
),
named_counts as (
    select vote_id, group_code, position, count(*) as named
    from vote_deputy_dissents
    where body = 'plenary'
    group by vote_id, group_code, position
),
-- Deputies behind each group's counts that no named deputy accounts for.
unnamed as (
    select c.vote_id, c.group_code, sum(greatest(c.deputies - coalesce(n.named, 0), 0)) as unnamed
    from (
        select vote_id, group_code, position, sum(deputies) as deputies
        from vote_group_positions
        where body = 'plenary' and deputies is not null
        group by vote_id, group_code, position
    ) c
    left join named_counts n on n.vote_id = c.vote_id and n.group_code = c.group_code and n.position = c.position
    group by c.vote_id, c.group_code
),
whole as (
    select vote_id, group_code, any_value(position) as position
    from vote_group_positions
    where body = 'plenary' and deputies is null
    group by vote_id, group_code
    having count(*) = 1
),
named as (
    select vote_id, cadastro_id, any_value(position) as position
    from vote_deputy_dissents
    where body = 'plenary' and cadastro_id is not null
    group by vote_id, cadastro_id
)
select
    b.vote_id,
    b.legislature,
    b.date,
    b.cadastro_id,
    g.group_acronym,
    w.position as group_position,
    coalesce(u.unnamed, 0) > 0 as group_split,
    n.position is not null as named,
    case
        when n.position is not null then n.position
        when coalesce(u.unnamed, 0) = 0 then w.position
    end as position
from base b
left join groups g on g.vote_id = b.vote_id and g.cadastro_id = b.cadastro_id
left join whole w on w.vote_id = b.vote_id and w.group_code = g.group_acronym
left join unnamed u on u.vote_id = b.vote_id and u.group_code = g.group_acronym
left join named n on n.vote_id = b.vote_id and n.cadastro_id = b.cadastro_id;

-- vote_tallies: estimated favour, against, abstention and absent counts per plenary vote. Per
-- group seated that day and position: the larger of its count (as in 2-PS) and its named
-- deputies, since the count usually is the named deputies; the rest of its seated deputies
-- take the group's position as a whole. Complete when every seated group is accounted for that
-- way; incomplete votes (no detail, or a split with no position for the rest) should not be
-- shown as tallies. Seated is not present, so this is the margin implied by the group
-- positions, not a count on the day.
create or replace table vote_tallies as
with seats as (
    select vote_id, group_acronym, count(*) as seats
    from deputy_vote_positions
    group by vote_id, group_acronym
),
counts as (
    select vote_id, group_code, position, sum(deputies) as deputies
    from vote_group_positions
    where body = 'plenary' and deputies is not null
    group by vote_id, group_code, position
),
named as (
    select vote_id, group_code, position, count(*) as deputies
    from vote_deputy_dissents
    where body = 'plenary'
    group by vote_id, group_code, position
),
parts as (
    select
        coalesce(c.vote_id, n.vote_id) as vote_id,
        coalesce(c.group_code, n.group_code) as group_code,
        coalesce(c.position, n.position) as position,
        greatest(coalesce(c.deputies, 0), coalesce(n.deputies, 0)) as deputies
    from counts c
    full join named n on n.vote_id = c.vote_id and n.group_code = c.group_code and n.position = c.position
),
whole as (
    select vote_id, group_code, count(*) as whole_rows, any_value(position) as position
    from vote_group_positions
    where body = 'plenary' and deputies is null
    group by vote_id, group_code
),
per_group as (
    select
        s.vote_id,
        w.whole_rows,
        w.position as whole_position,
        s.seats - coalesce(sum(p.deputies), 0) as rest,
        coalesce(sum(p.deputies) filter (p.position = 'favour'), 0) as favour,
        coalesce(sum(p.deputies) filter (p.position = 'against'), 0) as against,
        coalesce(sum(p.deputies) filter (p.position = 'abstention'), 0) as abstention,
        coalesce(sum(p.deputies) filter (p.position = 'absent'), 0) as absent
    from seats s
    left join whole w on w.vote_id = s.vote_id and w.group_code = s.group_acronym
    left join parts p on p.vote_id = s.vote_id and p.group_code = s.group_acronym
    group by s.vote_id, s.group_acronym, s.seats, w.whole_rows, w.position
)
select
    vote_id,
    sum(favour + case when whole_rows = 1 and whole_position = 'favour' then rest else 0 end)::integer as favour,
    sum(against + case when whole_rows = 1 and whole_position = 'against' then rest else 0 end)::integer as against,
    sum(abstention + case when whole_rows = 1 and whole_position = 'abstention' then rest else 0 end)::integer
        as abstention,
    sum(absent + case when whole_rows = 1 and whole_position = 'absent' then rest else 0 end)::integer as absent,
    bool_and(coalesce(whole_rows = 1 and rest >= 0, false) or (coalesce(whole_rows, 0) = 0 and rest = 0)) as complete
from per_group
group by vote_id;

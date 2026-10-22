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

-- deputy_elections: one row per person and legislature in which they were elected or held a
-- seat: an effective period, or a Suspenso(Eleito) one (elected, with the mandate suspended for a
-- reason the data does not give). seated says whether they held the seat at some point in it.
-- situation, situation_start and situation_end are those of their latest period in it (latest
-- start, then the longer one), with their circle, and their latest group in it.
create or replace view deputy_elections as
with m as (
    -- The latest period as one struct: arg_max skips rows whose value is null, and an open
    -- period has a null end_date.
    select
        legislature,
        cadastro_id,
        arg_max(
            struct_pack(deputy_id, circle_id, situation, start_date, end_date),
            struct_pack(s := start_date, e := coalesce(end_date, date '9999-12-31'))
        ) as latest,
        bool_or(is_effective) as seated
    from mandates
    group by legislature, cadastro_id
    having bool_or(is_effective) or bool_or(situation = 'Suspenso(Eleito)')
),
g as (
    select legislature, cadastro_id, arg_max(group_acronym, start_date) as group_acronym
    from group_memberships
    group by legislature, cadastro_id
)
select
    m.legislature,
    m.cadastro_id,
    m.latest.deputy_id,
    m.latest.circle_id,
    c.name as circle,
    m.latest.situation,
    g.group_acronym,
    l.start_date as legislature_start,
    l.end_date as legislature_end,
    l.is_open,
    m.seated,
    m.latest.start_date as situation_start,
    m.latest.end_date as situation_end
from m
join legislature_days l on l.legislature = m.legislature
left join electoral_circles c on c.legislature = m.legislature and c.circle_id = m.latest.circle_id
left join g on g.legislature = m.legislature and g.cadastro_id = m.cadastro_id;

-- deputy_legislatures: the rows of deputy_elections where the person held a seat. Seated-day
-- figures (attendance, votes, time served, group counts) read this one.
create or replace view deputy_legislatures as
select * exclude (seated, situation_start, situation_end)
from deputy_elections
where seated;

-- deputy_vote_positions: one row per plenary vote and deputy seated on its day (the seating
-- rule), with their group that day and their position: the position the vote detail names
-- them with, else their group's position as a whole. Unknown (null) when the vote has no
-- published positions, or when the group split by counts (as in 2-PS) that the named deputies
-- do not account for, and the deputy is not named. The AR usually names the deputies behind a
-- count, so a count matched by as many named deputies of the group with that position does not
-- make the rest unknown. A table, not a view: it is millions of rows and requests read it by
-- deputy.
-- Built in steps, so no step holds the millions of rows at once: as one query it ran out of
-- memory on the 3 GB runner. _vote_day_seats holds the deputies seated on each plenary vote day
-- and _vote_day_groups their group that day: the membership that covers the day, else the
-- person's latest one in that legislature. Both are per day, not per vote.
create or replace temp table _vote_day_seats as
with plenary_days as (
    select distinct legislature, date from votes where body = 'plenary'
)
select s.day, s.legislature, s.cadastro_id
from seated_during((select min(date) from plenary_days), (select max(date) from plenary_days)) s
semi join plenary_days d on d.date = s.day and d.legislature = s.legislature;

create or replace temp table _vote_day_groups as
select s.legislature, s.day, s.cadastro_id,
    arg_max(g.group_acronym, struct_pack(
        covers := g.start_date <= s.day and (g.end_date is null or g.end_date >= s.day),
        since := g.start_date
    )) as group_acronym
from _vote_day_seats s
join group_memberships g on g.legislature = s.legislature and g.cadastro_id = s.cadastro_id
group by s.legislature, s.day, s.cadastro_id;

create or replace table deputy_vote_positions as
with base as (
    select p.vote_id, p.legislature, p.date, s.cadastro_id
    from votes p
    join _vote_day_seats s on s.day = p.date and s.legislature = p.legislature
    where p.body = 'plenary'
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
left join _vote_day_groups g on g.legislature = b.legislature and g.day = b.date and g.cadastro_id = b.cadastro_id
left join whole w on w.vote_id = b.vote_id and w.group_code = g.group_acronym
left join unnamed u on u.vote_id = b.vote_id and u.group_code = g.group_acronym
left join named n on n.vote_id = b.vote_id and n.cadastro_id = b.cadastro_id;

drop table _vote_day_groups;
drop table _vote_day_seats;

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

-- deputy_initiatives: one row per initiative and deputy who signed it.
create or replace view deputy_initiatives as
select distinct legislature, initiative_id, cadastro_id
from initiative_authors
where author_type = 'deputy' and cadastro_id is not null;

-- initiative_outcome: the outcome of each initiative that has one, from its plenary votes.
-- Decisive phases: final global vote, final global vote on a decree after a veto, global vote,
-- deliberation vote and final vote. On the latest day with a decisive vote, the initiative passed
-- when any of that day's votes passed (partly_approved when others that day did not, as with
-- point-by-point votes), and failed when every one of them was Rejeitado. Without a later
-- decisive vote, a Rejeitado on the latest generality vote also decides it. Everything else has
-- no row: lapsed, withdrawn or not voted yet, which the release does not tell apart.
create or replace view initiative_outcome as
with plenary as (
    select iv.initiative_legislature as legislature, iv.initiative_id, iv.phase, v.vote_id, v.date, v.result
    from initiative_votes iv
    join votes v on v.vote_id = iv.vote_id
    where iv.body = 'plenary'
),
decisive as (
    select *
    from plenary
    where phase in (
        'Votação final global', 'Votação final global decreto', 'Votação global', 'Votação Deliberação',
        'Votação final'
    )
),
last_day as (
    select d.legislature, d.initiative_id, d.date,
        bool_or(d.result = 'Aprovado') as any_approved,
        bool_and(d.result = 'Rejeitado') as all_rejected,
        bool_or(d.result is distinct from 'Aprovado') as any_other
    from decisive d
    where d.date = (
        select max(x.date) from decisive x where x.legislature = d.legislature and x.initiative_id = d.initiative_id
    )
    group by d.legislature, d.initiative_id, d.date
),
generality as (
    select legislature, initiative_id,
        arg_max(result, struct_pack(d := date, id := vote_id)) as result,
        max(date) as date
    from plenary
    where phase in ('Votação na generalidade', 'Votação generalidade decreto')
    group by legislature, initiative_id
),
decided as (
    select
        coalesce(f.legislature, g.legislature) as legislature,
        coalesce(f.initiative_id, g.initiative_id) as initiative_id,
        case
            when f.any_approved then 'Aprovado'
            when f.all_rejected then 'Rejeitado'
            when g.result = 'Rejeitado' and (f.date is null or g.date > f.date) then 'Rejeitado'
        end as result,
        coalesce(f.any_approved and f.any_other, false) as partly_approved,
        case
            when f.any_approved or f.all_rejected then 'final'
            when g.result = 'Rejeitado' and (f.date is null or g.date > f.date) then 'generality'
        end as decided_by,
        case when f.any_approved or f.all_rejected then f.date else g.date end as decided_on
    from last_day f
    full join generality g on g.legislature = f.legislature and g.initiative_id = f.initiative_id
)
select * from decided where result is not null;

-- initiative_signing: how each projeto de lei, de resolução or de deliberação signed by deputies
-- was signed. 'outros_grupos' when its deputies sat for more than one group; otherwise
-- 'grupo_parlamentar' when they include every deputy of their group seated on the day it was
-- submitted (a group of one seat always does), else 'subscricao_restrita'. The AR lists a
-- group's deputies as authors of its initiatives, so this shows how a deputy signs, not who
-- wrote the initiative.
create or replace view initiative_signing as
with authors as (
    select a.legislature, a.initiative_id, i.first_event_date as day,
        count(distinct a.cadastro_id) as signatories,
        count(distinct a.group_code) as groups,
        any_value(a.group_code) as group_code
    from initiative_authors a
    join initiatives i on i.legislature = a.legislature and i.initiative_id = a.initiative_id
    where a.author_type = 'deputy' and a.cadastro_id is not null and i.type_code in ('J', 'R', 'D')
    group by a.legislature, a.initiative_id, i.first_event_date
),
seated as (
    select a.legislature, a.initiative_id, count(distinct m.cadastro_id) as seated
    from authors a
    join mandates m
      on m.legislature = a.legislature and m.is_effective
     and m.start_date <= a.day and coalesce(m.end_date, date '9999-12-31') >= a.day
    join group_memberships g
      on g.legislature = m.legislature and g.cadastro_id = m.cadastro_id and g.group_acronym = a.group_code
     and g.start_date <= a.day and coalesce(g.end_date, date '9999-12-31') >= a.day
    where a.groups = 1
    group by a.legislature, a.initiative_id
)
select
    a.legislature,
    a.initiative_id,
    a.signatories,
    s.seated as group_seated,
    case
        when a.groups > 1 then 'outros_grupos'
        when s.seated > 0 and a.signatories >= s.seated then 'grupo_parlamentar'
        when s.seated > a.signatories then 'subscricao_restrita'
    end as kind
from authors a
left join seated s on s.legislature = a.legislature and s.initiative_id = a.initiative_id;

-- deputy_seat_days: per person and legislature they held a seat in, their group (as in
-- deputy_legislatures), the days they were seated (effective mandates, counted up to the
-- legislature's reference day, as for the deputy page) and the legislature's days to that day.
create or replace view deputy_seat_days as
with seats as (
    select m.legislature, m.cadastro_id,
        sum(greatest(date_diff('day', m.start_date, least(coalesce(m.end_date, l.ref_day), l.ref_day)), 0)) as days
    from mandates m
    join legislature_days l on l.legislature = m.legislature
    where m.is_effective
    group by m.legislature, m.cadastro_id
)
select
    dl.legislature,
    dl.cadastro_id,
    dl.group_acronym,
    s.days,
    date_diff('day', l.start_date, l.ref_day) as legislature_days,
    l.is_open
from deputy_legislatures dl
join seats s on s.legislature = dl.legislature and s.cadastro_id = dl.cadastro_id
join legislature_days l on l.legislature = dl.legislature;

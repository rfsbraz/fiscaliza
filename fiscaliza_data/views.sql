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

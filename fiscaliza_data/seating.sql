-- Fiscaliza's seating rule, owned and tested in this repo.

-- The seating rule, in one place. The vote_group_positions mart uses seated_during, so
-- build.py creates these macros right after the mandates table, before the marts.

-- seated_by_period_during(d0, d1): for each day from d0 to d1 and each person, the period
-- that decides whether they are seated at the end of that day, before swap days are
-- handled. AR situation periods can overlap on a handover day (for example an Efetivo and
-- a Suspenso period that both cover 2025-06-05). The latest-starting period covering the
-- day wins; on a tie, the longer one; on a tie in both dates, the effective one (swap days
-- below then decide who holds the seat).
create or replace macro seated_by_period_during(d0, d1) as table
select * exclude (rn)
from (
    select
        dd.day,
        m.*,
        row_number() over (
            partition by dd.day, m.legislature, m.cadastro_id
            order by
                m.start_date desc,
                coalesce(m.end_date, date '9999-12-31') desc,
                m.is_effective desc
        ) as rn
    from (select unnest(generate_series(d0::date, d1::date, interval 1 day))::date as day) dd
    join mandates m
      on m.start_date <= dd.day and (m.end_date is null or m.end_date >= dd.day)
)
where rn = 1 and is_effective;

-- seated_during(d0, d1): deputies holding a seat at the end of each day from d0 to d1,
-- one row per day and deputy.
-- Swap days: AR dates are inclusive, so on the day one deputy hands a seat to another,
-- both periods cover the day and the circle shows one deputy too many. At the end of the
-- day the incoming deputy holds the seat. A period is outgoing on day d when it ends on d
-- and the person has no effective period starting on d + 1. Incoming means starting an
-- effective period on d after not being seated on d - 1. A swap shows as a one-day spike:
-- the circle has more deputies on d than on both d - 1 and d + 1. In each circle,
-- outgoing periods do not count, up to the smaller of that spike and the number of
-- incoming people, earliest start first. A circle that fills a vacancy on d has no spike,
-- so its outgoing periods still count. Who replaced whom is not used, because the source
-- does not record it.
create or replace macro seated_during(d0, d1) as table
with periods as (select * from seated_by_period_during(d0::date - 1, d1::date + 1)),
today as (select * from periods where day between d0::date and d1::date),

circle_counts as (
    select legislature, circle_id, day, count(*) as n
    from periods
    group by all
),

-- How far each circle's count on d rises above both d - 1 and d + 1.
spike as (
    select
        t.legislature,
        t.circle_id,
        t.day,
        least(t.n - coalesce(y.n, 0), t.n - coalesce(n.n, 0)) as n
    from circle_counts t
    left join circle_counts y
      on y.legislature = t.legislature and y.circle_id = t.circle_id and y.day = t.day - 1
    left join circle_counts n
      on n.legislature = t.legislature and n.circle_id = t.circle_id and n.day = t.day + 1
    where t.day between d0::date and d1::date
),

incoming as (
    select t.legislature, t.circle_id, t.day, count(*) as n
    from today t
    where t.start_date = t.day
      and not exists (
          select 1 from periods y
          where y.legislature = t.legislature
            and y.cadastro_id = t.cadastro_id
            and y.day = t.day - 1
      )
    group by all
),

outgoing as (
    select
        t.legislature,
        t.cadastro_id,
        t.circle_id,
        t.day,
        row_number() over (
            partition by t.legislature, t.circle_id, t.day order by t.start_date, t.cadastro_id
        ) as k
    from today t
    where t.end_date = t.day
      and not exists (
          select 1 from mandates n
          where n.legislature = t.legislature
            and n.cadastro_id = t.cadastro_id
            and n.is_effective
            and n.start_date = t.day + 1
      )
),

dropped as (
    select o.legislature, o.cadastro_id, o.day
    from outgoing o
    join spike g using (legislature, circle_id, day)
    join incoming i using (legislature, circle_id, day)
    where o.k <= least(g.n, i.n)
)

select t.day, t.legislature, t.cadastro_id, t.deputy_id, t.circle_id, t.situation
from today t
anti join dropped x using (legislature, cadastro_id, day);

-- seated_on(d): deputies holding a seat at the end of day d.
create or replace macro seated_on(d) as table
select legislature, cadastro_id, deputy_id, circle_id, situation
from seated_during(d, d);

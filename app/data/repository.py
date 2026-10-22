"""All SQL the site runs, one function per question, returning plain rows.

Every function takes a DuckDB cursor on the live file (see connection.py) and returns
dicts or lists of dicts. The site views and tables it reads (legislature_days,
current_legislature, seated_detail, deputy_current, deputy_legislatures, deputy_vote_positions,
vote_tallies) are created at sync time by fiscaliza_data/views.sql. Values are always bound
parameters; the only SQL put together in Python is shared fixed fragments.
"""


def _rows(con, sql, params=()):
    cur = con.execute(sql, params if isinstance(params, dict) else list(params))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def _one(con, sql, params=()):
    rows = _rows(con, sql, params)
    return rows[0] if rows else None


def meta(con):
    """Tag, schema version, source_updated, data commit and sync time of the live file."""
    # synced_at is a timestamp with time zone; read as text so no tz library is needed.
    return _one(
        con, "select tag, schema_version, source_updated, data_commit, synced_at::varchar as synced_at from _meta"
    )


def current_legislature(con):
    return _one(con, "select * from current_legislature")


def legislature(con, name):
    return _one(con, "select * from legislature_days where legislature = ?", [name])


def legislatures(con):
    """Every legislature, newest first, with the number of people who held a seat in it."""
    return _rows(
        con,
        """
        select l.*, count(dl.cadastro_id) as people_seated
        from legislature_days l
        left join deputy_legislatures dl on dl.legislature = l.legislature
        group by all
        order by l.start_date desc
        """,
    )


def seats_by_group(con, legislature, day):
    """Seats per parliamentary group on a day, largest first."""
    return _rows(
        con,
        """
        select s.group_acronym, g.name, count(*) as seats
        from seated_detail(?::date) s
        left join parliamentary_groups g
          on g.legislature = s.legislature and g.group_acronym = s.group_acronym
        where s.legislature = ?
        group by all
        order by seats desc, s.group_acronym
        """,
        [day, legislature],
    )


def seats_by_circle(con, legislature, day):
    """Seats per electoral circle on a day, largest first."""
    return _rows(
        con,
        """
        select circle, count(*) as seats
        from seated_detail(?::date)
        where legislature = ?
        group by all
        order by seats desc, circle
        """,
        [day, legislature],
    )


def people_seated(con, legislature):
    """People who held a seat at some point in the legislature."""
    return con.execute("select count(*) from deputy_legislatures where legislature = ?", [legislature]).fetchone()[0]


def groups(con, legislature):
    """Parliamentary groups of a legislature."""
    return _rows(
        con,
        "select group_acronym, name from parliamentary_groups where legislature = ? order by group_acronym",
        [legislature],
    )


def deputies_page(con, current, legislature=None, current_only=True, search=None, limit=20, offset=0):
    """People who held a seat, one row each: in ``legislature`` if given, else in the current
    legislature if ``current_only``, else in any. ``search`` matches the parliamentary or full
    name, ignoring case and accents. Seated people come first, then the rest of the current
    legislature, then by latest legislature and name. Each row carries ``total`` (people
    matched) and ``records`` (their person-legislature rows)."""
    return _rows(
        con,
        """
        with people as (
            select
                cadastro_id,
                count(*) as legislatures,
                max(legislature_start) as last_start,
                bool_or(legislature = $current) as in_current
            from deputy_legislatures
            where $legislature is null or legislature = $legislature
            group by cadastro_id
            having not $current_only or $legislature is not null or bool_or(legislature = $current)
        ),
        matched as (
            select p.*, d.parliamentary_name, d.full_name, d.profession,
                   p.cadastro_id in (select cadastro_id from deputy_current) as is_seated
            from people p
            join deputies d on d.cadastro_id = p.cadastro_id
            where $search is null
               or contains(strip_accents(lower(d.parliamentary_name)), strip_accents(lower($search)))
               or contains(strip_accents(lower(d.full_name)), strip_accents(lower($search)))
        )
        select *, count(*) over () as total, sum(legislatures) over () as records
        from matched
        order by is_seated desc, in_current desc, last_start desc, parliamentary_name, cadastro_id
        limit $limit offset $offset
        """,
        {
            "current": current,
            "legislature": legislature,
            "current_only": current_only,
            "search": search or None,
            "limit": limit,
            "offset": offset,
        },
    )


def deputies_count(con, current, legislature=None, current_only=True, search=None):
    """Total people and person-legislature rows for an empty page of deputies_page."""
    row = _one(
        con,
        """
        with people as (
            select cadastro_id, count(*) as legislatures
            from deputy_legislatures
            where $legislature is null or legislature = $legislature
            group by cadastro_id
            having not $current_only or $legislature is not null or bool_or(legislature = $current)
        )
        select count(*) as total, coalesce(sum(legislatures), 0) as records
        from people p
        join deputies d on d.cadastro_id = p.cadastro_id
        where $search is null
           or contains(strip_accents(lower(d.parliamentary_name)), strip_accents(lower($search)))
           or contains(strip_accents(lower(d.full_name)), strip_accents(lower($search)))
        """,
        {"current": current, "legislature": legislature, "current_only": current_only, "search": search or None},
    )
    return row["total"], row["records"]


def careers(con, cadastro_ids):
    """Every legislature each person held a seat in, oldest first, with their latest
    situation, circle and group in it."""
    if not cadastro_ids:
        return []
    return _rows(
        con,
        """
        select * from deputy_legislatures
        where list_contains(?, cadastro_id)
        order by cadastro_id, legislature_start
        """,
        [list(cadastro_ids)],
    )


def groups_served(con, cadastro_ids):
    """Each person's parliamentary groups, in the order they first joined them."""
    if not cadastro_ids:
        return []
    return _rows(
        con,
        """
        select cadastro_id, group_acronym, min(start_date) as first_start
        from group_memberships
        where list_contains(?, cadastro_id)
        group by all
        order by cadastro_id, first_start, group_acronym
        """,
        [list(cadastro_ids)],
    )


def coalition_rows(con, coalition=None):
    """The coalitions seed, one row per legislature, list and group, with the legislature's
    dates. ``coalition`` limits it to one coalition by its short name."""
    return _rows(
        con,
        """
        select c.legislature, c.coalition, c.ballot_acronym, c.coalition_name, c.group_code,
               coalesce(g.name, c.group_name) as group_name,
               l.start_date, l.end_date, l.ref_day, l.is_open
        from coalitions c
        join legislature_days l on l.legislature = c.legislature
        left join parliamentary_groups g
          on g.legislature = c.legislature and g.group_acronym = c.group_code
        where ? is null or c.coalition = ?
        order by c.coalition, l.start_date, c.ballot_acronym, c.group_code
        """,
        [coalition, coalition],
    )


def seated_in_groups(con, legislature, day, group_acronyms):
    """Deputies seated on a day in any of the given groups, by name."""
    return _rows(
        con,
        """
        select s.cadastro_id, s.deputy_id, s.circle, s.group_acronym, d.parliamentary_name, d.full_name
        from seated_detail(?::date) s
        join deputies d on d.cadastro_id = s.cadastro_id
        where s.legislature = ? and list_contains(?, s.group_acronym)
        order by d.parliamentary_name, s.cadastro_id
        """,
        [day, legislature, list(group_acronyms)],
    )


# Voting analytics (F16, F17, F19, F25 to F29). deputy_vote_positions and vote_tallies are
# tables built at sync time (views.sql). Group positions "as a whole" are the rows of
# vote_group_positions with no deputy count; a group with two such rows on one vote is
# treated as having no single position.

CAST = ("favour", "against", "abstention")
DECISIVE_PHASES = (
    "Votação final global",
    "Votação final global decreto",
    "Votação global",
    "Votação Deliberação",
    "Votação final",
)
GENERALITY_PHASES = ("Votação na generalidade", "Votação generalidade decreto")

_GROUP_POSITIONS = """
    select vote_id, group_code, any_value(position) as position
    from vote_group_positions
    where body = 'plenary' and legislature = $legislature and deputies is null
    group by vote_id, group_code
    having count(*) = 1
"""
# The same for every legislature at once.
_ALL_GROUP_POSITIONS = """
    select legislature, vote_id, group_code, any_value(position) as position
    from vote_group_positions
    where body = 'plenary' and deputies is null
    group by legislature, vote_id, group_code
    having count(*) = 1
"""


def deputy_votes(con, cadastro_ids):
    """Every plenary vote each person was seated for, per legislature and oldest first, with
    their group that day, the group's position as a whole and theirs (null when unknown)."""
    return _rows(
        con,
        """
        select cadastro_id, legislature, vote_id, date, group_acronym, group_position, position, named
        from deputy_vote_positions
        where cadastro_id in (select unnest(?))
        order by cadastro_id, legislature, date, vote_id
        """,
        [list(cadastro_ids)],
    )


def deputy_group_agreement(con, cadastro_ids):
    """Per person and legislature, for each other group: the votes where the deputy and that
    group as a whole both cast a vote (favour, against or abstention), and how many of them match."""
    return _rows(
        con,
        f"""
        with mine as (
            select cadastro_id, legislature, vote_id, group_acronym, position
            from deputy_vote_positions
            where cadastro_id in (select unnest($cadastro_ids)) and list_contains($cast, position)
        ),
        groups as ({_ALL_GROUP_POSITIONS})
        select m.cadastro_id, m.legislature, g.group_code as group_acronym,
               count(*) as total_votes,
               count(*) filter (g.position = m.position) as aligned_votes
        from mine m
        join groups g
          on g.legislature = m.legislature and g.vote_id = m.vote_id and g.group_code is distinct from m.group_acronym
        where list_contains($cast, g.position)
        group by m.cadastro_id, m.legislature, g.group_code
        order by m.cadastro_id, m.legislature, g.group_code
        """,  # noqa: S608 - a fixed SQL fragment, values are bound
        {"cadastro_ids": list(cadastro_ids), "cast": list(CAST)},
    )


def deputy_close_votes(con, cadastro_ids, margin):
    """Per person and legislature, the plenary votes they have a known position on whose tally
    is complete and decided by ``margin`` or fewer (favour minus against), newest first."""
    return _rows(
        con,
        """
        select p.cadastro_id, p.legislature, p.vote_id, p.position, t.favour, t.against, t.abstention
        from deputy_vote_positions p
        join vote_tallies t on t.vote_id = p.vote_id
        where p.cadastro_id in (select unnest(?)) and p.position is not null
          and t.complete and abs(t.favour - t.against) <= ?
        order by p.cadastro_id, p.legislature, p.date desc, p.vote_id desc
        """,
        [list(cadastro_ids), margin],
    )


def votes_by_id(con, vote_ids):
    """Date, description and result of the given votes."""
    if not vote_ids:
        return []
    return _rows(
        con,
        "select vote_id, date, description, result from votes where vote_id in (select unnest(?))",
        [list(vote_ids)],
    )


def whole_group_positions(con, vote_ids):
    """Each group's position as a whole on the given votes."""
    if not vote_ids:
        return []
    return _rows(
        con,
        """
        select vote_id, group_code, any_value(position) as position
        from vote_group_positions
        where body = 'plenary' and deputies is null and vote_id in (select unnest(?))
        group by vote_id, group_code
        having count(*) = 1
        order by vote_id, group_code
        """,
        [list(vote_ids)],
    )


def group(con, legislature, group_acronym):
    return _one(
        con,
        "select group_acronym, name from parliamentary_groups where legislature = ? and group_acronym = ?",
        [legislature, group_acronym],
    )


def group_monthly_votes(con, legislature, group_acronym):
    """Per month, the plenary votes the group cast as a whole, by position."""
    return _rows(
        con,
        f"""
        with groups as ({_GROUP_POSITIONS})
        select strftime(v.date, '%Y-%m') as month,
               count(*) as total,
               count(*) filter (g.position = 'favour') as favour,
               count(*) filter (g.position = 'against') as against,
               count(*) filter (g.position = 'abstention') as abstention
        from groups g
        join votes v on v.vote_id = g.vote_id
        where g.group_code = $group and list_contains($cast, g.position)
        group by month
        order by month
        """,  # noqa: S608 - a fixed SQL fragment, values are bound
        {"legislature": legislature, "group": group_acronym, "cast": list(CAST)},
    )


_GROUP_INITIATIVES = """
    select distinct i.legislature, i.initiative_id, i.type_code, i.type, i.first_event_date
    from initiatives i
    join initiative_authors a on a.legislature = i.legislature and a.initiative_id = i.initiative_id
    where i.legislature = $legislature and a.group_code = $group and a.author_type in ('group', 'deputy')
"""


def group_monthly_initiatives(con, legislature, group_acronym):
    """Per month of submission, the initiatives the group or its deputies signed."""
    return _rows(
        con,
        f"""
        select strftime(first_event_date, '%Y-%m') as month, count(*) as initiatives
        from ({_GROUP_INITIATIVES})
        where first_event_date is not null
        group by month
        order by month
        """,  # noqa: S608 - a fixed SQL fragment, values are bound
        {"legislature": legislature, "group": group_acronym},
    )


def group_initiative_outcomes(con, legislature, group_acronym):
    """Per initiative type, the initiatives the group or its deputies signed and their
    outcomes. On the latest day with a decisive plenary vote, an initiative passed when any
    vote passed (partly when others that day did not, as with point-by-point votes) and
    failed when all were Rejeitado. Without a later decisive vote, a Rejeitado on the latest
    generality vote also decides it. The rest has no outcome in the release (lapsed,
    withdrawn or not voted yet)."""
    return _rows(
        con,
        f"""
        with mine as ({_GROUP_INITIATIVES}),
        plenary as (
            select iv.initiative_id, iv.phase, v.vote_id, v.date, v.result
            from initiative_votes iv
            join votes v on v.vote_id = iv.vote_id
            join mine m on m.initiative_id = iv.initiative_id
            where iv.body = 'plenary' and iv.initiative_legislature = $legislature
        ),
        decisive as (select * from plenary where list_contains($decisive, phase)),
        last_day as (
            select d.initiative_id, d.date,
                bool_or(d.result = 'Aprovado') as any_approved,
                bool_and(d.result = 'Rejeitado') as all_rejected,
                bool_or(d.result is distinct from 'Aprovado') as any_other
            from decisive d
            where d.date = (select max(x.date) from decisive x where x.initiative_id = d.initiative_id)
            group by d.initiative_id, d.date
        ),
        generality as (
            select initiative_id,
                arg_max(result, struct_pack(d := date, id := vote_id)) as result,
                max(date) as date
            from plenary
            where list_contains($generality, phase)
            group by initiative_id
        ),
        outcomes as (
            select m.type_code, m.type,
                case
                    when f.any_approved then 'approved'
                    when f.all_rejected then 'rejected'
                    when g.result = 'Rejeitado' and (f.date is null or g.date > f.date) then 'rejected'
                end as outcome,
                coalesce(f.any_approved and f.any_other, false) as partly
            from mine m
            left join last_day f on f.initiative_id = m.initiative_id
            left join generality g on g.initiative_id = m.initiative_id
        )
        select type_code, min(type) as type,
               count(*) as initiated,
               count(*) filter (outcome = 'approved') as approved,
               count(*) filter (partly) as partly_approved,
               count(*) filter (outcome = 'rejected') as rejected
        from outcomes
        group by type_code
        order by type_code
        """,  # noqa: S608 - fixed SQL fragments, values are bound
        {
            "legislature": legislature,
            "group": group_acronym,
            "decisive": list(DECISIVE_PHASES),
            "generality": list(GENERALITY_PHASES),
        },
    )


def group_cohesion_by_type(con, legislature, group_acronym):
    """Per initiative type, the plenary votes on initiatives of that type where the group
    cast a vote as a whole, and how many of them had no deputy of the group, named or
    counted, voting another way. Being absent does not count as voting another way."""
    return _rows(
        con,
        f"""
        with mine as (
            select * from ({_GROUP_POSITIONS})
            where group_code = $group and list_contains($cast, position)
        ),
        broke as (
            select p.vote_id
            from vote_group_positions p
            join mine m on m.vote_id = p.vote_id
            where p.body = 'plenary' and p.group_code = $group and p.deputies is not null
              and p.position <> 'absent' and p.position <> m.position
            union
            select d.vote_id
            from vote_deputy_dissents d
            join mine m on m.vote_id = d.vote_id
            where d.body = 'plenary' and d.group_code = $group
              and d.position <> 'absent' and d.position <> m.position
        ),
        typed as (
            select distinct iv.vote_id, i.type_code, i.type
            from initiative_votes iv
            join initiatives i on i.legislature = iv.initiative_legislature and i.initiative_id = iv.initiative_id
            where iv.body = 'plenary'
        )
        select t.type_code, min(t.type) as type,
               count(*) as total_votes,
               count(*) filter (m.vote_id not in (select vote_id from broke)) as cohesive_votes
        from mine m
        join typed t on t.vote_id = m.vote_id
        group by t.type_code
        order by total_votes desc, t.type_code
        """,  # noqa: S608 - fixed SQL fragments, values are bound
        {"legislature": legislature, "group": group_acronym, "cast": list(CAST)},
    )


def group_agreement(con, legislature, group_acronym):
    """For each other group, the plenary votes where both groups cast a vote as a whole,
    and how many of them match."""
    return _rows(
        con,
        f"""
        with groups as (select * from ({_GROUP_POSITIONS}) where list_contains($cast, position))
        select o.group_code as group_acronym,
               count(*) as total_votes,
               count(*) filter (o.position = m.position) as aligned_votes
        from groups m
        join groups o on o.vote_id = m.vote_id and o.group_code <> m.group_code
        where m.group_code = $group
        group by o.group_code
        order by o.group_code
        """,  # noqa: S608 - a fixed SQL fragment, values are bound
        {"legislature": legislature, "group": group_acronym, "cast": list(CAST)},
    )


def group_activity(con, legislature, group_acronym):
    """Initiatives the group or its deputies signed, interventions by its deputies and
    plenary votes where it or some of its deputies cast a vote, in the legislature."""
    return _one(
        con,
        f"""
        select
            (select count(*) from ({_GROUP_INITIATIVES})) as initiatives,
            (select count(*) from interventions
             where legislature = $legislature and group_acronym = $group and speaker_kind = 'deputy')
                as interventions,
            (select count(distinct vote_id) from vote_group_positions
             where body = 'plenary' and legislature = $legislature and group_code = $group
               and position <> 'absent') as votes
        """,  # noqa: S608 - a fixed SQL fragment, values are bound
        {"legislature": legislature, "group": group_acronym},
    )


# Agenda page (S8)
def group_name(con, group_acronym):
    """The group's name in the latest legislature that lists it, or None if no legislature does."""
    row = _one(
        con,
        """
        select g.name
        from parliamentary_groups g
        join legislature_days l on l.legislature = g.legislature
        where g.group_acronym = ?
        order by l.start_date desc
        limit 1
        """,
        [group_acronym],
    )
    return row["name"] if row else None


def group_service(con, group_acronym, legislature=None):
    """One row per person and legislature in which they held a seat and sat for the group,
    with their circle in it and their register details. ``legislature`` limits it to one."""
    return _rows(
        con,
        """
        select dl.legislature, dl.cadastro_id, dl.circle, dl.legislature_start, dl.legislature_end,
               d.parliamentary_name, d.full_name, d.profession
        from deputy_legislatures dl
        join deputies d on d.cadastro_id = dl.cadastro_id
        where ($legislature is null or dl.legislature = $legislature)
          and exists (
            select 1 from group_memberships g
            where g.legislature = dl.legislature and g.cadastro_id = dl.cadastro_id
              and g.group_acronym = $group
          )
        order by dl.cadastro_id, dl.legislature_start
        """,
        {"group": group_acronym, "legislature": legislature},
    )


def group_seated(con, legislature, day, group_acronym):
    """The group's deputies seated on a day, with sex, birth date, profession, circle and the
    number of legislatures they held a seat in up to and including this one."""
    return _rows(
        con,
        """
        select s.cadastro_id, s.circle, d.parliamentary_name, d.sex, d.birth_date, d.profession,
               (select count(*) from deputy_legislatures dl
                where dl.cadastro_id = s.cadastro_id
                  and dl.legislature_start <= (select start_date from legislature_days where legislature = $leg)
               ) as legislatures_served
        from seated_detail($day::date) s
        join deputies d on d.cadastro_id = s.cadastro_id
        where s.legislature = $leg and s.group_acronym = $group
        order by s.cadastro_id
        """,
        {"leg": legislature, "day": day, "group": group_acronym},
    )


# Deputy page (S5)


# The deputy page reads these for a set of people at once (app.data.deputy_rows): each returns
# rows for every person in ``cadastro_ids``, carrying their cadastro_id.


def deputies_by_id(con, cadastro_ids):
    return _rows(con, "select * from deputies where cadastro_id in (select unnest(?))", [list(cadastro_ids)])


def seated(con, cadastro_ids):
    """Which of the people are seated now."""
    return {
        r[0]
        for r in con.execute(
            "select distinct cadastro_id from deputy_current where cadastro_id in (select unnest(?))",
            [list(cadastro_ids)],
        ).fetchall()
    }


def seat_periods(con, cadastro_ids):
    """Per person and legislature they held a seat in, oldest first: the first day and the last
    day of their effective mandates (null while still seated in an open legislature) and the days
    seated, counted up to the legislature's reference day."""
    return _rows(
        con,
        """
        select
            m.cadastro_id,
            m.legislature,
            min(m.start_date) as seat_start,
            case when l.is_open and bool_or(m.end_date is null) then null
                 else max(least(coalesce(m.end_date, l.ref_day), l.ref_day)) end as seat_end,
            sum(greatest(date_diff('day', m.start_date, least(coalesce(m.end_date, l.ref_day), l.ref_day)), 0))
                as days
        from mandates m
        join legislature_days l on l.legislature = m.legislature
        where m.cadastro_id in (select unnest(?)) and m.is_effective
        group by m.cadastro_id, m.legislature, l.is_open, l.start_date
        order by m.cadastro_id, l.start_date
        """,
        [list(cadastro_ids)],
    )


def group_names(con, legislatures):
    """{(legislature, group acronym): name} for the groups of the given legislatures."""
    rows = _rows(
        con,
        "select legislature, group_acronym, name from parliamentary_groups where list_contains(?, legislature)",
        [list(legislatures)],
    )
    return {(r["legislature"], r["group_acronym"]): r["name"] for r in rows}


def deputy_activity_by_legislature(con, cadastro_ids):
    """Per person and legislature: initiatives the person signed and their plenary interventions."""
    return _rows(
        con,
        """
        with ini as (
            select cadastro_id, legislature, count(*) as initiatives
            from deputy_initiatives
            where cadastro_id in (select unnest($cads))
            group by cadastro_id, legislature
        ),
        itv as (
            select cadastro_id, legislature, count(*) as interventions
            from interventions
            where cadastro_id in (select unnest($cads))
            group by cadastro_id, legislature
        )
        select
            coalesce(ini.cadastro_id, itv.cadastro_id) as cadastro_id,
            coalesce(ini.legislature, itv.legislature) as legislature,
            coalesce(ini.initiatives, 0) as initiatives,
            coalesce(itv.interventions, 0) as interventions
        from ini
        full join itv on itv.cadastro_id = ini.cadastro_id and itv.legislature = ini.legislature
        """,
        {"cads": list(cadastro_ids)},
    )


# Projetos de lei, de resolução and de deliberação: the initiatives with an approval rate and a
# signing pattern. The other types are counted only.
RATED_TYPES = ("J", "R", "D")


def deputy_outcomes(con, cadastro_ids):
    """Per person, legislature (oldest first) and type of projeto they signed: how many, how
    many passed (and of those, partly), and how many failed, per initiative_outcome."""
    return _rows(
        con,
        """
        select
            di.cadastro_id,
            di.legislature,
            i.type_code,
            any_value(i.type) as type,
            count(*) as total,
            count(*) filter (o.result = 'Aprovado') as approved,
            count(*) filter (o.partly_approved) as partly_approved,
            count(*) filter (o.result = 'Rejeitado') as rejected
        from deputy_initiatives di
        join initiatives i on i.legislature = di.legislature and i.initiative_id = di.initiative_id
        join legislature_days l on l.legislature = di.legislature
        left join initiative_outcome o on o.legislature = di.legislature and o.initiative_id = di.initiative_id
        where di.cadastro_id in (select unnest($cads))
          and list_contains($types, i.type_code)
        group by di.cadastro_id, di.legislature, l.start_date, i.type_code
        order by di.cadastro_id, l.start_date, list_position($types, i.type_code)
        """,
        {"cads": list(cadastro_ids), "types": list(RATED_TYPES)},
    )


def deputy_signing(con, cadastro_ids):
    """Per person and legislature (oldest first): the projetos they signed, by initiative_signing kind."""
    return _rows(
        con,
        """
        select
            di.cadastro_id,
            di.legislature,
            count(*) filter (s.kind = 'grupo_parlamentar') as grupo_parlamentar,
            count(*) filter (s.kind = 'subscricao_restrita') as subscricao_restrita,
            count(*) filter (s.kind = 'outros_grupos') as outros_grupos
        from deputy_initiatives di
        join initiative_signing s on s.legislature = di.legislature and s.initiative_id = di.initiative_id
        join legislature_days l on l.legislature = di.legislature
        where di.cadastro_id in (select unnest(?))
        group by di.cadastro_id, di.legislature, l.start_date
        order by di.cadastro_id, l.start_date
        """,
        [list(cadastro_ids)],
    )


def deputy_initiative_types(con, cadastro_ids):
    """Initiatives each person signed, per type, most first."""
    return _rows(
        con,
        """
        select di.cadastro_id, i.type_code, any_value(i.type) as type, count(*) as total
        from deputy_initiatives di
        join initiatives i on i.legislature = di.legislature and i.initiative_id = di.initiative_id
        where di.cadastro_id in (select unnest(?))
        group by di.cadastro_id, i.type_code
        order by di.cadastro_id, total desc, i.type_code
        """,
        [list(cadastro_ids)],
    )


# Per seat-year figures: a count over the days seated, times 365.25.
_MEASURES = {
    "restricted_initiatives": """
        select di.cadastro_id, count(*) as n
        from deputy_initiatives di
        join initiative_signing s on s.legislature = di.legislature and s.initiative_id = di.initiative_id
        where di.legislature = $leg and s.kind = 'subscricao_restrita'
        group by di.cadastro_id
    """,
    "interventions": """
        select cadastro_id, count(*) as n from interventions where legislature = $leg group by cadastro_id
    """,
}


def group_comparisons(con, legislature, measure):
    """Everyone seated in ``legislature`` against their group, per seat-year of ``measure`` (a
    key of _MEASURES). A group's comparison population is its people seated at least half of the
    legislature's days. Per person: their group, whether they are in that population
    (``eligible``), how many others are (``peers``), their figure and the population's average.
    Someone who held no seat in the legislature has no row."""
    return _rows(
        con,
        f"""
        with counts as ({_MEASURES[measure]}),
        seats as (
            select d.cadastro_id, d.group_acronym, d.days, d.legislature_days, coalesce(c.n, 0) as n
            from deputy_seat_days d
            left join counts c on c.cadastro_id = d.cadastro_id
            where d.legislature = $leg
        ),
        per as (
            select cadastro_id, group_acronym, n * 365.25 / days as per_year
            from seats
            where days > 0 and days >= 0.5 * legislature_days
        ),
        groups as (
            select group_acronym, count(*) as members, avg(per_year) as group_per_year from per group by group_acronym
        )
        select
            s.cadastro_id,
            s.group_acronym,
            s.days > 0 and s.days >= 0.5 * s.legislature_days as eligible,
            coalesce(g.members, 0) - (p.cadastro_id is not null)::int as peers,
            s.n * 365.25 / nullif(s.days, 0) as per_year,
            g.group_per_year
        from seats s
        left join groups g on g.group_acronym is not distinct from s.group_acronym
        left join per p on p.cadastro_id = s.cadastro_id
        """,  # noqa: S608 - the measure query comes from the fixed table above
        {"leg": legislature},
    )


_INTERVENTION_ORDER = {
    "newest": "meeting_date desc nulls last, intervention_id desc",
    "oldest": "meeting_date asc nulls last, intervention_id asc",
    "type": "intervention_type asc nulls last, meeting_date desc nulls last, intervention_id desc",
}


def interventions_page(con, cadastro_id, legislature, kind=None, order="newest", limit=50, offset=0):
    """The person's plenary interventions in a legislature, one page, each row carrying
    ``total`` (interventions matched). ``kind`` matches part of the intervention type."""
    order_by = _INTERVENTION_ORDER.get(order, _INTERVENTION_ORDER["newest"])
    return _rows(
        con,
        f"""
        select *, count(*) over () as total
        from interventions
        where cadastro_id = $cad and legislature = $leg
          and ($kind is null or contains(lower(intervention_type), lower($kind)))
        order by {order_by}
        limit $limit offset $offset
        """,  # noqa: S608 - order_by comes from the fixed table above
        {"cad": cadastro_id, "leg": legislature, "kind": kind or None, "limit": limit, "offset": offset},
    )


def interventions(con, cadastro_ids):
    """Every plenary intervention of each person, per legislature, newest first (the order of
    interventions_page with no filter)."""
    return _rows(
        con,
        f"""
        select * from interventions
        where cadastro_id in (select unnest(?))
        order by cadastro_id, legislature, {_INTERVENTION_ORDER["newest"]}
        """,  # noqa: S608 - the order comes from the fixed table above
        [list(cadastro_ids)],
    )


def interventions_count(con, cadastro_id, legislature, kind=None):
    return con.execute(
        """
        select count(*) from interventions
        where cadastro_id = $cad and legislature = $leg
          and ($kind is null or contains(lower(intervention_type), lower($kind)))
        """,
        {"cad": cadastro_id, "leg": legislature, "kind": kind or None},
    ).fetchone()[0]


def interventions_by_legislature(con):
    """Interventions published per legislature, all speakers, as {legislature: count}."""
    return dict(con.execute("select legislature, count(*) from interventions group by legislature").fetchall())


def legislature_interventions(con, legislature):
    """Interventions published for a legislature, all speakers."""
    return con.execute("select count(*) from interventions where legislature = ?", [legislature]).fetchone()[0]


def deputy_initiatives_in(con, cadastro_ids, limit=100):
    """Per person and legislature, the initiatives they signed, newest first and at most
    ``limit``, with their outcome, how they were signed (initiative_signing), the deputies who
    signed them and ``total``, the number signed in that legislature."""
    return _rows(
        con,
        """
        with mine as (
            select cadastro_id, legislature, initiative_id
            from deputy_initiatives
            where cadastro_id in (select unnest($cads))
        ),
        signed as (
            select a.legislature, a.initiative_id,
                   list(distinct a.name order by a.name) as authors,
                   count(distinct a.cadastro_id) as signatories
            from initiative_authors a
            join (select distinct legislature, initiative_id from mine) using (legislature, initiative_id)
            where a.author_type = 'deputy'
            group by a.legislature, a.initiative_id
        )
        select m.cadastro_id, i.*, o.result, coalesce(o.partly_approved, false) as partly_approved,
               s.authors, s.signatories, g.kind as signing,
               count(*) over (partition by m.cadastro_id, i.legislature) as total
        from initiatives i
        join mine m on m.legislature = i.legislature and m.initiative_id = i.initiative_id
        left join initiative_outcome o on o.legislature = i.legislature and o.initiative_id = i.initiative_id
        left join initiative_signing g on g.legislature = i.legislature and g.initiative_id = i.initiative_id
        left join signed s on s.legislature = i.legislature and s.initiative_id = i.initiative_id
        qualify row_number() over (
            partition by m.cadastro_id, i.legislature
            order by i.first_event_date desc nulls last, i.initiative_id desc
        ) <= $limit
        order by m.cadastro_id, i.legislature, i.first_event_date desc nulls last, i.initiative_id desc
        """,
        {"cads": list(cadastro_ids), "limit": limit},
    )


def latest_declaration(con, cadastro_id):
    """The person's latest interest declaration in the AR open data: latest legislature first,
    then the latest version within it."""
    return _one(
        con,
        """
        select d.*
        from interest_declarations d
        left join legislatures l on l.legislature = d.legislature
        where d.cadastro_id = ?
        order by l.start_date desc nulls last, d.version_date desc nulls last, d.declaration_id desc nulls last
        limit 1
        """,
        [cadastro_id],
    )


def declaration_items(con, legislature, declaration_key, categories):
    """Items of one declaration in the given categories, in their published order. Items the
    declaration repeats word for word (same post, place and period) come back once; the same
    post for another period is its own item."""
    return _rows(
        con,
        """
        select category, description, entity, share, location, start_date_raw, end_date_raw
        from interests
        where legislature = ? and declaration_key = ? and list_contains(?, category)
        qualify row_number() over (
            partition by category, description, entity, share, location, start_date_raw, end_date_raw
            order by item_number
        ) = 1
        order by item_number
        """,
        [legislature, declaration_key, list(categories)],
    )


def declaration_flags(con, legislature, declaration_key):
    """Whether a declaration lists an activity other than the deputy mandate itself (an item
    described as 'Deputado...' or held at the Assembleia da República), and any shareholding."""
    return _one(
        con,
        """
        select
            coalesce(bool_or(
                category = 'activity'
                and not (lower(coalesce(description, '')) like 'deputad%'
                         or lower(coalesce(entity, '')) like '%assembleia da república%')
            ), false) as other_activities,
            coalesce(bool_or(category = 'society'), false) as shareholdings
        from interests
        where legislature = ? and declaration_key = ?
        """,
        [legislature, declaration_key],
    )


def declaration_coverage(con):
    """Over the legislatures with AR open data declarations (first and last): the people with an
    effective mandate in any of them, each counted once, and how many of those have a declaration
    in the AR open data (#106, #113)."""
    return _one(
        con,
        """
        with legs as (
            select distinct d.legislature, l.start_date
            from interest_declarations d
            join legislatures l on l.legislature = d.legislature
            where d.source = 'ar_open_data'
        ),
        seated as (
            select distinct m.cadastro_id
            from mandates m
            join legs using (legislature)
            where m.is_effective
        ),
        declared as (
            select distinct d.cadastro_id
            from interest_declarations d
            join legs using (legislature)
            where d.source = 'ar_open_data'
        )
        select
            (select arg_min(legislature, start_date) from legs) as first_legislature,
            (select arg_max(legislature, start_date) from legs) as last_legislature,
            count(*) as seated,
            count(d.cadastro_id) as declared
        from seated s
        left join declared d on d.cadastro_id = s.cadastro_id
        """,
    )


def seated_since(con, cadastro_id, legislature):
    """Legislatures from ``legislature`` on in which the person held a seat, oldest first."""
    return [
        r[0]
        for r in con.execute(
            """
            select dl.legislature
            from deputy_legislatures dl
            where dl.cadastro_id = ?
              and dl.legislature_start >= (select start_date from legislatures where legislature = ?)
            order by dl.legislature_start
            """,
            [cadastro_id, legislature],
        ).fetchall()
    ]


def recent_plenary_votes(con, legislature, limit):
    """The latest plenary votes of a legislature, newest first, with the initiatives they
    decided (lowest id first) and the phase."""
    return _rows(
        con,
        """
        with latest as (
            select vote_id, date, result, unanimous, description
            from votes
            where legislature = ? and body = 'plenary'
            order by date desc, vote_id desc
            limit ?
        )
        select l.*,
               list(i.title order by i.initiative_id) filter (where i.title is not null) as titles,
               min(iv.phase) as phase
        from latest l
        left join initiative_votes iv on iv.vote_id = l.vote_id and iv.body = 'plenary'
        left join initiatives i
          on i.initiative_id = iv.initiative_id and i.legislature = iv.initiative_legislature
        group by all
        order by l.date desc, l.vote_id desc
        """,
        [legislature, limit],
    )


def group_positions(con, vote_ids):
    """Published group positions of the given plenary votes, by group and then whole groups
    before counts."""
    if not vote_ids:
        return []
    return _rows(
        con,
        """
        select vote_id, group_code, position, deputies
        from vote_group_positions
        where body = 'plenary' and list_contains(?, vote_id)
        order by vote_id, group_code, deputies nulls first
        """,
        [list(vote_ids)],
    )


def activity_counts(con, start, end):
    """Plenary meeting days (with a vote or an intervention), plenary votes by result,
    initiatives presented and interventions between two days, both included."""
    return _one(
        con,
        """
        select
            (select count(*) from (
                select date from votes where body = 'plenary' and date between $start and $end
                union
                select meeting_date from interventions where meeting_date between $start and $end
            )) as plenary_days,
            (select count(*) from votes where body = 'plenary' and date between $start and $end) as votes,
            (select count(*) from votes
             where body = 'plenary' and date between $start and $end and result ilike 'aprovad%') as approved,
            (select count(*) from votes
             where body = 'plenary' and date between $start and $end and result ilike 'rejeitad%') as rejected,
            (select count(*) from initiatives where first_event_date between $start and $end) as initiatives,
            (select count(*) from interventions where meeting_date between $start and $end) as interventions
        """,
        {"start": start, "end": end},
    )


# Plenary attendance (S11): the plenary_attendance mart, one row per sitting and seat holder.

_ATTENDANCE_COUNTS = """
    count(*) as meetings,
    count(*) filter (where category = 'present') as present,
    count(*) filter (where category = 'other_body_or_mission') as other_body_or_mission,
    count(*) filter (where category = 'justified') as justified,
    count(*) filter (where category = 'missed_quorum_vote') as missed_quorum_vote,
    count(*) filter (where category = 'pending') as pending,
    count(*) filter (where category = 'unclassified') as unclassified,
    count(*) filter (where category = 'unjustified') as unjustified
"""


def attendance_by_legislature(con, cadastro_ids):
    """Per person, legislature and kind of sitting (is_ceremonial), their sittings in the lists
    and how many fall in each category, with the groups they sat for and the first and last
    sitting."""
    return _rows(
        con,
        f"""
        select cadastro_id, legislature, is_ceremonial, {_ATTENDANCE_COUNTS},
            list(distinct group_code order by group_code) as groups,
            min(meeting_date) as first_meeting, max(meeting_date) as last_meeting
        from plenary_attendance
        where cadastro_id in (select unnest(?))
        group by cadastro_id, legislature, is_ceremonial
        """,  # noqa: S608 (a constant, no input)
        [list(cadastro_ids)],
    )


def attendance_legislatures(con, legislatures):
    """Per legislature, the seats on the lists of its ordinary and extraordinary sittings and
    how many were present or in another body or on mission. Legislatures with no lists have
    no row."""
    if not legislatures:
        return []
    return _rows(
        con,
        """
        select legislature,
            count(*) as seats,
            count(*) filter (where category = 'present') as present,
            count(*) filter (where category in ('present', 'other_body_or_mission')) as attended
        from plenary_attendance
        where list_contains(?, legislature) and not is_ceremonial
        group by legislature
        """,
        [list(legislatures)],
    )


def attendance_records(con, cadastro_id):
    """Every sitting where the person was not plainly present, newest first."""
    return _rows(
        con,
        """
        select legislature, meeting_date, meeting_id, meeting_type, is_ceremonial, code, category, group_code
        from plenary_attendance
        where cadastro_id = ? and category <> 'present'
        order by meeting_date desc, meeting_id desc
        """,
        [cadastro_id],
    )


def attendance_between(con, legislature, start, end):
    """Seats on the lists of the legislature's ordinary and extraordinary sittings between two
    days (both included), how many attended, and the number of sittings."""
    return _one(
        con,
        """
        select count(distinct meeting_id) as meetings, count(*) as seats,
            count(*) filter (where category in ('present', 'other_body_or_mission')) as attended
        from plenary_attendance
        where legislature = ? and not is_ceremonial and meeting_date between ? and ?
        """,
        [legislature, start, end],
    )

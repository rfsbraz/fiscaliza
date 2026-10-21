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


def deputy_votes(con, cadastro_id, legislature):
    """Every plenary vote of the legislature the deputy was seated for, oldest first, with
    their group that day, the group's position as a whole and theirs (null when unknown)."""
    return _rows(
        con,
        """
        select vote_id, date, group_acronym, group_position, position, named
        from deputy_vote_positions
        where cadastro_id = ? and legislature = ?
        order by date, vote_id
        """,
        [cadastro_id, legislature],
    )


def deputy_group_agreement(con, cadastro_id, legislature):
    """For each other group, the votes where the deputy and that group as a whole both cast
    a vote (favour, against or abstention), and how many of them match."""
    return _rows(
        con,
        f"""
        with mine as (
            select vote_id, group_acronym, position
            from deputy_vote_positions
            where cadastro_id = $cadastro_id and legislature = $legislature and list_contains($cast, position)
        ),
        groups as ({_GROUP_POSITIONS})
        select g.group_code as group_acronym,
               count(*) as total_votes,
               count(*) filter (g.position = m.position) as aligned_votes
        from mine m
        join groups g on g.vote_id = m.vote_id and g.group_code is distinct from m.group_acronym
        where list_contains($cast, g.position)
        group by g.group_code
        order by g.group_code
        """,  # noqa: S608 - a fixed SQL fragment, values are bound
        {"cadastro_id": cadastro_id, "legislature": legislature, "cast": list(CAST)},
    )


def deputy_close_votes(con, cadastro_id, legislature, margin):
    """Plenary votes the deputy has a known position on whose tally is complete and decided
    by ``margin`` or fewer (favour minus against), newest first."""
    return _rows(
        con,
        """
        select p.vote_id, p.position, t.favour, t.against, t.abstention
        from deputy_vote_positions p
        join vote_tallies t on t.vote_id = p.vote_id
        where p.cadastro_id = ? and p.legislature = ? and p.position is not null
          and t.complete and abs(t.favour - t.against) <= ?
        order by p.date desc, p.vote_id desc
        """,
        [cadastro_id, legislature, margin],
    )


def votes_by_id(con, vote_ids):
    """Date, description and result of the given votes."""
    if not vote_ids:
        return []
    return _rows(
        con,
        "select vote_id, date, description, result from votes where list_contains(?, vote_id)",
        [list(vote_ids)],
    )


def group_positions(con, vote_ids):
    """Each group's position as a whole on the given votes."""
    if not vote_ids:
        return []
    return _rows(
        con,
        """
        select vote_id, group_code, any_value(position) as position
        from vote_group_positions
        where body = 'plenary' and deputies is null and list_contains(?, vote_id)
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

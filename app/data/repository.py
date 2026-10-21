"""All SQL the site runs, one function per question, returning plain rows.

Every function takes a DuckDB cursor on the live file (see connection.py) and returns
dicts or lists of dicts. The site views it reads (legislature_days, current_legislature,
seated_detail, deputy_current, deputy_legislatures) are created at sync time by
fiscaliza_data/views.sql. No string building: every value is a bound parameter.
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

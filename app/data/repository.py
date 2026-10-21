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


# Deputy page (S5)


def deputy(con, cadastro_id):
    return _one(con, "select * from deputies where cadastro_id = ?", [cadastro_id])


def is_seated(con, cadastro_id):
    return con.execute("select count(*) from deputy_current where cadastro_id = ?", [cadastro_id]).fetchone()[0] > 0


def seat_periods(con, cadastro_id):
    """Per legislature the person held a seat in, oldest first: the first day and the last day
    of their effective mandates (null while still seated in an open legislature) and the days
    seated, counted up to the legislature's reference day."""
    return _rows(
        con,
        """
        select
            m.legislature,
            min(m.start_date) as seat_start,
            case when l.is_open and bool_or(m.end_date is null) then null
                 else max(least(coalesce(m.end_date, l.ref_day), l.ref_day)) end as seat_end,
            sum(greatest(date_diff('day', m.start_date, least(coalesce(m.end_date, l.ref_day), l.ref_day)), 0))
                as days
        from mandates m
        join legislature_days l on l.legislature = m.legislature
        where m.cadastro_id = ? and m.is_effective
        group by m.legislature, l.is_open, l.start_date
        order by l.start_date
        """,
        [cadastro_id],
    )


def group_names(con, legislatures):
    """{(legislature, group acronym): name} for the groups of the given legislatures."""
    rows = _rows(
        con,
        "select legislature, group_acronym, name from parliamentary_groups where list_contains(?, legislature)",
        [list(legislatures)],
    )
    return {(r["legislature"], r["group_acronym"]): r["name"] for r in rows}


def deputy_activity_by_legislature(con, cadastro_id):
    """Per legislature: initiatives the person signed, how many of them passed, and their
    plenary interventions."""
    return _rows(
        con,
        """
        with ini as (
            select di.legislature, count(*) as initiatives, count(*) filter (o.result = 'Aprovado') as approved
            from deputy_initiatives di
            left join initiative_outcome o
              on o.legislature = di.legislature and o.initiative_id = di.initiative_id
            where di.cadastro_id = $cad
            group by di.legislature
        ),
        itv as (
            select legislature, count(*) as interventions
            from interventions
            where cadastro_id = $cad
            group by legislature
        )
        select
            coalesce(ini.legislature, itv.legislature) as legislature,
            coalesce(ini.initiatives, 0) as initiatives,
            coalesce(ini.approved, 0) as approved,
            coalesce(itv.interventions, 0) as interventions
        from ini
        full join itv on itv.legislature = ini.legislature
        """,
        {"cad": cadastro_id},
    )


def deputy_initiative_types(con, cadastro_id):
    """Initiatives the person signed, per type, most first."""
    return _rows(
        con,
        """
        select i.type_code, any_value(i.type) as type, count(*) as total
        from deputy_initiatives di
        join initiatives i on i.legislature = di.legislature and i.initiative_id = di.initiative_id
        where di.cadastro_id = ?
        group by i.type_code
        order by total desc, i.type_code
        """,
        [cadastro_id],
    )


def legislature_comparison(con, cadastro_id, legislature, group_acronym):
    """In one legislature, over everyone who held a seat in it: the average initiatives and
    interventions of the people of ``group_acronym``, the average interventions of everyone, and
    the person's percentile by initiatives (percent_rank, 0 to 1)."""
    return _one(
        con,
        """
        with people as (
            select cadastro_id, group_acronym from deputy_legislatures where legislature = $leg
        ),
        ini as (
            select cadastro_id, count(*) as n from deputy_initiatives where legislature = $leg group by 1
        ),
        itv as (
            select cadastro_id, count(*) as n from interventions where legislature = $leg group by 1
        ),
        per as (
            select
                p.cadastro_id,
                p.group_acronym,
                coalesce(ini.n, 0) as initiatives,
                coalesce(itv.n, 0) as interventions,
                percent_rank() over (order by coalesce(ini.n, 0)) as rank
            from people p
            left join ini on ini.cadastro_id = p.cadastro_id
            left join itv on itv.cadastro_id = p.cadastro_id
        )
        select
            avg(initiatives) filter (group_acronym = $grp) as party_initiatives,
            avg(interventions) filter (group_acronym = $grp) as party_interventions,
            avg(interventions) as all_interventions,
            max(rank) filter (cadastro_id = $cad) as rank
        from per
        """,
        {"leg": legislature, "grp": group_acronym, "cad": cadastro_id},
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


def interventions_count(con, cadastro_id, legislature, kind=None):
    return con.execute(
        """
        select count(*) from interventions
        where cadastro_id = $cad and legislature = $leg
          and ($kind is null or contains(lower(intervention_type), lower($kind)))
        """,
        {"cad": cadastro_id, "leg": legislature, "kind": kind or None},
    ).fetchone()[0]


def legislature_interventions(con, legislature):
    """Interventions published for a legislature, all speakers."""
    return con.execute("select count(*) from interventions where legislature = ?", [legislature]).fetchone()[0]


def deputy_initiatives_in(con, cadastro_id, legislature, limit=100):
    """Initiatives the person signed in a legislature, newest first, with their outcome, the
    deputies who signed them and how many groups those deputies sat for."""
    return _rows(
        con,
        """
        with mine as (
            select initiative_id from deputy_initiatives where cadastro_id = $cad and legislature = $leg
        ),
        signed as (
            select a.initiative_id,
                   list(distinct a.name order by a.name) as authors,
                   count(distinct a.group_code) as groups
            from initiative_authors a
            join mine using (initiative_id)
            where a.legislature = $leg and a.author_type = 'deputy'
            group by a.initiative_id
        )
        select i.*, o.result, s.authors, s.groups, count(*) over () as total
        from initiatives i
        join mine using (initiative_id)
        left join initiative_outcome o on o.legislature = i.legislature and o.initiative_id = i.initiative_id
        left join signed s on s.initiative_id = i.initiative_id
        where i.legislature = $leg
        order by i.first_event_date desc nulls last, i.initiative_id desc
        limit $limit
        """,
        {"cad": cadastro_id, "leg": legislature, "limit": limit},
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
    """Items of one declaration in the given categories, in their published order."""
    return _rows(
        con,
        """
        select category, description, entity, share
        from interests
        where legislature = ? and declaration_key = ? and list_contains(?, category)
        order by item_number
        """,
        [legislature, declaration_key, list(categories)],
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

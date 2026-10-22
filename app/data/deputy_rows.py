"""The rows the deputy page reads, fetched for a set of people at once.

Each question runs once for everyone in the set, the first time any of them needs it, and is
then answered from memory. The Flask routes make one for the person asked; the static export
makes one per batch of people, so it runs a few queries per batch instead of a few per person
and legislature. Both build their answers from the same rows with the same code.
"""

from collections import defaultdict

from app.data import repository


class DeputyRows:
    def __init__(self, con, cadastro_ids):
        self.con = con
        self.ids = list(cadastro_ids)
        self._cache = {}

    def _memo(self, key, load):
        if key not in self._cache:
            self._cache[key] = load()
        return self._cache[key]

    def _by(self, name, load, *fields):
        """Rows of ``load(con, ids)`` grouped by ``fields``, in their query order."""

        def group():
            out = defaultdict(list)
            for row in load(self.con, self.ids):
                out[tuple(row[f] for f in fields)].append(row)
            return out

        return self._memo(name, group)

    # Shared by everyone

    def current_legislature(self):
        return self._memo("current", lambda: repository.current_legislature(self.con))

    def legislature(self, name):
        return self._memo(("legislature", name), lambda: repository.legislature(self.con, name))

    def legislature_interventions(self, name):
        return self._memo(("published", name), lambda: repository.legislature_interventions(self.con, name))

    def group_names(self):
        """{(legislature, group acronym): name} for every legislature anyone in the set was elected
        or held a seat in."""
        return self._memo(
            "group_names",
            lambda: repository.group_names(
                self.con, sorted({c["legislature"] for cad in self.ids for c in self.elections(cad)})
            ),
        )

    def comparison(self, cadastro_id, legislature, measure):
        rows = self._memo(
            ("comparison", legislature, measure),
            lambda: {r["cadastro_id"]: r for r in repository.group_comparisons(self.con, legislature, measure)},
        )
        return rows.get(cadastro_id)

    # Per person

    def deputy(self, cadastro_id):
        found = self._by("deputies", repository.deputies_by_id, "cadastro_id").get((cadastro_id,))
        return found[0] if found else None

    def career(self, cadastro_id):
        return self._by("careers", repository.careers, "cadastro_id").get((cadastro_id,), [])

    def elections(self, cadastro_id):
        """Every legislature the person was elected or held a seat in, oldest first."""
        return self._by("elections", repository.elections, "cadastro_id").get((cadastro_id,), [])

    def is_seated(self, cadastro_id):
        return cadastro_id in self._memo("seated", lambda: repository.seated(self.con, self.ids))

    def seat_periods(self, cadastro_id):
        return self._by("seat_periods", repository.seat_periods, "cadastro_id").get((cadastro_id,), [])

    def activity_by_legislature(self, cadastro_id):
        return self._by("activity", repository.deputy_activity_by_legislature, "cadastro_id").get((cadastro_id,), [])

    def initiative_types(self, cadastro_id):
        return self._by("initiative_types", repository.deputy_initiative_types, "cadastro_id").get((cadastro_id,), [])

    def outcomes(self, cadastro_id, legislature=None):
        rows = self._by("outcomes", repository.deputy_outcomes, "cadastro_id").get((cadastro_id,), [])
        return [r for r in rows if legislature is None or r["legislature"] == legislature]

    def signing(self, cadastro_id, legislature=None):
        rows = self._by("signing", repository.deputy_signing, "cadastro_id").get((cadastro_id,), [])
        return [r for r in rows if legislature is None or r["legislature"] == legislature]

    def interventions(self, cadastro_id, legislature):
        by = self._by("interventions", repository.interventions, "cadastro_id", "legislature")
        return by.get((cadastro_id, legislature), [])

    def initiatives(self, cadastro_id, legislature, limit):
        by = self._by(
            ("initiatives", limit),
            lambda con, ids: repository.deputy_initiatives_in(con, ids, limit=limit),
            "cadastro_id",
            "legislature",
        )
        return by.get((cadastro_id, legislature), [])

    def attendance(self, cadastro_id):
        return self._by("attendance", repository.attendance_by_legislature, "cadastro_id").get((cadastro_id,), [])

    def votes(self, cadastro_id, legislature):
        return self._by("votes", repository.deputy_votes, "cadastro_id", "legislature").get(
            (cadastro_id, legislature), []
        )

    def close_votes(self, cadastro_id, legislature, margin):
        by = self._by(
            ("close", margin),
            lambda con, ids: repository.deputy_close_votes(con, ids, margin),
            "cadastro_id",
            "legislature",
        )
        return by.get((cadastro_id, legislature), [])

    def group_agreement(self, cadastro_id, legislature):
        by = self._by("agreement", repository.deputy_group_agreement, "cadastro_id", "legislature")
        return by.get((cadastro_id, legislature), [])

    def vote_items(self, vote_ids):
        """{vote_id: (vote row, [group position rows], [initiative rows])} for the given votes. The
        first call loads every vote anyone in the set may list: those where the detail names them,
        and the close votes asked for so far."""
        items = self._cache.setdefault("vote_items", {})
        missing = set(vote_ids) - items.keys()
        if missing:
            if "vote_items_loaded" not in self._cache:
                self._cache["vote_items_loaded"] = True
                missing |= {r["vote_id"] for rows in self._by_votes() for r in rows if r["named"]}
                for key, by in self._cache.items():
                    if isinstance(key, tuple) and key[0] == "close":
                        missing |= {r["vote_id"] for rows in by.values() for r in rows}
                missing -= items.keys()
            ids = sorted(missing)
            positions = defaultdict(list)
            for row in repository.whole_group_positions(self.con, ids):
                positions[row["vote_id"]].append(row)
            initiatives = defaultdict(list)
            for row in repository.vote_initiatives(self.con, ids):
                initiatives[row["vote_id"]].append(row)
            for vote in repository.votes_by_id(self.con, ids):
                items[vote["vote_id"]] = (vote, positions[vote["vote_id"]], initiatives[vote["vote_id"]])
        return {v: items[v] for v in vote_ids if v in items}

    def _by_votes(self):
        return self._by("votes", repository.deputy_votes, "cadastro_id", "legislature").values()

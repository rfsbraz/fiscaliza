"""Dependabot groups updates per ecosystem: minor and patch in one PR, majors in another."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".github" / "dependabot.yml"


def _entries():
    """Split dependabot.yml into one text block per update entry."""
    text = CONFIG.read_text()
    return [block for block in re.split(r"\n  - ", text)[1:]]


def _groups(block):
    """Return {group_name: [update types]} for one update entry."""
    groups = {}
    current = None
    in_groups = False
    for line in block.splitlines():
        if re.match(r"^    groups:\s*$", line):
            in_groups = True
            continue
        if in_groups and re.match(r"^    \S", line):
            break
        name = re.match(r"^      ([A-Za-z0-9_-]+):\s*$", line)
        if in_groups and name:
            current = name.group(1)
            groups[current] = []
            continue
        types = re.match(r"^        update-types:\s*\[(.*)\]\s*$", line)
        if in_groups and current and types:
            groups[current] = [t.strip().strip("\"'") for t in types.group(1).split(",")]
    return groups


def test_there_are_update_entries():
    assert len(_entries()) == 3


def test_every_ecosystem_groups_minor_and_patch_and_majors_apart():
    for block in _entries():
        ecosystem = re.search(r"package-ecosystem:\s*\"?([\w-]+)", block).group(1)
        types = sorted(_groups(block).values())
        assert types == [["major"], ["minor", "patch"]], f"{ecosystem}: {types}"

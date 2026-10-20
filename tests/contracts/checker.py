"""Check a JSON payload against an endpoint contract.

A contract lists key paths with a type and a nullable flag. ``a.b`` is key ``b`` of
object ``a``; ``a[].b`` is key ``b`` of every element of array ``a``. A nullable key may
be missing or null, and then nothing under it is checked.

Types: ``object``, ``array``, ``mapping`` (an object keyed by names, such as counts per
category), ``string``, ``number``, ``boolean``, ``scalar`` (a string or a number that the
component renders as text) and ``any``.
"""

import re

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "mapping": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, int | float) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "scalar": lambda v: isinstance(v, str | int | float) and not isinstance(v, bool),
    "any": lambda v: True,
}

_SEGMENT = re.compile(r"[^.\[\]]+|\[\]")
_MISSING = object()


def _segments(path):
    return _SEGMENT.findall(path)


def _resolve(payload, segments, where=""):
    """Yield (concrete path, value) for every value the segments reach.

    Stops quietly at a missing or null container: whether that is allowed is checked on
    the container's own key.
    """
    if not segments:
        yield where or "<root>", payload
        return
    head, rest = segments[0], segments[1:]
    if head == "[]":
        if isinstance(payload, list):
            for i, item in enumerate(payload):
                yield from _resolve(item, rest, f"{where}[{i}]")
        return
    if not isinstance(payload, dict):
        return
    here = f"{where}.{head}" if where else head
    value = payload.get(head, _MISSING)
    if not rest:
        yield here, value
        return
    if value is _MISSING or value is None:
        return
    yield from _resolve(value, rest, here)


def check(payload, contract):
    """Return a list of human-readable problems; empty means the payload fits."""
    if not isinstance(payload, dict):
        return [f"<root>: expected object, got {type(payload).__name__}"]
    problems = []
    for key in contract["keys"]:
        expected = key["type"]
        for where, value in _resolve(payload, _segments(key["path"])):
            if value is _MISSING:
                if not key["nullable"]:
                    problems.append(f"{where}: missing")
            elif value is None:
                if not key["nullable"]:
                    problems.append(f"{where}: null but not nullable")
            elif not _TYPES[expected](value):
                problems.append(f"{where}: expected {expected}, got {type(value).__name__}")
    return problems

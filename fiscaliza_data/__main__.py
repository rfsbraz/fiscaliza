"""python -m fiscaliza_data sync [--tag TAG] [--from PATH] [--data-dir DIR] [--data-commit SHA]

Also runnable as `python -m fiscaliza_data.sync [--tag TAG] [--from PATH] [--data-dir DIR]`.
"""

import argparse
import os
import sys

from fiscaliza_data.sync import DEFAULT_DATA_DIR, SyncError, sync


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fiscaliza_data")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync", help="build the site's DuckDB file from a parlamento-aberto release")
    s.add_argument("--tag", help="release tag; default: the latest release")
    s.add_argument(
        "--from",
        "--from-dir",
        dest="source",
        metavar="PATH",
        help="a local `release build` output instead of GitHub: the folder, its manifest.json, "
        "or a .tar.gz, .tgz or .zip of the folder",
    )
    s.add_argument(
        "--data-dir",
        default=os.getenv("FISCALIZA_DATA_DIR") or DEFAULT_DATA_DIR,
        help=f"where the DuckDB files live (default $FISCALIZA_DATA_DIR, else {DEFAULT_DATA_DIR})",
    )
    s.add_argument("--data-commit", metavar="SHA", help="stop unless the release was built from this commit")
    args = parser.parse_args(argv)
    try:
        result = sync(args.data_dir, tag=args.tag, source=args.source, data_commit=args.data_commit)
    except SyncError as e:
        print(f"sync failed: {e}", file=sys.stderr)
        return 1
    if not result.changed:
        print(f"{result.tag} is already live, nothing to do")
        return 0
    print(f"{result.tag} is live: {result.path}")
    for legislature, n in sorted(result.seated.items()):
        print(f"  {legislature}: {n} seated on {result.extract_date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

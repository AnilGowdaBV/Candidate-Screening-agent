"""Read-only check: live SQLite files vs candidate_screening MySQL tables."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pymysql

from app.database.session import TECHNOLOGY_DB_MAP

DATA = Path(__file__).resolve().parents[2] / "data"
TABLES = [
    "candidates",
    "screening_runs",
    "screening_results",
    "note_actions",
    "activity_events",
]


def main() -> None:
    con = pymysql.connect(
        host="127.0.0.1",
        user=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"],
        database="candidate_screening",
        charset="utf8mb4",
    )
    cur = con.cursor()
    problems = []
    for tech, filename in TECHNOLOGY_DB_MAP.items():
        if tech == "qa":
            continue
        path = DATA / filename
        src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        src.row_factory = sqlite3.Row
        print(f"\n== {tech} ({filename}) ==")
        for table in TABLES:
            dest = f"{tech}_{table}"
            exists = src.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not exists:
                print(f"  {table}: missing in sqlite")
                problems.append((tech, table, "missing sqlite"))
                continue
            srows = list(src.execute(f'SELECT * FROM "{table}" ORDER BY id'))
            info = list(src.execute(f'PRAGMA table_info("{table}")'))
            scols = [r[1] for r in info]
            cur.execute(f"SHOW COLUMNS FROM `{dest}`")
            mcols = [r[0] for r in cur.fetchall()]
            missing_cols = [c for c in scols if c not in mcols]
            cur.execute(f"SELECT * FROM `{dest}`")
            mdesc = [d[0] for d in cur.description]
            mrows = cur.fetchall()
            print(
                f"  {table}: sqlite={len(srows)} mysql={len(mrows)} "
                f"extra_sqlite_cols={missing_cols or '-'}"
            )
            if len(srows) != len(mrows):
                problems.append((tech, table, "count"))
            if missing_cols and srows:
                for c in missing_cols:
                    filled = sum(1 for r in srows if r[c] not in (None, ""))
                    if filled:
                        problems.append((tech, table, f"dropped {c} filled={filled}"))
                        print(f"    DROPPED NONEMPTY {c}: {filled}")
            sid = {r["id"] for r in srows}
            mid = {r[mdesc.index("id")] for r in mrows}
            if sid != mid:
                problems.append(
                    (tech, table, f"id mismatch only_sqlite={len(sid - mid)} only_mysql={len(mid - sid)}")
                )
                print("    ID SET MISMATCH")
                continue
            mmap = {r[mdesc.index("id")]: r for r in mrows}
            bad = 0
            for r in srows:
                mr = mmap[r["id"]]
                for c in scols:
                    if c not in mcols:
                        continue
                    sv = r[c]
                    mv = mr[mdesc.index(c)]
                    if sv is None and mv is None:
                        continue
                    if isinstance(mv, datetime) and isinstance(sv, str):
                        sv = datetime.fromisoformat(sv.replace("Z", "+00:00"))
                        if sv.tzinfo is not None:
                            sv = sv.astimezone(timezone.utc).replace(tzinfo=None)
                    if sv != mv and str(sv) != str(mv):
                        bad += 1
                        if bad <= 2:
                            print(f"    value mismatch id={r['id']} col={c}")
                        break
            if bad:
                problems.append((tech, table, f"value mismatches={bad}"))
                print(f"    mismatches={bad}")
            else:
                print("    values match")
        src.close()
    print("\nPROBLEMS", len(problems))
    for item in problems:
        print(" ", item)
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

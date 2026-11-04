"""Copy live SQLite screening databases into local MySQL. Does not modify SQLite files."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.database.session import TECHNOLOGY_DB_MAP, Base
import app.models  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
HOST = os.environ.get("DB_HOST", "127.0.0.1")
PORT = int(os.environ.get("DB_PORT", "3306"))
USER = os.environ["DB_USERNAME"]
PASSWORD = os.environ["DB_PASSWORD"]

# Parent rows first so foreign keys succeed.
TABLE_ORDER = [
    "candidates",
    "screening_runs",
    "screening_results",
    "note_actions",
    "activity_events",
]


def mysql_admin():
    return pymysql.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, autocommit=True)


def copy_db(sqlite_path: Path, mysql_name: str, prefix: str) -> dict[str, tuple[int, int]]:
    from sqlalchemy import Column, MetaData, Table, Text
    from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
    from urllib.parse import quote_plus

    admin = mysql_admin()
    with admin.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{mysql_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    admin.close()

    url = (
        f"mysql+pymysql://{quote_plus(USER)}:{quote_plus(PASSWORD)}"
        f"@{HOST}:{PORT}/{mysql_name}?charset=utf8mb4"
    )
    engine: Engine = create_engine(url)
    prefixed = MetaData()
    for table in Base.metadata.sorted_tables:
        Table(
            f"{prefix}{table.name}",
            prefixed,
            *[
                Column(
                    c.name,
                    (
                        Text()
                        if "CHAR" in str(c.type) or "TEXT" in str(c.type)
                        else MYSQL_DATETIME(fsp=6)
                        if "DATETIME" in str(c.type).upper() or "DATE" in str(c.type).upper()
                        else c.type
                    ),
                    primary_key=c.primary_key,
                    nullable=c.nullable,
                )
                for c in table.columns
            ],
        )
    prefixed.drop_all(bind=engine)
    prefixed.create_all(bind=engine)

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row
    counts: dict[str, tuple[int, int]] = {}

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in TABLE_ORDER:
            exists = src.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not exists:
                counts[table] = (0, 0)
                continue
            rows = src.execute(f'SELECT * FROM "{table}"').fetchall()
            dest = f"{prefix}{table}"
            mysql_cols = {
                r[0]
                for r in conn.execute(text(f"SHOW COLUMNS FROM `{dest}`"))
            }
            if not rows:
                counts[table] = (0, 0)
                continue
            src_cols = [k for k in rows[0].keys() if k in mysql_cols]
            placeholders = ", ".join(f":{c}" for c in src_cols)
            col_sql = ", ".join(f"`{c}`" for c in src_cols)
            def keep_utc_wall_time(value):
                if (
                    not isinstance(value, str)
                    or len(value) < 19
                    or not value[0].isdigit()
                    or "T" not in value[:11]
                ):
                    return value
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
                return parsed.strftime("%Y-%m-%d %H:%M:%S.%f")

            payload = [
                {c: keep_utc_wall_time(row[c]) for c in src_cols} for row in rows
            ]
            conn.execute(
                text(f"INSERT INTO `{dest}` ({col_sql}) VALUES ({placeholders})"),
                payload,
            )
            copied = conn.execute(text(f"SELECT COUNT(*) FROM `{dest}`")).scalar()
            counts[table] = (len(rows), int(copied))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    src.close()
    engine.dispose()
    return counts


def main() -> None:
    print(f"MySQL {HOST}:{PORT} as {USER}")
    for tech, filename in TECHNOLOGY_DB_MAP.items():
        if tech == "qa":
            continue
        path = DATA / filename
        mysql_name = "candidate_screening"
        print(f"\n{path.name} -> {mysql_name}.{tech}_*")
        if not path.exists():
            print("  SKIP missing file")
            continue
        counts = copy_db(path, mysql_name, prefix=f"{tech}_")
        ok = True
        for table, (src_n, dst_n) in counts.items():
            flag = "OK" if src_n == dst_n else "MISMATCH"
            if flag != "OK":
                ok = False
            print(f"  {table}: sqlite={src_n} mysql={dst_n} {flag}")
        print("  RESULT", "MATCH" if ok else "FAILED")


if __name__ == "__main__":
    main()

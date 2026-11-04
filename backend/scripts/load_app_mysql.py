"""Load each technology into its own MySQL database."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pymysql
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.database.session import TECHNOLOGY_DB_MAP, Base, get_engine_for_tech
import app.models  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
TABLES = [
    "candidates",
    "screening_runs",
    "screening_results",
    "note_actions",
    "activity_events",
]


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


def main() -> None:
    settings = get_settings()
    url = make_url(settings.DATABASE_URL)
    admin = pymysql.connect(
        host=url.host,
        port=url.port or 3306,
        user=url.username,
        password=url.password,
        autocommit=True,
    )
    techs = [tech for tech in TECHNOLOGY_DB_MAP if tech != "qa"]
    with admin.cursor() as cur:
        for tech in techs:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `candidate_screening_{tech}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    admin.close()

    for tech in techs:
        eng = get_engine_for_tech(tech)
        Base.metadata.drop_all(bind=eng)
        Base.metadata.create_all(bind=eng)
        src = sqlite3.connect(ROOT / "data" / TECHNOLOGY_DB_MAP[tech])
        src.row_factory = sqlite3.Row
        with eng.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            for table in TABLES:
                rows = list(src.execute(f'SELECT * FROM "{table}"'))
                if not rows:
                    print(f"{tech}.{table}: 0")
                    continue
                mysql_cols = {row[0] for row in conn.execute(text(f"SHOW COLUMNS FROM `{table}`"))}
                cols = [name for name in rows[0].keys() if name in mysql_cols and name != "technology"]
                payload = []
                for row in rows:
                    item = {col: keep_utc_wall_time(row[col]) for col in cols}
                    if "technology" in mysql_cols:
                        item["technology"] = tech
                    payload.append(item)
                insert_cols = cols + (["technology"] if "technology" in mysql_cols else [])
                col_sql = ", ".join(f"`{c}`" for c in insert_cols)
                placeholders = ", ".join(f":{c}" for c in insert_cols)
                conn.execute(
                    text(f"INSERT INTO `{table}` ({col_sql}) VALUES ({placeholders})"),
                    payload,
                )
                copied = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
                print(f"{tech}.{table}: sqlite={len(rows)} mysql={copied}")
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        src.close()

    admin = pymysql.connect(
        host=url.host,
        port=url.port or 3306,
        user=url.username,
        password=url.password,
        autocommit=True,
    )
    with admin.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS `candidate_screening`")
    admin.close()
    print("removed combined database candidate_screening")


if __name__ == "__main__":
    main()

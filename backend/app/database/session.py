"""Database engine and session factory. MySQL for the app, SQLite for local tests."""

from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base model class for SQLAlchemy 2.x declarative models."""
    pass


# Supported Technologies and their DB files
TECHNOLOGY_DB_MAP = {
    "golang": "screening_golang.db",
    "python": "screening_python.db",
    "java": "screening_java.db",
    "javascript": "screening_javascript.db",
    "typescript": "screening_typescript.db",
    "frontend": "screening_frontend.db",
    "qa_automation": "screening_qa_automation.db",
    "qa": "screening_qa_automation.db",
}

settings = get_settings()
# Resolve project root data directory
project_root = Path(__file__).resolve().parents[3]  # backend/app/database/session.py -> 3 parents is root
base_dir = project_root / "data"
if not base_dir.exists():
    base_dir = Path(__file__).resolve().parents[2] / "data"
base_dir.mkdir(parents=True, exist_ok=True)

_engines: dict[str, Engine] = {}
_sessionmakers: dict[str, sessionmaker] = {}


def _uses_mysql() -> bool:
    return settings.DATABASE_URL.startswith("mysql")


def _uses_postgres() -> bool:
    return settings.DATABASE_URL.startswith("postgresql")


def _canonical_tech(technology: str | None) -> str:
    tech = (technology or "golang").lower()
    if tech not in TECHNOLOGY_DB_MAP:
        tech = "golang"
    if tech == "qa":
        tech = "qa_automation"
    return tech


def _mysql_database_name(tech: str) -> str:
    return f"candidate_screening_{tech}"


def get_engine_for_tech(technology: str = "golang") -> Engine:
    tech = _canonical_tech(technology)
    if tech not in _engines:
        if _uses_postgres():
            if "postgres" not in _engines:
                _engines["postgres"] = create_engine(
                    settings.DATABASE_URL,
                    poolclass=NullPool,
                    echo=False,
                    connect_args={"prepare_threshold": None},
                )
            eng = _engines["postgres"].execution_options(schema_translate_map={None: tech})
        elif _uses_mysql():
            url = make_url(settings.DATABASE_URL).set(database=_mysql_database_name(tech))
            eng = create_engine(url, pool_pre_ping=True, echo=False)
        else:
            db_path = base_dir / TECHNOLOGY_DB_MAP[tech]
            eng = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False},
                echo=False,
            )

            @event.listens_for(eng, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        _engines[tech] = eng
        _sessionmakers[tech] = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return _engines[tech]


def get_sessionmaker_for_tech(technology: str = "golang") -> sessionmaker:
    tech = _canonical_tech(technology)
    if tech not in _sessionmakers:
        get_engine_for_tech(tech)
    return _sessionmakers[tech]


# Default engine and sessionmaker for backward compatibility (points to golang)
engine = get_engine_for_tech("golang")
SessionLocal = get_sessionmaker_for_tech("golang")


from fastapi import Query

def get_db(technology: str = Query("golang")) -> Generator[Session, None, None]:
    """Dependency that yields an active database session for the specified technology."""
    sm = get_sessionmaker_for_tech(technology)
    db = sm()
    try:
        yield db
    finally:
        db.close()


def _column_names(conn, table: str) -> set[str]:
    if conn.engine.dialect.name == "mysql":
        rows = conn.exec_driver_sql(f"SHOW COLUMNS FROM `{table}`").fetchall()
        return {row[0] for row in rows}
    if conn.engine.dialect.name == "postgresql":
        rows = conn.exec_driver_sql(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            (table,),
        ).fetchall()
        return {row[0] for row in rows}
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _migrate_columns(eng: Engine) -> None:
    """Add columns that were introduced after the first schema."""
    try:
        with eng.connect() as conn:
            existing_cols = _column_names(conn, "candidates")
            if not existing_cols:
                return
            new_cols = {
                "technology": "VARCHAR(50) DEFAULT 'golang'",
                "gitroll_rating": "FLOAT",
                "gitroll_grade": "VARCHAR(20)",
                "gitroll_profile_url": "VARCHAR(500)",
                "gitroll_scanned_at": "DATETIME",
                "gitroll_note_status": "VARCHAR(50)",
                "current_salary": "VARCHAR(100)",
                "location": "VARCHAR(150)",
                "experience": "VARCHAR(50)",
                "coding_profiles": "VARCHAR(500)",
                "languages_found": "VARCHAR(200)",
            }
            for col_name, col_type in new_cols.items():
                if col_name not in existing_cols:
                    conn.exec_driver_sql(f"ALTER TABLE candidates ADD COLUMN {col_name} {col_type}")

            existing_sr_cols = _column_names(conn, "screening_results")
            if existing_sr_cols and "languages_found" not in existing_sr_cols:
                conn.exec_driver_sql("ALTER TABLE screening_results ADD COLUMN languages_found VARCHAR(200)")
            for table in ("screening_runs", "screening_results", "note_actions", "activity_events"):
                cols = _column_names(conn, table)
                if cols and "technology" not in cols:
                    conn.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN technology VARCHAR(50) DEFAULT 'golang'"
                    )

            conn.commit()
    except Exception as e:
        pass


def init_db(technology: str = "golang") -> None:
    """Create all tables if they don't exist for the specified technology or all."""
    import app.models  # Ensures all models are registered with Base.metadata
    from sqlalchemy import text

    techs = list(TECHNOLOGY_DB_MAP) if technology == "all" else [technology]
    for tech in techs:
        eng = get_engine_for_tech(tech)
        if _uses_postgres():
            with eng.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{_canonical_tech(tech)}"'))
        Base.metadata.create_all(bind=eng)
        _migrate_columns(eng)

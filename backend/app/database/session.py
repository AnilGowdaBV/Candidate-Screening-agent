"""Database engine, session factory, and SQLite PRAGMA configuration."""

from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session, DeclarativeBase
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


def get_engine_for_tech(technology: str = "golang") -> Engine:
    tech = technology.lower() if technology else "golang"
    if tech not in TECHNOLOGY_DB_MAP:
        tech = "golang"

    if tech not in _engines:
        db_filename = TECHNOLOGY_DB_MAP[tech]
        db_path = base_dir / db_filename
        db_url = f"sqlite:///{db_path}"
        eng = create_engine(
            db_url,
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
    tech = technology.lower() if technology else "golang"
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


def _migrate_columns(eng: Engine) -> None:
    """Safely add any missing columns to existing SQLite tables."""
    try:
        with eng.connect() as conn:
            cursor = conn.exec_driver_sql("PRAGMA table_info(candidates)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if not existing_cols:
                return
            new_cols = {
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

            cursor_sr = conn.exec_driver_sql("PRAGMA table_info(screening_results)")
            existing_sr_cols = {row[1] for row in cursor_sr.fetchall()}
            if existing_sr_cols and "languages_found" not in existing_sr_cols:
                conn.exec_driver_sql("ALTER TABLE screening_results ADD COLUMN languages_found VARCHAR(200)")

            conn.commit()
    except Exception as e:
        pass


def init_db(technology: str = "golang") -> None:
    """Create all tables if they don't exist for the specified technology or all."""
    import app.models  # Ensures all models are registered with Base.metadata
    if technology == "all":
        for tech in TECHNOLOGY_DB_MAP:
            eng = get_engine_for_tech(tech)
            Base.metadata.create_all(bind=eng)
            _migrate_columns(eng)
    else:
        eng = get_engine_for_tech(technology)
        Base.metadata.create_all(bind=eng)
        _migrate_columns(eng)

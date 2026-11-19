from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..config import settings
from ..models.database import Base

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)

    # Auto-migrate SQLite schema for missing columns on existing databases
    if settings.DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                res = conn.exec_driver_sql("PRAGMA table_info(sessions)").fetchall()
                existing_cols = {row[1] for row in res}
                if existing_cols:
                    if "is_mock" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE sessions ADD COLUMN is_mock BOOLEAN DEFAULT 0 NOT NULL")
                    if "mock_reason" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE sessions ADD COLUMN mock_reason TEXT")
                    if "requested_problem_summary" not in existing_cols:
                        conn.exec_driver_sql("ALTER TABLE sessions ADD COLUMN requested_problem_summary TEXT")
                    conn.commit()
        except Exception:
            pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

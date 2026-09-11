import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Load .env variables into environment
load_dotenv()

logger = logging.getLogger("dreemfolio.database")

# Database Configuration (Reads from .env or Environment Variables)
DATABASE_URL = os.getenv("DATABASE_URL")

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
# Support both MYSQL_DATABASE and MYSQL_DB aliases
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB") or "cv_saas_db"

if DATABASE_URL and DATABASE_URL.strip():
    clean_db_url = DATABASE_URL.strip()
    if clean_db_url.startswith("postgres://"):
        clean_db_url = clean_db_url.replace("postgres://", "postgresql://", 1)
    MYSQL_URL = clean_db_url
elif MYSQL_USER and MYSQL_USER.strip():
    MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
else:
    # No explicit DB credentials provided; default directly to SQLite to avoid network hang
    MYSQL_URL = None

SQLITE_FALLBACK_URL = os.getenv("SQLITE_URL", "sqlite:////tmp/cv_saas_local.db" if os.getenv("VERCEL") else "sqlite:///./cv_saas_local.db")

# Initialize typed declarative base
class Base(DeclarativeBase):
    pass

engine = None
SessionLocal = None

def init_engine():
    global engine, SessionLocal
    # If no MySQL URL is set, jump straight to SQLite fast fallback without network delay
    if not MYSQL_URL:
        logger.info("ℹ️ No MySQL credentials specified. Initializing SQLite local database.")
        engine = create_engine(
            SQLITE_FALLBACK_URL,
            connect_args={"check_same_thread": False},
            echo=False
        )
    else:
        connected = False
        # Dual attempt: try configured host, and fallback between 127.0.0.1 and localhost (cPanel unix socket vs TCP)
        urls_to_try = [MYSQL_URL]
        if "127.0.0.1" in MYSQL_URL:
            urls_to_try.append(MYSQL_URL.replace("127.0.0.1", "localhost"))
        elif "localhost" in MYSQL_URL:
            urls_to_try.append(MYSQL_URL.replace("localhost", "127.0.0.1"))

        last_err = None
        for try_url in urls_to_try:
            try:
                candidate_engine = create_engine(
                    try_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_recycle=3600,
                    pool_pre_ping=True,
                    connect_args={"connect_timeout": 3} if "mysql" in try_url else {},
                    echo=False
                )
                with candidate_engine.connect() as test_conn:
                    engine = candidate_engine
                    connected = True
                    logger.info("✅ Successfully connected to MySQL database: %s", MYSQL_DATABASE)
                    break
            except Exception as e:
                last_err = e
                continue

        if not connected:
            logger.warning("⚠️ MySQL connection failed (%s). Falling back to SQLite local database.", last_err)
            engine = create_engine(
                SQLITE_FALLBACK_URL,
                connect_args={"check_same_thread": False},
                echo=False
            )

    # Auto-migrate missing columns for smooth upgrades
    try:
        from sqlalchemy import inspect, text
        insp = inspect(engine)
        if insp.has_table("users"):
            user_cols = {c["name"] for c in insp.get_columns("users")}
            needed_cols = [
                ("daily_copilot_kits_count", "INT NOT NULL DEFAULT 0"),
                ("daily_chat_count", "INT NOT NULL DEFAULT 0"),
                ("daily_interview_count", "INT NOT NULL DEFAULT 0"),
                ("google_id", "VARCHAR(255) NULL"),
                ("avatar_url", "VARCHAR(500) NULL"),
                ("auth_provider", "VARCHAR(50) NOT NULL DEFAULT 'email'")
            ]
            with engine.connect() as mig_conn:
                for col_name, col_def in needed_cols:
                    if col_name not in user_cols:
                        mig_conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                mig_conn.commit()
    except Exception as mig_err:
        logger.warning("Database schema check warning: %s", mig_err)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine

def get_engine():
    global engine
    if engine is None:
        init_engine()
    return engine

def get_db():
    """FastAPI Dependency for request-scoped database sessions."""
    global SessionLocal
    if SessionLocal is None:
        init_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

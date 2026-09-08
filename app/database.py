import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger("dreemfolio.database")

# MySQL Configuration (Default to XAMPP port 3306)
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "cv_saas_db")

MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
SQLITE_FALLBACK_URL = "sqlite:///./cv_saas_local.db"

# Initialize typed declarative base
class Base(DeclarativeBase):
    pass

engine = None
SessionLocal = None

def init_engine():
    global engine, SessionLocal
    try:
        # First ensure the database exists in MySQL
        import pymysql
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=int(MYSQL_PORT),
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            charset='utf8mb4'
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()

        # Connect with modern production connection pooling and auto pre-ping (connection health check)
        engine = create_engine(
            MYSQL_URL,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False
        )
        # Test connection
        with engine.connect() as test_conn:
            logger.info("✅ Successfully connected to MySQL database: %s", MYSQL_DATABASE)
    except Exception as e:
        logger.warning("⚠️ MySQL connection failed (%s). Falling back to SQLite local database.", e)
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

# Initialize on module import
init_engine()

def get_db():
    """FastAPI Dependency for request-scoped database sessions."""
    if SessionLocal is None:
        init_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

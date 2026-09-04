from datetime import datetime
from typing import List, Optional
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class User(Base):
    """
    SQLAlchemy 2.0 Typed User Model for SaaS Authentication.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Candidate")
    plan_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    subscription_status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    subscription_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    daily_ai_generations_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_pdf_downloads_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_cover_letter_downloads_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_ats_downloads_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_visual_downloads_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_cover_letter_downloads_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_generation_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(50), default="email", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to user's saved resumes
    resumes: Mapped[List["UserResume"]] = relationship(
        "UserResume", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', plan='{self.plan_tier}', admin={self.is_admin})>"


class SaasSetting(Base):
    """
    SQLAlchemy 2.0 Typed Model for dynamic SaaS system configuration & subscription rules.
    Configurable via the Admin Control Center.
    """
    __tablename__ = "saas_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<SaasSetting(key='{self.key}', value='{self.value}')>"


class UserResume(Base):
    """
    SQLAlchemy 2.0 Typed UserResume Model for saving tailored CVs,
    cover letters, styles, and configurations per user.
    """
    __tablename__ = "user_resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="My Professional Resume")
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    template_style: Mapped[str] = mapped_column(String(100), default="visual_sidebar", nullable=False)
    resume_data_json: Mapped[str] = mapped_column(Text(length=4294967295), nullable=False)  # MySQL LONGTEXT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to parent User
    user: Mapped["User"] = relationship("User", back_populates="resumes")

    def __repr__(self) -> str:
        return f"<UserResume(id={self.id}, user_id={self.user_id}, title='{self.title}')>"

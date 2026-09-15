from datetime import datetime
from typing import List, Optional
from sqlalchemy import Integer, String, Text, Boolean, DateTime, ForeignKey, Float
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
    daily_copilot_kits_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_chat_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_interview_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
    # Relationship to user's tracked job applications
    job_applications: Mapped[List["UserJobApplication"]] = relationship(
        "UserJobApplication", back_populates="user", cascade="all, delete-orphan"
    )
    # Relationship to user's bank payment slips
    bank_payment_slips: Mapped[List["BankPaymentSlip"]] = relationship(
        "BankPaymentSlip", back_populates="user", cascade="all, delete-orphan"
    )
    # Relationship to user's online gateway payment orders
    online_orders: Mapped[List["OnlinePaymentOrder"]] = relationship(
        "OnlinePaymentOrder", back_populates="user", cascade="all, delete-orphan"
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


class UserJobApplication(Base):
    """
    SQLAlchemy 2.0 Typed Model for tracking job opportunities, applications,
    and generated AI application kits per user.
    """
    __tablename__ = "user_job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Target Company")
    location: Mapped[str] = mapped_column(String(255), default="Remote", nullable=False)
    work_mode: Mapped[str] = mapped_column(String(50), default="Remote", nullable=False)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    match_score: Mapped[int] = mapped_column(Integer, default=95, nullable=False)
    job_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="wishlist", nullable=False)  # wishlist, ready_to_apply, applied, interviewing, offered, rejected
    applied_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_kit_json: Mapped[Optional[str]] = mapped_column(Text(length=4294967295), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to parent User
    user: Mapped["User"] = relationship("User", back_populates="job_applications")

    def __repr__(self) -> str:
        return f"<UserJobApplication(id={self.id}, user_id={self.user_id}, role='{self.job_title}', company='{self.company_name}', status='{self.status}')>"


class BankPaymentSlip(Base):
    """
    SQLAlchemy 2.0 Typed Model for local bank deposit slips and transfer verification.
    Enables zero-gateway-fee manual subscriptions with admin review and 1-click approval.
    """
    __tablename__ = "bank_payment_slips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    target_plan: Mapped[str] = mapped_column(String(50), nullable=False)  # 'pro', 'elite', 'sprint'
    amount_paid: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="LKR")
    slip_image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    bank_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # 'pending', 'approved', 'rejected'
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship to parent User
    user: Mapped["User"] = relationship("User", back_populates="bank_payment_slips")

    def __repr__(self) -> str:
        return f"<BankPaymentSlip(id={self.id}, user_id={self.user_id}, plan='{self.target_plan}', status='{self.status}')>"


class OnlinePaymentOrder(Base):
    """
    SQLAlchemy 2.0 Typed Model for Online Payment Gateway Orders (PayHere, etc.).
    Keeps audit records of generated hashes, IPN callbacks, payment status,
    and gateway transaction identifiers.
    """
    __tablename__ = "online_payment_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    target_plan: Mapped[str] = mapped_column(String(50), nullable=False)  # 'pro', 'elite'
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="LKR")
    gateway: Mapped[str] = mapped_column(String(50), nullable=False, default="payhere")
    status: Mapped[str] = mapped_column(String(50), default="initiated", nullable=False)  # 'initiated', 'pending', 'success', 'failed', 'canceled'
    payhere_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # VISA, MASTER, etc.
    card_holder_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    card_no_masked: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 2: Success, 0: Pending, -1: Canceled, -2: Failed
    status_message: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_ipn_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to parent User
    user: Mapped["User"] = relationship("User", back_populates="online_orders")

    def __repr__(self) -> str:
        return f"<OnlinePaymentOrder(order_id='{self.order_id}', user_id={self.user_id}, plan='{self.target_plan}', status='{self.status}')>"


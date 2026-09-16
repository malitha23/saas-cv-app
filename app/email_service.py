import os
import smtplib
import logging
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional, List, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv

logger = logging.getLogger("dreemfolio.email")

# Setup Jinja2 Template Environment for Transactional Emails
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)


def get_smtp_config() -> Dict[str, Any]:
    """Dynamically loads SMTP credentials and settings from .env."""
    load_dotenv(override=True)
    host = os.getenv("SMTP_HOST", "").strip()
    port_str = os.getenv("SMTP_PORT", "587").strip()
    try:
        port = int(port_str)
    except ValueError:
        port = 587

    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip() or user or "no-reply@dreemfolio.com"
    from_name = os.getenv("SMTP_FROM_NAME", "DreemFolio AI").strip()
    use_ssl = (port == 465) or os.getenv("SMTP_USE_SSL", "false").strip().lower() in ("true", "1")
    admin_fallback = os.getenv("ADMIN_NOTIFICATION_EMAIL", "").strip() or os.getenv("ADMIN_EMAIL", "").strip()

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_email": from_email,
        "from_name": from_name,
        "use_ssl": use_ssl,
        "admin_email": admin_fallback
    }


def get_admin_emails(db=None) -> List[str]:
    """
    Retrieves active admin recipient email addresses.
    Checks both ADMIN_NOTIFICATION_EMAIL from .env and active is_admin=True users in database.
    """
    config = get_smtp_config()
    recipients = set()
    if config["admin_email"]:
        for e in config["admin_email"].split(","):
            clean = e.strip()
            if clean and "@" in clean:
                recipients.add(clean)

    if db is not None:
        try:
            from app.models import User
            from sqlalchemy import select
            stmt = select(User.email).where(User.is_admin == True, User.is_active == True)
            db_admins = db.scalars(stmt).all()
            for a in db_admins:
                if a and "@" in a:
                    recipients.add(a.strip())
        except Exception as err:
            logger.warning("Failed to query admin users from DB: %s", err)

    if not recipients:
        # Fallback default
        recipients.add("admin@dreemfolio.com")

    return list(recipients)


def send_raw_email(to_email: str, subject: str, html_body: str, plain_body: Optional[str] = None) -> bool:
    """
    Core blocking SMTP dispatcher.
    If SMTP credentials are missing, logs simulation cleanly without throwing errors.
    """
    cfg = get_smtp_config()
    to_clean = to_email.strip()

    if not cfg["host"] or not cfg["user"]:
        logger.info(
            "📧 [SIMULATED EMAIL] To: %s | Subject: %s | Note: Configure SMTP_HOST and SMTP_USER in .env to dispatch live emails.",
            to_clean, subject
        )
        return True

    # Build MIME Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{cfg['from_name']} <{cfg['from_email']}>"
    msg["To"] = to_clean

    text_content = plain_body or "Please view this email in an HTML-compatible client."
    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if cfg["use_ssl"]:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15) as server:
                if cfg["user"] and cfg["password"]:
                    server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
                try:
                    server.starttls()
                except Exception as tls_err:
                    logger.debug("STARTTLS warning: %s", tls_err)
                if cfg["user"] and cfg["password"]:
                    server.login(cfg["user"], cfg["password"])
                server.send_message(msg)

        logger.info("✅ Transactional email successfully dispatched to: %s | Subject: %s", to_clean, subject)
        return True
    except Exception as e:
        logger.error("❌ Failed to dispatch email to %s: %s", to_clean, str(e))
        return False


def dispatch_email_in_background(to_email: str, subject: str, html_body: str, background_tasks=None):
    """Dispatches email asynchronously via FastAPI BackgroundTasks or asyncio thread pool."""
    if background_tasks is not None:
        background_tasks.add_task(send_raw_email, to_email, subject, html_body)
    else:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(asyncio.to_thread(send_raw_email, to_email, subject, html_body))
            else:
                send_raw_email(to_email, subject, html_body)
        except Exception:
            import threading
            threading.Thread(target=send_raw_email, args=(to_email, subject, html_body), daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# HIGH-LEVEL TRANSACTIONAL EMAIL DISPATCHERS
# ─────────────────────────────────────────────────────────────────────────────

def send_user_welcome_email(to_email: str, full_name: str, base_url: str = "http://localhost:8000", background_tasks=None):
    """Sends warm welcome email to new SaaS registrant."""
    template = jinja_env.get_template("emails/user_welcome.html")
    html = template.render(
        subject="Welcome to DreemFolio AI!",
        full_name=full_name or "Candidate",
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    dispatch_email_in_background(to_email, f"🚀 Welcome to DreemFolio AI, {full_name or 'Candidate'}!", html, background_tasks)


def send_admin_new_user_alert(user_email: str, full_name: str, provider: str = "Email", base_url: str = "http://localhost:8000", db=None, background_tasks=None):
    """Sends new user registration notification to system administrators."""
    template = jinja_env.get_template("emails/admin_new_user_alert.html")
    now_str = datetime.utcnow().strftime("%b %d, %Y - %I:%M %p UTC")
    html = template.render(
        subject="New User Registered on DreemFolio AI",
        full_name=full_name or "Candidate",
        user_email=user_email,
        provider=provider,
        created_at=now_str,
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    for admin in get_admin_emails(db):
        dispatch_email_in_background(admin, f"👤 New SaaS User: {full_name} ({user_email})", html, background_tasks)


def send_user_subscription_confirmed(
    to_email: str,
    full_name: str,
    plan_title: str,
    amount: float,
    currency: str,
    order_id: str,
    payment_id: str,
    duration_days: int = 30,
    base_url: str = "http://localhost:8000",
    background_tasks=None
):
    """Sends official subscription receipt / confirmation email to customer."""
    template = jinja_env.get_template("emails/user_subscription_confirmed.html")
    now_str = datetime.utcnow().strftime("%b %d, %Y - %I:%M %p UTC")
    html = template.render(
        subject=f"Your DreemFolio AI {plan_title} is Active!",
        full_name=full_name or "Customer",
        plan_title=plan_title,
        amount=amount,
        currency=currency,
        order_id=order_id,
        payment_id=payment_id,
        duration_days=duration_days,
        payment_date=now_str,
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    dispatch_email_in_background(to_email, f"🎉 Subscription Confirmed: {plan_title} - DreemFolio AI", html, background_tasks)


def send_admin_subscription_alert(
    user_email: str,
    full_name: str,
    plan_title: str,
    amount: float,
    currency: str,
    order_id: str,
    payment_id: str,
    method: str = "PayHere Gateway",
    base_url: str = "http://localhost:8000",
    db=None,
    background_tasks=None
):
    """Sends new revenue / subscription payment alert to system administrators."""
    template = jinja_env.get_template("emails/admin_subscription_alert.html")
    now_str = datetime.utcnow().strftime("%b %d, %Y - %I:%M %p UTC")
    html = template.render(
        subject=f"New Subscription: {plan_title} ({currency} {amount:.2f})",
        full_name=full_name or "Customer",
        user_email=user_email,
        plan_title=plan_title,
        amount=amount,
        currency=currency,
        order_id=order_id,
        payment_id=payment_id,
        method=method,
        payment_date=now_str,
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    for admin in get_admin_emails(db):
        dispatch_email_in_background(admin, f"💰 New Subscription: {plan_title} - {currency} {amount:.2f}", html, background_tasks)


def send_user_refund_processed(
    to_email: str,
    full_name: str,
    order_id: str,
    refund_id: str,
    amount: float,
    currency: str,
    reason: str,
    base_url: str = "http://localhost:8000",
    background_tasks=None
):
    """Sends refund notification and bank processing timeline notice to customer."""
    template = jinja_env.get_template("emails/user_refund_processed.html")
    now_str = datetime.utcnow().strftime("%b %d, %Y - %I:%M %p UTC")
    html = template.render(
        subject=f"Refund Processed for Order #{order_id}",
        full_name=full_name or "Customer",
        order_id=order_id,
        refund_id=refund_id,
        amount=amount,
        currency=currency,
        reason=reason or "Customer request / administrative refund",
        refund_date=now_str,
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    dispatch_email_in_background(to_email, f"↩️ Refund Processed for Order #{order_id} - DreemFolio AI", html, background_tasks)


def send_admin_refund_alert(
    user_email: str,
    full_name: str,
    order_id: str,
    refund_id: str,
    amount: float,
    currency: str,
    reason: str,
    admin_email: str,
    base_url: str = "http://localhost:8000",
    db=None,
    background_tasks=None
):
    """Sends refund execution audit log to system administrators."""
    template = jinja_env.get_template("emails/admin_refund_alert.html")
    now_str = datetime.utcnow().strftime("%b %d, %Y - %I:%M %p UTC")
    html = template.render(
        subject=f"Refund Executed: Order #{order_id} ({currency} {amount:.2f})",
        full_name=full_name or "Customer",
        user_email=user_email,
        order_id=order_id,
        refund_id=refund_id,
        amount=amount,
        currency=currency,
        reason=reason,
        admin_email=admin_email,
        refund_date=now_str,
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    for admin in get_admin_emails(db):
        dispatch_email_in_background(admin, f"🔔 Refund Executed: #{order_id} ({currency} {amount:.2f})", html, background_tasks)


def send_user_forgot_password(
    to_email: str,
    full_name: str,
    reset_token: str,
    base_url: str = "http://localhost:8000",
    background_tasks=None
):
    """Sends cryptographic password reset link to user."""
    template = jinja_env.get_template("emails/user_forgot_password.html")
    reset_url = f"{base_url.rstrip('/')}/reset-password?token={reset_token}"
    html = template.render(
        subject="Reset Your DreemFolio AI Password",
        full_name=full_name or "Candidate",
        reset_url=reset_url,
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    dispatch_email_in_background(to_email, "🔐 Reset Your DreemFolio AI Password", html, background_tasks)


def send_user_password_reset_success(
    to_email: str,
    full_name: str,
    base_url: str = "http://localhost:8000",
    background_tasks=None
):
    """Sends confirmation email after password has been successfully reset."""
    template = jinja_env.get_template("emails/user_password_reset_success.html")
    html = template.render(
        subject="Your DreemFolio AI Password Was Updated",
        full_name=full_name or "Candidate",
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    dispatch_email_in_background(to_email, "✅ Your DreemFolio AI Password Was Updated", html, background_tasks)


def send_admin_chargeback_alert(
    user_email: str,
    full_name: str,
    order_id: str,
    payment_id: str,
    amount: float,
    currency: str,
    target_plan: str,
    base_url: str = "http://localhost:8000",
    db=None,
    background_tasks=None
):
    """Dispatches high-priority fraud/chargeback alert to all active administrators."""
    template = jinja_env.get_template("emails/admin_chargeback_alert.html")
    now_str = datetime.utcnow().strftime("%B %d, %Y - %I:%M %p UTC")
    html = template.render(
        subject=f"🚨 Chargeback Alert: Order #{order_id} ({currency} {amount:.2f})",
        user_email=user_email,
        full_name=full_name or "Customer",
        order_id=order_id,
        payment_id=payment_id or "N/A",
        amount=amount,
        currency=currency,
        target_plan=target_plan or "pro",
        alert_date=now_str,
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    for admin in get_admin_emails(db):
        dispatch_email_in_background(admin, f"🚨 Chargeback Dispute Alert: #{order_id}", html, background_tasks)


def send_admin_user_refund_request(
    user_email: str,
    full_name: str,
    order_id: str,
    payment_id: str,
    amount: float,
    currency: str,
    target_plan: str,
    reason: str,
    base_url: str = "http://localhost:8000",
    db=None,
    background_tasks=None
):
    """Sends immediate alert to administrators when a customer submits a refund request."""
    template = jinja_env.get_template("emails/admin_refund_request.html")
    now_str = datetime.utcnow().strftime("%B %d, %Y - %I:%M %p UTC")
    html = template.render(
        subject=f"⚠️ Refund Requested: Order #{order_id} ({currency} {amount:.2f})",
        user_email=user_email,
        full_name=full_name or "Customer",
        order_id=order_id,
        payment_id=payment_id or "N/A",
        amount=amount,
        currency=currency,
        target_plan=target_plan or "pro",
        reason=reason,
        request_date=now_str,
        base_url=base_url.rstrip("/"),
        current_year=datetime.utcnow().year
    )
    for admin in get_admin_emails(db):
        dispatch_email_in_background(admin, f"⚠️ Customer Refund Request: #{order_id} - {currency} {amount:.2f}", html, background_tasks)



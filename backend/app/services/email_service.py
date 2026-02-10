"""
Async email service using aiosmtplib.

Sends welcome, forgot password, password changed,
and account locked notification emails using Jinja2 HTML templates.
"""
import logging
from pathlib import Path
from typing import Optional

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader

from app.auth.config import auth_settings

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"

# Jinja2 environment
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=True,
)


class EmailService:
    """Async email sending service."""

    @staticmethod
    async def _send_email(to_email: str, subject: str, html_body: str) -> bool:
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email address.
            subject: Email subject.
            html_body: HTML email body.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not auth_settings.smtp_username or not auth_settings.smtp_password:
            logger.warning("SMTP credentials not configured. Email not sent to %s", to_email)
            return False

        message = MIMEMultipart("alternative")
        message["From"] = f"{auth_settings.smtp_from_name} <{auth_settings.smtp_from_email}>"
        message["To"] = to_email
        message["Subject"] = subject

        html_part = MIMEText(html_body, "html")
        message.attach(html_part)

        try:
            await aiosmtplib.send(
                message,
                hostname=auth_settings.smtp_host,
                port=auth_settings.smtp_port,
                username=auth_settings.smtp_username,
                password=auth_settings.smtp_password,
                start_tls=auth_settings.smtp_use_tls,
            )
            logger.info("Email sent successfully to %s: %s", to_email, subject)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e))
            return False

    @staticmethod
    def _render_template(template_name: str, **kwargs) -> str:
        """Render a Jinja2 email template."""
        template = _jinja_env.get_template(template_name)
        return template.render(**kwargs)

    @classmethod
    async def send_welcome_email(
        cls,
        to_email: str,
        username: str,
        password: str,
        user_name: str,
    ) -> bool:
        """Send welcome email with credentials."""
        html = cls._render_template(
            "welcome_user.html",
            user_name=user_name,
            username=username,
            password=password,
        )
        return await cls._send_email(
            to_email,
            "Welcome to Reconciler System",
            html,
        )

    @classmethod
    async def send_forgot_password_email(
        cls,
        to_email: str,
        reset_token: str,
        user_name: str,
    ) -> bool:
        """Send forgot password email with reset token."""
        html = cls._render_template(
            "forgot_password.html",
            user_name=user_name,
            reset_token=reset_token,
        )
        return await cls._send_email(
            to_email,
            "Password Reset Request",
            html,
        )

    @classmethod
    async def send_password_changed_notification(
        cls,
        to_email: str,
        user_name: str,
    ) -> bool:
        """Send notification that password was changed."""
        html = cls._render_template(
            "password_changed.html",
            user_name=user_name,
        )
        return await cls._send_email(
            to_email,
            "Your Password Has Been Changed",
            html,
        )

    @classmethod
    async def send_account_locked_notification(
        cls,
        to_email: str,
        user_name: str,
        locked_minutes: int,
    ) -> bool:
        """Send notification that account has been locked."""
        html = cls._render_template(
            "account_locked.html",
            user_name=user_name,
            locked_minutes=locked_minutes,
        )
        return await cls._send_email(
            to_email,
            "Account Temporarily Locked",
            html,
        )

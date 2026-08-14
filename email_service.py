"""email_service.py — Email service for password resets and notifications.

Handles:
- Sending password reset emails
- Generating secure reset tokens
- Validating reset tokens
- Sending notifications
"""

import os
import json
import smtplib
import secrets
import hashlib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# Email configuration file location
CONFIG_FILE = os.path.expanduser("~/.config/harvest_hero/email_config.json")


class EmailService:
    """Service for sending emails and managing password resets."""

    def __init__(self):
        """Initialize email service."""
        self.config = self._load_config()
        self.reset_tokens = {}  # In-memory token storage (can be persisted to DB)

    def _load_config(self) -> dict:
        """Load email configuration from file."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading email config: {e}")
        return {}

    def is_configured(self) -> bool:
        """Check if email service is configured."""
        return bool(
            self.config.get("smtp_server") and
            self.config.get("smtp_port") and
            self.config.get("sender_email") and
            self.config.get("sender_password")
        )

    def configure(self, smtp_server: str, smtp_port: int, sender_email: str,
                  sender_password: str, organization_name: str = "Harvest Hero") -> bool:
        """Configure email service.
        
        Args:
            smtp_server: SMTP server address (e.g., smtp.gmail.com)
            smtp_port: SMTP port (usually 587 for TLS)
            sender_email: Email address to send from
            sender_password: Email password or app password
            organization_name: Organization name for emails
            
        Returns:
            True if configuration saved successfully
        """
        try:
            config = {
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "sender_email": sender_email,
                "sender_password": sender_password,
                "organization_name": organization_name,
            }
            
            # Create directory if needed
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            # Save configuration
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Update in-memory config
            self.config = config
            return True
        except Exception as e:
            print(f"Error saving email config: {e}")
            return False

    def generate_reset_token(self, username: str) -> str:
        """Generate a secure password reset token.
        
        Args:
            username: Username requesting reset
            
        Returns:
            Reset token (32 random characters)
        """
        token = secrets.token_urlsafe(32)
        # Store token with expiration (24 hours)
        self.reset_tokens[token] = {
            "username": username,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
            "used": False,
        }
        return token

    def validate_reset_token(self, token: str) -> tuple[bool, str]:
        """Validate a password reset token.
        
        Args:
            token: Reset token to validate
            
        Returns:
            Tuple of (is_valid, username or error_message)
        """
        if token not in self.reset_tokens:
            return False, "Invalid or expired token"
        
        token_data = self.reset_tokens[token]
        
        # Check if expired
        if datetime.now() > token_data["expires_at"]:
            return False, "Token has expired (24 hour limit)"
        
        # Check if already used
        if token_data["used"]:
            return False, "Token has already been used"
        
        return True, token_data["username"]

    def mark_token_used(self, token: str):
        """Mark a token as used."""
        if token in self.reset_tokens:
            self.reset_tokens[token]["used"] = True

    def send_password_reset_email(self, recipient_email: str, username: str,
                                  reset_token: str, recipient_name: str = None) -> tuple[bool, str]:
        """Send password reset email.
        
        Args:
            recipient_email: Email address to send to
            username: Username of account
            reset_token: Password reset token
            recipient_name: Full name of recipient (optional)
            
        Returns:
            Tuple of (success, message)
        """
        if not self.is_configured():
            return False, "Email service not configured"
        
        try:
            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "🌾 Harvest Hero - Password Reset Request"
            msg["From"] = self.config["sender_email"]
            msg["To"] = recipient_email
            
            org_name = self.config.get("organization_name", "Harvest Hero")
            name = recipient_name or username
            
            # Plain text version
            text = f"""
Hello {name},

You requested a password reset for your {org_name} account.

Username: {username}
Reset Token: {reset_token}

This token will expire in 24 hours.

To reset your password:
1. Open the Harvest Hero application
2. Click "Forgot Password?" on the login screen
3. Enter your username and new password
4. Paste the reset token above when prompted
5. Click "Reset Password"

If you did not request this reset, please ignore this email.

---
{org_name} - Inventory Management System
"""
            
            # HTML version
            html = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #2A6E40;">🌾 {org_name} - Password Reset</h2>
      
      <p>Hello {name},</p>
      
      <p>You requested a password reset for your {org_name} account.</p>
      
      <div style="background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <p><strong>Username:</strong> {username}</p>
        <p><strong>Reset Token:</strong></p>
        <p style="font-family: monospace; background-color: #fff; padding: 10px; border-radius: 4px; word-break: break-all;">
          {reset_token}
        </p>
      </div>
      
      <p><strong>This token will expire in 24 hours.</strong></p>
      
      <h3>To reset your password:</h3>
      <ol>
        <li>Open the Harvest Hero application</li>
        <li>Click "Forgot Password?" on the login screen</li>
        <li>Enter your username and new password</li>
        <li>Paste the reset token above when prompted</li>
        <li>Click "Reset Password"</li>
      </ol>
      
      <p style="color: #999; font-size: 12px; margin-top: 30px;">
        If you did not request this reset, please ignore this email.
      </p>
      
      <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
      <p style="color: #999; font-size: 12px;">
        {org_name} - Inventory Management System
      </p>
    </div>
  </body>
</html>
"""
            
            # Attach both versions
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))
            
            # Send email
            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["sender_email"], self.config["sender_password"])
                server.send_message(msg)
            
            return True, f"Password reset email sent to {recipient_email}"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"

    def send_notification_email(self, recipient_email: str, subject: str,
                               body: str, html_body: str = None) -> tuple[bool, str]:
        """Send a notification email.
        
        Args:
            recipient_email: Email address to send to
            subject: Email subject
            body: Plain text body
            html_body: HTML body (optional)
            
        Returns:
            Tuple of (success, message)
        """
        if not self.is_configured():
            return False, "Email service not configured"
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config["sender_email"]
            msg["To"] = recipient_email
            
            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            
            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["sender_email"], self.config["sender_password"])
                server.send_message(msg)
            
            return True, f"Email sent to {recipient_email}"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"


# Global instance
_email_service = None


def get_email_service() -> EmailService:
    """Get or create email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

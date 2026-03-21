"""
Email Sender - Sends emails with attachments via SMTP (Gmail).
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends emails with optional attachments via SMTP."""
    
    def __init__(self, smtp_config: dict):
        """
        Initialize email sender with SMTP configuration.
        
        Args:
            smtp_config: Dictionary with keys:
                - smtp_host: SMTP server (e.g., smtp.gmail.com)
                - smtp_port: Port (e.g., 587)
                - smtp_user: Email address
                - smtp_password: App password or credentials
                - from_email: Sender email address
        """
        self.smtp_host = smtp_config.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = smtp_config.get("smtp_port", 587)
        self.smtp_user = smtp_config.get("smtp_user", "")
        self.smtp_password = smtp_config.get("smtp_password", "")
        self.from_email = smtp_config.get("from_email", self.smtp_user)
    
    def send(self, 
             to_email: str, 
             subject: str, 
             body: str, 
             attachments: Optional[List[Path]] = None,
             body_type: str = "plain") -> bool:
        """
        Send an email with optional attachments.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body text
            attachments: Optional list of file paths to attach
            body_type: "plain" or "html"
            
        Returns:
            True if email sent successfully, False otherwise
        """
        import tempfile
        
        try:
            # Create boundary for multipart message
            boundary = "====JobAgentBoundary$(date +%s)===="
            
            # Create temporary email file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.eml', delete=False) as f:
                temp_path = f.name
                
                # Write headers
                f.write(f"From: {self.from_email}\n")
                f.write(f"To: {to_email}\n")
                f.write(f"Subject: {subject}\n")
                
                if attachments:
                    # Multipart email with attachments
                    f.write(f"Content-Type: multipart/mixed; boundary=\"{boundary}\"\n\n")
                    f.write(f"--{boundary}\n")
                    f.write(f"Content-Type: text/{body_type}; charset=utf-8\n\n")
                    f.write(f"{body}\n")
                    
                    # Add attachments
                    for attachment in attachments:
                        if attachment.exists():
                            import base64
                            with open(attachment, 'rb') as af:
                                encoded = base64.b64encode(af.read()).decode()
                            filename = attachment.name
                            f.write(f"\n--{boundary}\n")
                            f.write(f"Content-Type: application/octet-stream; name=\"{filename}\"\n")
                            f.write(f"Content-Transfer-Encoding: base64\n")
                            f.write(f"Content-Disposition: attachment; filename=\"{filename}\"\n\n")
                            f.write(f"{encoded}\n")
                    
                    f.write(f"--{boundary}--\n")
                else:
                    # Simple email without attachments
                    content_type = f"text/{body_type}; charset=utf-8"
                    f.write(f"Content-Type: {content_type}\n\n")
                    f.write(f"{body}\n")
            
            # Send using msmtp or direct SMTP
            result = self._send_via_msmtp(to_email, temp_path)
            
            # Clean up
            Path(temp_path).unlink(missing_ok=True)
            
            if result:
                logger.info(f"Email sent successfully to {to_email}")
            else:
                logger.error(f"Failed to send email to {to_email}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _send_via_msmtp(self, to_email: str, email_file: str) -> bool:
        """Send email using msmtp command."""
        try:
            # Build msmtp command
            cmd = [
                'msmtp',
                '--host', self.smtp_host,
                '--port', str(self.smtp_port),
                '--auth=on',
                '--user', self.smtp_user,
                '--passwordeval', f'echo {self.smtp_password}',
                '--tls',
                '--tls-starttls=on',
                '--from', self.from_email,
                to_email
            ]
            
            # Read email content
            with open(email_file, 'r') as f:
                email_content = f.read()
            
            # Run msmtp
            result = subprocess.run(
                cmd,
                input=email_content,
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
            
        except FileNotFoundError:
            logger.error("msmtp not found. Install with: sudo apt install msmtp")
            return False
        except Exception as e:
            logger.error(f"msmtp error: {e}")
            return False
    
    def send_with_cover_letter(self,
                                to_email: str,
                                job: dict,
                                cover_letter: str,
                                resume_path: Optional[Path] = None,
                                cc_email: Optional[str] = None) -> bool:
        """
        Send email with cover letter and optional resume attachment.
        
        Args:
            to_email: Recipient email address
            job: Job dictionary
            cover_letter: Cover letter text
            resume_path: Optional path to resume PDF
            cc_email: Optional CC email address
            
        Returns:
            True if sent successfully
        """
        job_title = job.get("title", "the position")
        company = job.get("company", "your organization")
        
        subject = f"Application for {job_title} - {self._get_sender_name()}"
        
        # Add resume to attachments if provided
        attachments = []
        if resume_path and resume_path.exists():
            attachments.append(resume_path)
        
        return self.send(
            to_email=to_email,
            subject=subject,
            body=cover_letter,
            attachments=attachments if attachments else None
        )
    
    def _get_sender_name(self) -> str:
        """Get sender name from email or profile."""
        if hasattr(self, 'profile'):
            return self.profile.get("name", "Applicant")
        # Try to extract name from email
        email_name = self.from_email.split('@')[0]
        return email_name.replace('.', ' ').replace('_', ' ').title()


# ── Factory function ──────────────────────────────────────────

def create_email_sender(env_vars: dict) -> EmailSender:
    """
    Create an EmailSender from environment variables.
    
    Args:
        env_vars: Dictionary with env var values
        
    Returns:
        Configured EmailSender instance
    """
    smtp_config = {
        "smtp_host": env_vars.get("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(env_vars.get("SMTP_PORT", "587")),
        "smtp_user": env_vars.get("SMTP_USER", ""),
        "smtp_password": env_vars.get("SMTP_PASSWORD", ""),
        "from_email": env_vars.get("FROM_EMAIL", env_vars.get("SMTP_USER", "")),
    }
    
    return EmailSender(smtp_config)

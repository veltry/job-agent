"""
Mailer module - Cover letter generation and email sending with attachments.
"""

from .cover_letter import CoverLetterGenerator
from .email_sender import EmailSender

__all__ = ["CoverLetterGenerator", "EmailSender"]

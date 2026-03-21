"""
Tests for Mailer module - Cover letter and email functionality.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Test Profile ─────────────────────────────────────────────

TEST_PROFILE = {
    "name": "VELMURUGAN P",
    "title": "VP, Chapter Lead - Backend Engineering",
    "current_company": "Standard Chartered Bank",
    "experience_years": 17,
    "skills": ["Java", "AWS", "Spring Boot", "API Development"],
    "preferred_roles": ["VP Chapter Lead", "Backend Lead"],
    "preferred_locations": ["Malaysia", "Singapore"],
    "preferred_work_type": ["Full-time", "Hybrid"],
    "salary_min_lpa": 36,
    "notice_period": "2 months",
    "linkedin_url": "https://linkedin.com/in/veltry"
}


# ── Cover Letter Tests ───────────────────────────────────────

def test_cover_letter_generator_init():
    """CoverLetterGenerator should initialize with profile."""
    from mailer.cover_letter import CoverLetterGenerator
    
    generator = CoverLetterGenerator(TEST_PROFILE)
    assert generator.profile == TEST_PROFILE


def test_cover_letter_generate():
    """Cover letter should contain job and profile info."""
    from mailer.cover_letter import CoverLetterGenerator
    
    job = {
        "title": "VP Engineering Lead",
        "company": "Zurich Insurance",
        "location": "Kuala Lumpur",
        "description": "Lead engineering team"
    }
    
    generator = CoverLetterGenerator(TEST_PROFILE)
    letter = generator.generate(job)
    
    assert "VP Engineering Lead" in letter
    assert "Zurich Insurance" in letter
    assert "VELMURUGAN P" in letter
    assert "17 years" in letter


def test_cover_letter_skills():
    """Cover letter should list key skills."""
    from mailer.cover_letter import CoverLetterGenerator
    
    job = {"title": "Backend Lead", "company": "Bank", "location": "SG"}
    
    generator = CoverLetterGenerator(TEST_PROFILE)
    letter = generator.generate(job)
    
    # Should contain skill bullets
    assert "• Java" in letter or "Java" in letter


def test_cover_letter_save_to_file():
    """Cover letter should save to file when path provided."""
    from mailer.cover_letter import CoverLetterGenerator
    import tempfile
    
    job = {"title": "Test Job", "company": "Test Co", "location": "KL"}
    
    generator = CoverLetterGenerator(TEST_PROFILE)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "cover.txt"
        letter = generator.generate(job, output_path)
        
        assert output_path.exists()
        with open(output_path) as f:
            saved = f.read()
        assert "Test Job" in saved


def test_generate_cover_letter_function():
    """Standalone function should work same as class."""
    from mailer.cover_letter import generate_cover_letter
    
    job = {"title": "Dev Lead", "company": "FinTech", "location": "SG"}
    
    letter = generate_cover_letter(TEST_PROFILE, job)
    
    assert "Dev Lead" in letter
    assert "FinTech" in letter


# ── Email Sender Tests ──────────────────────────────────────

def test_email_sender_init():
    """EmailSender should initialize with SMTP config."""
    from mailer.email_sender import EmailSender
    
    config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "test@gmail.com",
        "smtp_password": "password123",
        "from_email": "test@gmail.com"
    }
    
    sender = EmailSender(config)
    
    assert sender.smtp_host == "smtp.gmail.com"
    assert sender.smtp_port == 587
    assert sender.smtp_user == "test@gmail.com"


def test_create_email_sender_from_env():
    """Factory function should create sender from env vars."""
    from mailer.email_sender import create_email_sender
    
    env = {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "user@gmail.com",
        "SMTP_PASSWORD": "secret",
        "FROM_EMAIL": "user@gmail.com"
    }
    
    sender = create_email_sender(env)
    
    assert sender.smtp_user == "user@gmail.com"


def test_email_sender_send_no_attachment():
    """Send should work without attachments."""
    from mailer.email_sender import EmailSender
    
    config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "test@gmail.com",
        "smtp_password": "test",
        "from_email": "test@gmail.com"
    }
    
    sender = EmailSender(config)
    
    # This will fail without msmtp but should not crash
    # In real tests, you'd mock the subprocess
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        result = sender.send(
            to_email="hr@company.com",
            subject="Test Subject",
            body="Test body content"
        )
        
        # Should call subprocess
        mock_run.assert_called_once()


def test_email_sender_with_attachments():
    """Send should handle attachments list."""
    from mailer.email_sender import EmailSender
    import tempfile
    
    config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "test@gmail.com",
        "smtp_password": "test",
        "from_email": "test@gmail.com"
    }
    
    sender = EmailSender(config)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        pdf_path = Path(tmpdir) / "resume.pdf"
        pdf_path.write_text("PDF content")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            result = sender.send(
                to_email="hr@company.com",
                subject="Application",
                body="Please find my application",
                attachments=[pdf_path]
            )
            
            assert mock_run.called


def test_send_with_cover_letter():
    """Helper function should combine cover letter + attachment."""
    from mailer.email_sender import EmailSender
    import tempfile
    
    config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "test@gmail.com",
        "smtp_password": "test",
        "from_email": "test@gmail.com"
    }
    
    sender = EmailSender(config)
    
    job = {"title": "VP Lead", "company": "Bank"}
    cover_letter = "Dear Hiring Manager..."
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        result = sender.send_with_cover_letter(
            to_email="hr@bank.com",
            job=job,
            cover_letter=cover_letter
        )
        
        assert mock_run.called


# ── Integration Tests ────────────────────────────────────────

def test_full_workflow():
    """Test complete cover letter → email workflow."""
    from mailer.cover_letter import CoverLetterGenerator
    from mailer.email_sender import EmailSender
    import tempfile
    
    # 1. Generate cover letter
    job = {
        "title": "Engineering Director",
        "company": "OCBC",
        "location": "Singapore"
    }
    
    generator = CoverLetterGenerator(TEST_PROFILE)
    cover_letter = generator.generate(job)
    
    assert "Engineering Director" in cover_letter
    assert "OCBC" in cover_letter
    
    # 2. Send email (mocked)
    config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "test@gmail.com",
        "smtp_password": "test",
        "from_email": "test@gmail.com"
    }
    
    sender = EmailSender(config)
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        result = sender.send(
            to_email="careers@ocbc.com",
            subject=f"Application for Engineering Director - OCBC",
            body=cover_letter
        )
        
        assert mock_run.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

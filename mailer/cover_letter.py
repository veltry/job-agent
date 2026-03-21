"""
Cover Letter Generator - Creates personalized cover letters based on job and profile.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """Generates personalized cover letters for job applications."""
    
    def __init__(self, profile: dict):
        self.profile = profile
    
    def generate(self, job: dict, output_path: Optional[Path] = None) -> str:
        """
        Generate a cover letter for the given job.
        
        Args:
            job: Job dictionary with title, company, location, description
            output_path: Optional path to save the cover letter
            
        Returns:
            The generated cover letter as a string
        """
        profile = self.profile
        
        # Parse name - first element is first name
        full_name = profile.get("name", "Candidate")
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else "Candidate"
        
        # Get key skills
        skills = profile.get("skills", [])
        if isinstance(skills, list):
            key_skills = skills[:6]  # Top 6 skills
        else:
            key_skills = [s.strip() for s in str(skills).split(",")[:6]]
        
        # Get target roles
        roles = profile.get("preferred_roles", [])
        if isinstance(roles, list):
            target_role = roles[0] if roles else "Backend Engineer"
        else:
            target_role = str(roles).split(",")[0].strip()
        
        # Get experience
        experience = profile.get("experience_years", "10+")
        
        # Get current role
        current_role = profile.get("title", "Backend Engineer")
        
        # Get current company
        current_company = profile.get("current_company", "current employer")
        
        # Get notice period
        notice = profile.get("notice_period", "2 months")
        
        # Get work type
        work_types = profile.get("preferred_work_type", [])
        if isinstance(work_types, list):
            work_type_str = ", ".join(work_types[:3])
        else:
            work_type_str = str(work_types)
        
        # Format date
        date_str = datetime.now().strftime("%B %d, %Y")
        
        # Job details
        job_title = job.get("title", "the position")
        company_name = job.get("company", "your company")
        location = job.get("location", "")
        salary = job.get("salary", "competitive")
        
        # Skills bullet points
        skills_lines = "\n".join(f"• {skill.strip()}" for skill in key_skills if skill.strip())
        
        # Generate cover letter
        cover_letter = f"""Cover Letter

{date_str}

Hiring Manager,
{company_name}

Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company_name}. 
With {experience} years of experience in backend engineering and leadership, 
I am confident that I would be a valuable addition to your team.

CURRENT ROLE & EXPERTISE

I currently serve as {current_role} at {current_company}, 
where I lead backend engineering initiatives. My key competencies include:

{skills_lines}

I bring deep expertise in the banking and financial services domain, having delivered 
numerous enterprise projects for major organizations.

WHY {company_name.upper()}

I am particularly drawn to {company_name} because of its reputation in the financial 
services industry. My skills in backend development, cloud architecture, and 
team leadership align well with your requirements for this role.

I am comfortable with a notice period of {notice} and am 
available for {work_type_str} work arrangements.

ENCLOSURES

• Updated resume
• LinkedIn: {profile.get('linkedin_url', 'linkedin.com/in/veltry')}

Thank you for considering my application. I would welcome the opportunity to 
discuss how my background and skills would benefit your organization.

Best regards,
{full_name}
{location}
"""
        
        # Save to file if output path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cover_letter)
            logger.info(f"Cover letter saved to {output_path}")
        
        return cover_letter
    
    def generate_for_template(self, job: dict) -> dict:
        """
        Generate cover letter data for email template.
        
        Returns a dictionary with keys: subject, body
        """
        job_title = job.get("title", "the position")
        company_name = job.get("company", "your company")
        
        subject = f"Application for {job_title} - {full_name}"
        
        body = self.generate(job)
        
        return {
            "subject": subject,
            "body": body
        }


# ── Standalone function ──────────────────────────────────────

def generate_cover_letter(profile: dict, job: dict, output_path: Optional[Path] = None) -> str:
    """
    Convenience function to generate a cover letter.
    
    Args:
        profile: Candidate profile dictionary
        job: Job dictionary
        output_path: Optional path to save the letter
        
    Returns:
        The generated cover letter as a string
    """
    generator = CoverLetterGenerator(profile)
    return generator.generate(job, output_path)

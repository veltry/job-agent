"""
Skill Matcher - Uses Claude API to score job relevance against your skills profile.
Returns a match score (0-100) and human-readable reasons.
"""

import json
import logging
import anthropic
from typing import Tuple, List
from config.settings import Settings

logger = logging.getLogger(__name__)


class SkillMatcher:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Settings.CLAUDE_API_KEY)
        self.profile = Settings.get_skills_profile()

    async def score(self, job: dict) -> Tuple[int, List[str]]:
        """
        Score a job against the user's skills profile.
        Returns (score: int, reasons: List[str])
        """
        try:
            prompt = self._build_prompt(job)
            response = self.client.messages.create(
                model=Settings.CLAUDE_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            raw = response.content[0].text.strip()
            return self._parse_response(raw)

        except Exception as e:
            logger.error(f"Scoring failed for job {job.get('id')}: {e}")
            return 0, ["Scoring unavailable"]

    def _build_prompt(self, job: dict) -> str:
        profile = self.profile
        return f"""You are a job matching assistant. Score how well this job matches the candidate's profile.

CANDIDATE PROFILE:
- Title: {profile.get('title')}
- Experience: {profile.get('experience_years')} years
- Skills: {', '.join(profile.get('skills', []))}
- Preferred Roles: {', '.join(profile.get('preferred_roles', []))}
- Preferred Locations: {', '.join(profile.get('preferred_locations', []))}
- Preferred Work Type: {', '.join(profile.get('preferred_work_type', []))}
- Min Salary: {profile.get('salary_min_lpa')} LPA
- Preferred Industries: {', '.join(profile.get('industries_preferred', []))}
- Industries to Avoid: {', '.join(profile.get('industries_avoided', []))}

JOB LISTING:
- Title: {job.get('title')}
- Company: {job.get('company')}
- Location: {job.get('location')}
- Type: {job.get('employment_type')}
- Seniority: {job.get('seniority')}
- Salary: {job.get('salary')}
- Description: {job.get('description', '')[:1500]}

INSTRUCTIONS:
Respond ONLY with valid JSON in this exact format:
{{
  "score": <integer 0-100>,
  "reasons": [
    "<reason 1: skill or requirement that matches>",
    "<reason 2>",
    "<reason 3>"
  ],
  "concerns": [
    "<concern 1: any mismatch or red flag>"
  ]
}}

Score guidelines:
- 90-100: Perfect match, all skills align, ideal role
- 70-89: Strong match, most skills align
- 50-69: Partial match, some skills align
- Below 50: Poor match
"""

    def _parse_response(self, raw: str) -> Tuple[int, List[str]]:
        try:
            # Strip markdown fences if present
            clean = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            score = max(0, min(100, int(data.get("score", 0))))
            reasons = data.get("reasons", [])
            concerns = data.get("concerns", [])
            return score, reasons + [f"⚠️ {c}" for c in concerns]
        except Exception as e:
            logger.warning(f"Failed to parse score response: {e}\nRaw: {raw}")
            return 0, ["Could not parse match score"]

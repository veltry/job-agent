"""
Skill Matcher v2 - Uses Gemini AI with retry logic and improved prompting.
Model: gemini-2.0-flash-lite (free tier friendly)
"""

import json
import logging
import asyncio
import os
from google import genai
from google.genai import types
from typing import Tuple, List
from config.settings import Settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds


class SkillMatcher:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.profile = Settings.get_skills_profile()
        logger.info(f"🤖 Skill matcher ready (model: {Settings.GEMINI_MODEL})")

    async def score(self, job: dict) -> Tuple[int, List[str]]:
        """Score job with retry logic for rate limits."""
        await asyncio.sleep(Settings.RATE_LIMIT_SECONDS)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                prompt = self._build_prompt(job)
                response = self.client.models.generate_content(
                    model=Settings.GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=500,
                    )
                )
                response_text = response.text
                if not response_text:
                    logger.warning("  Gemini returned empty response text")
                    return 0, ["Scoring unavailable"]

                raw = response_text.strip()
                return self._parse_response(raw)

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < MAX_RETRIES:
                        wait = RETRY_DELAY * attempt
                        logger.warning(f"  Rate limited. Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})")
                        await asyncio.sleep(wait)
                        continue
                    else:
                        logger.error(f"  Rate limit exceeded after {MAX_RETRIES} attempts")
                        return 0, ["Rate limit exceeded — will retry next scan"]
                else:
                    logger.error(f"  Scoring failed for {job.get('id')}: {e}")
                    return 0, ["Scoring unavailable"]

        return 0, ["Max retries reached"]

    def _build_prompt(self, job: dict) -> str:
        profile = self.profile
        skills_str = ", ".join(profile.get("skills", []))
        roles_str = ", ".join(profile.get("preferred_roles", []))
        locations_str = ", ".join(profile.get("preferred_locations", []))

        return f"""You are an expert job matching assistant. Carefully analyze this job against the candidate profile.

=== CANDIDATE PROFILE ===
Name: {profile.get('name')}
Current Title: {profile.get('title')}
Experience: {profile.get('experience_years')} years
Technical Skills: {skills_str}
Target Roles: {roles_str}
Preferred Locations: {locations_str}
Work Type: {', '.join(profile.get('preferred_work_type', []))}
Min Salary: {profile.get('salary_min_lpa')} LPA
Preferred Industries: {', '.join(profile.get('industries_preferred', []))}
Avoid Industries: {', '.join(profile.get('industries_avoided', []))}

=== JOB LISTING ===
Title: {job.get('title')}
Company: {job.get('company')}
Location: {job.get('location')}
Employment Type: {job.get('employment_type')}
Salary: {job.get('salary')}
Source: {job.get('source', 'Unknown')}
Description:
{job.get('description', '')[:1200]}

=== INSTRUCTIONS ===
Score this job from 0-100 based on:
1. Skills match (40%) - Do required skills match candidate skills?
2. Role match (25%) - Is this role aligned with target roles?
3. Location match (20%) - Does location match preferences?
4. Seniority match (15%) - Is experience level appropriate?

Respond ONLY with valid JSON, no markdown, no extra text:
{{
  "score": <integer 0-100>,
  "reasons": [
    "<specific skill or requirement that matches>",
    "<another matching point>",
    "<third matching point>"
  ],
  "concerns": [
    "<specific mismatch or concern>"
  ],
  "summary": "<one sentence summary of fit>"
}}"""

    def _parse_response(self, raw: str) -> Tuple[int, List[str]]:
        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            # Find JSON object in response
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start >= 0 and end > start:
                clean = clean[start:end]

            data = json.loads(clean)
            score = max(0, min(100, int(data.get("score", 0))))
            reasons = data.get("reasons", [])
            concerns = data.get("concerns", [])
            summary = data.get("summary", "")

            all_reasons = reasons.copy()
            if summary:
                all_reasons.append(f"💡 {summary}")
            all_reasons += [f"⚠️ {c}" for c in concerns]

            return score, all_reasons

        except Exception as e:
            logger.warning(f"Failed to parse response: {e}\nRaw: {raw[:200]}")
            return 0, ["Could not parse match score"]

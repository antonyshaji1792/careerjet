"""
AI-Powered Job-Aware Resume Generation Service
Generates optimized resumes tailored to specific job descriptions
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

from app.services.llm_service import ask_ai
from app.ai.antigravity_resume_guard import AntigravityResumeGuard, ResumeGuardViolation
from app.models.config import AnswerCache
from app.extensions import db

logger = logging.getLogger(__name__)


class ResumeGenerationService:
    """
    AI-powered resume generation optimized for specific jobs.
    Uses structured prompts and deterministic outputs.
    """
    
    # Token limits for efficiency
    MAX_JD_TOKENS = 1000
    MAX_RESUME_TOKENS = 1500
    MAX_OUTPUT_TOKENS = 2000
    
    # Generation parameters
    TEMPERATURE = 0.3  # Low temperature for deterministic outputs
    VARIANTS_COUNT = 3  # Number of variants to generate
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.guard = AntigravityResumeGuard()
    
    def generate_job_aware_resume(
        self,
        job_description: str,
        base_resume: Dict,
        num_variants: int = 3
    ) -> List[Dict]:
        """
        Generate multiple resume variants optimized for a specific job.
        
        Args:
            job_description: Target job description
            base_resume: Base resume data (dict with sections)
            num_variants: Number of variants to generate (1-5)
        
        Returns:
            List of optimized resume variants
        """
        try:
            # Validate inputs
            self._validate_inputs(job_description, base_resume)
            
            # Extract job requirements
            job_analysis = self._analyze_job_description(job_description)
            
            # Generate variants
            variants = []
            for i in range(min(num_variants, 5)):
                variant = self._generate_single_variant(
                    job_description,
                    base_resume,
                    job_analysis,
                    variant_number=i+1
                )
                
                if variant:
                    variants.append(variant)
            
            logger.info(f"Generated {len(variants)} resume variants for user {self.user_id}")
            return variants
            
        except Exception as e:
            logger.error(f"Resume generation failed: {str(e)}")
            raise
    
    def _validate_inputs(self, job_description: str, base_resume: Dict):
        """Validate input data"""
        if not job_description or len(job_description.strip()) < 50:
            raise ValueError("Job description must be at least 50 characters")
        
        if not base_resume:
            raise ValueError("Base resume is required")
        
        required_sections = ['experience', 'skills']
        for section in required_sections:
            if section not in base_resume or not base_resume[section]:
                raise ValueError(f"Base resume must include {section}")
    
    def _analyze_job_description(self, job_description: str) -> Dict:
        """
        Extract key information from job description.
        Uses AI to identify skills, keywords, and requirements.
        """
        # Truncate JD if too long
        jd_text = self._truncate_text(job_description, self.MAX_JD_TOKENS)
        
        # Check cache first
        cache_key = self._generate_cache_key({
            'action': 'analyze_jd',
            'jd_hash': hash(jd_text)
        })
        
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info("Using cached job analysis")
            return cached
        
        # Structured prompt for job analysis
        prompt = self._build_job_analysis_prompt(jd_text)
        
        # Call AI with low temperature for consistency
        response = ask_ai(
            prompt,
            temperature=self.TEMPERATURE,
            max_tokens=500
        )
        
        # Parse response
        analysis = self._parse_json_response(response)
        
        # Validate analysis
        if not analysis or 'required_skills' not in analysis:
            raise ValueError("Failed to analyze job description")
        
        # Cache result
        self._save_to_cache(cache_key, analysis)
        
        return analysis
    
    def _generate_single_variant(
        self,
        job_description: str,
        base_resume: Dict,
        job_analysis: Dict,
        variant_number: int
    ) -> Optional[Dict]:
        """Generate a single resume variant"""
        try:
            # Generate optimized summary
            summary = self._generate_summary(
                base_resume,
                job_analysis,
                variant_number
            )
            
            # Optimize experience bullets
            experience = self._optimize_experience(
                base_resume.get('experience', []),
                job_analysis,
                variant_number
            )
            
            # Optimize skills section
            skills = self._optimize_skills(
                base_resume.get('skills', []),
                job_analysis
            )
            
            # Build complete resume
            optimized_resume = {
                'header': base_resume.get('header', {}),
                'summary': summary,
                'skills': skills,
                'experience': experience,
                'education': base_resume.get('education', []),
                'certifications': base_resume.get('certifications', []),
                'projects': base_resume.get('projects', []),
                'variant_number': variant_number,
                'optimization_metadata': {
                    'job_title': job_analysis.get('job_title', 'Unknown'),
                    'matched_skills': job_analysis.get('required_skills', [])[:10],
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
            # Validate with Antigravity Guard
            try:
                self.guard.validate_resume_structure(optimized_resume)
                self.guard.verify_factual_integrity(optimized_resume, base_resume)
            except ResumeGuardViolation as e:
                logger.warning(f"Variant {variant_number} failed guard: {str(e)}")
                return None
            
            return optimized_resume
            
        except Exception as e:
            logger.error(f"Failed to generate variant {variant_number}: {str(e)}")
            return None
    
    def _generate_summary(
        self,
        base_resume: Dict,
        job_analysis: Dict,
        variant_number: int
    ) -> str:
        """Generate optimized professional summary"""
        prompt = self._build_summary_prompt(base_resume, job_analysis, variant_number)
        
        response = ask_ai(
            prompt,
            temperature=self.TEMPERATURE + (variant_number * 0.1),  # Slight variation
            max_tokens=200
        )
        
        # Extract and clean summary
        summary = self._extract_summary_from_response(response)
        
        # Validate length (2-4 sentences)
        sentences = summary.split('.')
        if len(sentences) < 2 or len(sentences) > 5:
            logger.warning(f"Summary length unusual: {len(sentences)} sentences")
        
        return summary
    
    def _optimize_experience(
        self,
        experiences: List[Dict],
        job_analysis: Dict,
        variant_number: int
    ) -> List[Dict]:
        """Optimize experience bullet points for the job"""
        optimized = []
        
        for exp in experiences[:5]:  # Limit to 5 most recent
            optimized_exp = exp.copy()
            
            # Optimize achievements
            if 'achievements' in exp and exp['achievements']:
                optimized_achievements = self._optimize_achievements(
                    exp['achievements'],
                    exp.get('role', ''),
                    job_analysis,
                    variant_number
                )
                optimized_exp['achievements'] = optimized_achievements
            
            optimized.append(optimized_exp)
        
        return optimized
    
    def _optimize_achievements(
        self,
        achievements: List[str],
        role: str,
        job_analysis: Dict,
        variant_number: int
    ) -> List[str]:
        """Optimize achievement bullets for job relevance"""
        prompt = self._build_achievements_prompt(
            achievements,
            role,
            job_analysis,
            variant_number
        )
        
        response = ask_ai(
            prompt,
            temperature=self.TEMPERATURE + (variant_number * 0.1),
            max_tokens=400
        )
        
        # Parse achievements
        optimized = self._parse_achievements_response(response)
        
        # Validate each achievement
        validated = []
        for achievement in optimized[:6]:  # Max 6 bullets
            if len(achievement) <= self.guard.MAX_BULLET_LENGTH:
                validated.append(achievement)
        
        return validated
    
    def _optimize_skills(
        self,
        base_skills: List[str],
        job_analysis: Dict
    ) -> List[str]:
        """Optimize skills section for job match"""
        required_skills = set(s.lower() for s in job_analysis.get('required_skills', []))
        preferred_skills = set(s.lower() for s in job_analysis.get('preferred_skills', []))
        base_skills_lower = {s.lower(): s for s in base_skills}
        
        # Prioritize skills
        optimized = []
        
        # 1. Required skills that user has
        for skill_lower in required_skills:
            if skill_lower in base_skills_lower:
                optimized.append(base_skills_lower[skill_lower])
        
        # 2. Preferred skills that user has
        for skill_lower in preferred_skills:
            if skill_lower in base_skills_lower and base_skills_lower[skill_lower] not in optimized:
                optimized.append(base_skills_lower[skill_lower])
        
        # 3. Other skills from base resume
        for skill in base_skills:
            if skill not in optimized:
                optimized.append(skill)
        
        return optimized[:20]  # Max 20 skills
    
    # ========================================================================
    # Prompt Templates
    # ========================================================================
    
    def _build_job_analysis_prompt(self, job_description: str) -> str:
        """Build prompt for job description analysis"""
        return f"""Analyze this job description and extract key information.

Job Description:
{job_description}

Extract and return ONLY a JSON object with this exact structure:
{{
  "job_title": "exact job title from JD",
  "required_skills": ["skill1", "skill2", ...],
  "preferred_skills": ["skill1", "skill2", ...],
  "key_responsibilities": ["resp1", "resp2", ...],
  "experience_level": "junior/mid/senior",
  "industry": "industry name",
  "keywords": ["keyword1", "keyword2", ...]
}}

Focus on technical skills, tools, and technologies mentioned.
Return ONLY the JSON, no other text."""
    
    def _build_summary_prompt(
        self,
        base_resume: Dict,
        job_analysis: Dict,
        variant_number: int
    ) -> str:
        """Build prompt for summary generation"""
        base_summary = base_resume.get('summary', '')
        job_title = job_analysis.get('job_title', 'the role')
        required_skills = ', '.join(job_analysis.get('required_skills', [])[:5])
        
        tone_variants = {
            1: "professional and confident",
            2: "results-oriented and dynamic",
            3: "collaborative and innovative"
        }
        tone = tone_variants.get(variant_number, "professional")
        
        return f"""Rewrite this professional summary to align with the target job.

Current Summary:
{base_summary}

Target Job: {job_title}
Key Skills Needed: {required_skills}

Requirements:
- Keep it {tone}
- 2-3 sentences maximum
- Highlight relevant experience
- Include key skills: {required_skills}
- Use strong action words
- Be specific and quantifiable
- DO NOT fabricate experience or skills
- DO NOT add skills not in the original summary

Return ONLY the rewritten summary, no other text."""
    
    def _build_achievements_prompt(
        self,
        achievements: List[str],
        role: str,
        job_analysis: Dict,
        variant_number: int
    ) -> str:
        """Build prompt for achievement optimization"""
        achievements_text = '\n'.join(f"- {a}" for a in achievements)
        required_skills = ', '.join(job_analysis.get('required_skills', [])[:5])
        
        return f"""Rewrite these achievement bullets to better match the target job.

Role: {role}
Current Achievements:
{achievements_text}

Target Job Requirements: {required_skills}

Requirements:
- Rewrite each bullet to emphasize relevant skills
- Use strong action verbs (Led, Implemented, Achieved, etc.)
- Include metrics and quantifiable results
- Keep bullets under 300 characters
- Maintain factual accuracy - DO NOT fabricate
- Focus on impact and results
- Align with required skills: {required_skills}

Return bullets in this format:
BULLET: achievement text here
BULLET: achievement text here

Return ONLY the bullets, no other text."""
    
    # ========================================================================
    # Response Parsing
    # ========================================================================
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from AI response"""
        try:
            # Remove markdown code blocks
            cleaned = re.sub(r'```json\s*', '', response)
            cleaned = re.sub(r'```\s*', '', cleaned)
            cleaned = cleaned.strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            logger.error(f"Response was: {response[:200]}")
            return None
    
    def _extract_summary_from_response(self, response: str) -> str:
        """Extract summary text from AI response"""
        # Remove any markdown or extra formatting
        summary = response.strip()
        summary = re.sub(r'```.*?```', '', summary, flags=re.DOTALL)
        summary = re.sub(r'\*\*', '', summary)
        summary = re.sub(r'\n+', ' ', summary)
        
        # Ensure it ends with a period
        if not summary.endswith('.'):
            summary += '.'
        
        return summary.strip()
    
    def _parse_achievements_response(self, response: str) -> List[str]:
        """Parse achievement bullets from AI response"""
        achievements = []
        
        # Look for BULLET: prefix
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('BULLET:'):
                achievement = line.replace('BULLET:', '').strip()
                if achievement:
                    achievements.append(achievement)
            elif line.startswith('-') or line.startswith('•'):
                achievement = line[1:].strip()
                if achievement:
                    achievements.append(achievement)
        
        return achievements
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to approximate token limit"""
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        
        return text[:max_chars] + "..."
    
    def _generate_cache_key(self, data: Dict) -> str:
        """Generate cache key from data"""
        import hashlib
        key_string = json.dumps(data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get cached result"""
        try:
            cached = AnswerCache.query.filter_by(
                cache_key=cache_key,
                user_id=self.user_id
            ).first()
            
            if cached:
                return json.loads(cached.answer_text)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {str(e)}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """Save result to cache"""
        try:
            cache_entry = AnswerCache(
                user_id=self.user_id,
                cache_key=cache_key,
                question_text="job_analysis",
                answer_text=json.dumps(data)
            )
            db.session.add(cache_entry)
            db.session.commit()
        except Exception as e:
            logger.warning(f"Cache save failed: {str(e)}")
    
    def estimate_token_usage(
        self,
        job_description: str,
        base_resume: Dict,
        num_variants: int = 3
    ) -> Dict[str, int]:
        """Estimate token usage for generation"""
        # Rough estimates
        jd_tokens = len(job_description) // 4
        resume_tokens = len(json.dumps(base_resume)) // 4
        
        # Per variant: analysis + summary + achievements
        per_variant_tokens = 500 + 200 + 400
        
        total_input = jd_tokens + resume_tokens + (per_variant_tokens * num_variants)
        total_output = self.MAX_OUTPUT_TOKENS * num_variants
        
        return {
            'input_tokens': total_input,
            'output_tokens': total_output,
            'total_tokens': total_input + total_output,
            'estimated_cost_usd': (total_input + total_output) * 0.00002  # Rough GPT-4 estimate
        }

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class ResumeHealthService:
    """
    Calculates a comprehensive Resume Health Score by combining multiple quality metrics.
    Provides a single 0-100 score with detailed breakdown.
    """

    # Weights for each component (must sum to 1.0)
    WEIGHTS = {
        'ats_compatibility': 0.35,      # ATS parsing & keyword matching
        'recruiter_scan': 0.25,         # Visual hierarchy & scannability
        'skill_gap': 0.25,              # Alignment with job requirements
        'clarity': 0.15                 # Readability & professionalism
    }

    @staticmethod
    def calculate_health_score(resume_json: dict, job_description: str = None) -> Dict:
        """
        Calculates the overall resume health score.
        Returns a dict with overall score and component breakdown.
        """
        # Calculate individual components
        ats_score = ResumeHealthService._calculate_ats_score(resume_json)
        recruiter_score = ResumeHealthService._calculate_recruiter_scan_score(resume_json)
        skill_gap_score = ResumeHealthService._calculate_skill_gap_score(resume_json, job_description)
        clarity_score = ResumeHealthService._calculate_clarity_score(resume_json)

        # Weighted average
        overall_score = (
            ats_score * ResumeHealthService.WEIGHTS['ats_compatibility'] +
            recruiter_score * ResumeHealthService.WEIGHTS['recruiter_scan'] +
            skill_gap_score * ResumeHealthService.WEIGHTS['skill_gap'] +
            clarity_score * ResumeHealthService.WEIGHTS['clarity']
        )

        return {
            'overall_score': round(overall_score, 1),
            'grade': ResumeHealthService._get_grade(overall_score),
            'breakdown': {
                'ats_compatibility': {
                    'score': round(ats_score, 1),
                    'weight': ResumeHealthService.WEIGHTS['ats_compatibility'],
                    'status': ResumeHealthService._get_status(ats_score)
                },
                'recruiter_scan': {
                    'score': round(recruiter_score, 1),
                    'weight': ResumeHealthService.WEIGHTS['recruiter_scan'],
                    'status': ResumeHealthService._get_status(recruiter_score)
                },
                'skill_gap': {
                    'score': round(skill_gap_score, 1),
                    'weight': ResumeHealthService.WEIGHTS['skill_gap'],
                    'status': ResumeHealthService._get_status(skill_gap_score)
                },
                'clarity': {
                    'score': round(clarity_score, 1),
                    'weight': ResumeHealthService.WEIGHTS['clarity'],
                    'status': ResumeHealthService._get_status(clarity_score)
                }
            }
        }

    @staticmethod
    def _calculate_ats_score(resume_json: dict) -> float:
        """
        ATS Compatibility: Checks formatting, structure, and parsability.
        """
        score = 100.0
        
        # Check for required sections
        required_sections = ['header', 'experience', 'skills']
        for section in required_sections:
            if section not in resume_json or not resume_json[section]:
                score -= 15

        # Check experience structure
        experience = resume_json.get('experience', [])
        if experience:
            for job in experience:
                # Penalize missing key fields
                if not job.get('company'): score -= 5
                if not job.get('role'): score -= 5
                
                # Check achievements
                achievements = job.get('achievements', [])
                for bullet in achievements:
                    # Non-ASCII characters
                    if re.search(r'[^\x00-\x7F]+', bullet):
                        score -= 2
                    # Excessive length
                    if len(bullet) > 200:
                        score -= 3

        return max(0, min(100, score))

    @staticmethod
    def _calculate_recruiter_scan_score(resume_json: dict) -> float:
        """
        Recruiter Scan: Evaluates visual hierarchy and scannability.
        """
        score = 100.0
        
        experience = resume_json.get('experience', [])
        
        # Check for quantified achievements
        total_bullets = 0
        quantified_bullets = 0
        
        for job in experience:
            achievements = job.get('achievements', [])
            total_bullets += len(achievements)
            for bullet in achievements:
                # Look for numbers/metrics
                if re.search(r'\d+%|\$\d+|\d+\s+(?:users|clients|hours|projects)', bullet):
                    quantified_bullets += 1

        if total_bullets > 0:
            quantification_ratio = quantified_bullets / total_bullets
            if quantification_ratio < 0.3:
                score -= 20
            elif quantification_ratio < 0.5:
                score -= 10

        # Check for action verbs
        action_verbs = ['led', 'managed', 'developed', 'created', 'implemented', 'designed', 
                       'optimized', 'increased', 'reduced', 'achieved', 'launched']
        
        bullets_with_verbs = 0
        for job in experience:
            for bullet in job.get('achievements', []):
                first_word = bullet.split()[0].lower() if bullet.split() else ''
                if first_word in action_verbs:
                    bullets_with_verbs += 1

        if total_bullets > 0:
            verb_ratio = bullets_with_verbs / total_bullets
            if verb_ratio < 0.5:
                score -= 15

        return max(0, min(100, score))

    @staticmethod
    def _calculate_skill_gap_score(resume_json: dict, job_description: str = None) -> float:
        """
        Skill Gap: Measures alignment with job requirements.
        Returns 100 if no job description provided (neutral score).
        """
        if not job_description:
            return 100.0  # Neutral when no comparison available

        resume_skills = set(s.lower() for s in resume_json.get('skills', []))
        
        # Extract potential skills from job description
        jd_lower = job_description.lower()
        common_skills = ['python', 'java', 'javascript', 'react', 'node', 'sql', 'aws', 
                        'docker', 'kubernetes', 'git', 'agile', 'scrum', 'leadership']
        
        required_skills = set(skill for skill in common_skills if skill in jd_lower)
        
        if not required_skills:
            return 100.0  # No identifiable skills in JD

        matched_skills = resume_skills.intersection(required_skills)
        match_ratio = len(matched_skills) / len(required_skills)

        # Convert to 0-100 scale with severity
        if match_ratio >= 0.8:
            return 100.0
        elif match_ratio >= 0.6:
            return 85.0
        elif match_ratio >= 0.4:
            return 65.0
        elif match_ratio >= 0.2:
            return 40.0
        else:
            return 20.0

    @staticmethod
    def _calculate_clarity_score(resume_json: dict) -> float:
        """
        Clarity: Evaluates readability and professionalism.
        """
        score = 100.0
        
        # Check summary
        summary = resume_json.get('summary', '')
        if summary:
            # Too short
            if len(summary) < 100:
                score -= 10
            # Too long
            if len(summary) > 500:
                score -= 10
        else:
            score -= 15  # Missing summary

        # Check bullet consistency
        experience = resume_json.get('experience', [])
        for job in experience:
            achievements = job.get('achievements', [])
            for bullet in achievements:
                # Too short (not impactful)
                if len(bullet) < 30:
                    score -= 5
                # Starts with lowercase (unprofessional)
                if bullet and bullet[0].islower():
                    score -= 2

        return max(0, min(100, score))

    @staticmethod
    def _get_grade(score: float) -> str:
        """Converts numeric score to letter grade."""
        if score >= 90: return 'A'
        elif score >= 80: return 'B'
        elif score >= 70: return 'C'
        elif score >= 60: return 'D'
        else: return 'F'

    @staticmethod
    def _get_status(score: float) -> str:
        """Converts score to status label."""
        if score >= 85: return 'excellent'
        elif score >= 70: return 'good'
        elif score >= 50: return 'needs_improvement'
        else: return 'critical'

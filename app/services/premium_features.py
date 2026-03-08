"""
Premium-only features: Recruiter Personas, Interview Probability, Resume Analytics
"""
import logging
from typing import Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PremiumFeaturesService:
    """
    Implements premium-tier features for advanced resume optimization.
    """

    RECRUITER_PERSONAS = {
        'tech_startup': {
            'name': 'Tech Startup Recruiter',
            'priorities': ['innovation', 'speed', 'culture_fit', 'technical_depth'],
            'red_flags': ['job_hopping', 'corporate_jargon', 'lack_of_metrics'],
            'preferred_length': 'concise',
            'keywords': ['agile', 'mvp', 'scale', 'ownership', 'impact']
        },
        'enterprise': {
            'name': 'Enterprise Recruiter',
            'priorities': ['stability', 'process', 'certifications', 'team_leadership'],
            'red_flags': ['gaps_in_employment', 'lack_of_structure', 'too_casual'],
            'preferred_length': 'detailed',
            'keywords': ['compliance', 'governance', 'stakeholder', 'methodology', 'framework']
        },
        'finance': {
            'name': 'Finance Sector Recruiter',
            'priorities': ['accuracy', 'compliance', 'quantitative_skills', 'risk_management'],
            'red_flags': ['errors', 'vague_achievements', 'lack_of_certifications'],
            'preferred_length': 'detailed',
            'keywords': ['audit', 'regulatory', 'sox', 'financial_modeling', 'risk']
        },
        'creative': {
            'name': 'Creative Industry Recruiter',
            'priorities': ['portfolio', 'creativity', 'collaboration', 'vision'],
            'red_flags': ['generic_design', 'lack_of_portfolio', 'too_technical'],
            'preferred_length': 'visual',
            'keywords': ['design', 'brand', 'user_experience', 'storytelling', 'innovation']
        }
    }

    @staticmethod
    def analyze_with_persona(resume_json: dict, persona_type: str) -> Dict:
        """
        Analyze resume from a specific recruiter persona's perspective.
        """
        if persona_type not in PremiumFeaturesService.RECRUITER_PERSONAS:
            persona_type = 'tech_startup'
        
        persona = PremiumFeaturesService.RECRUITER_PERSONAS[persona_type]
        
        # Extract resume content
        summary = resume_json.get('summary', '')
        experience = resume_json.get('experience', [])
        skills = resume_json.get('skills', [])
        
        # Analyze against persona priorities
        strengths = []
        concerns = []
        score = 100
        
        # Check for preferred keywords
        all_text = summary.lower()
        for exp in experience:
            for achievement in exp.get('achievements', []):
                all_text += ' ' + achievement.lower()
        
        keyword_matches = sum(1 for kw in persona['keywords'] if kw in all_text)
        keyword_ratio = keyword_matches / len(persona['keywords'])
        
        if keyword_ratio > 0.6:
            strengths.append(f"Strong alignment with {persona['name']} priorities ({keyword_matches}/{len(persona['keywords'])} key terms)")
        elif keyword_ratio < 0.3:
            concerns.append(f"Limited use of industry-relevant terminology")
            score -= 15
        
        # Check red flags
        for flag in persona['red_flags']:
            if flag == 'job_hopping' and len(experience) > 5:
                avg_tenure = 5 / len(experience)  # Rough estimate
                if avg_tenure < 1.5:
                    concerns.append("Frequent job changes may raise stability concerns")
                    score -= 10
            elif flag == 'lack_of_metrics':
                metrics_count = sum(1 for exp in experience for ach in exp.get('achievements', []) 
                                  if any(char.isdigit() for char in ach))
                if metrics_count < len(experience) * 2:
                    concerns.append("More quantifiable achievements would strengthen impact")
                    score -= 10
        
        return {
            'persona': persona['name'],
            'score': max(0, score),
            'strengths': strengths,
            'concerns': concerns,
            'recommendations': PremiumFeaturesService._generate_persona_recommendations(persona, concerns)
        }

    @staticmethod
    def _generate_persona_recommendations(persona: dict, concerns: List[str]) -> List[str]:
        """Generate actionable recommendations based on persona analysis."""
        recommendations = []
        
        if any('terminology' in c for c in concerns):
            recommendations.append(f"Incorporate more {persona['name']}-specific keywords: {', '.join(persona['keywords'][:3])}")
        
        if any('metrics' in c for c in concerns):
            recommendations.append("Add quantifiable achievements (percentages, dollar amounts, time saved)")
        
        if any('stability' in c for c in concerns):
            recommendations.append("Emphasize long-term projects and sustained impact in each role")
        
        return recommendations

    @staticmethod
    def calculate_interview_probability(resume_json: dict, job_description: str = None) -> Dict:
        """
        Predict likelihood of getting an interview based on resume quality.
        """
        score = 0
        factors = {}
        
        # Factor 1: Completeness (30 points)
        required_sections = ['header', 'summary', 'experience', 'skills']
        completeness = sum(1 for s in required_sections if s in resume_json and resume_json[s]) / len(required_sections)
        completeness_score = completeness * 30
        score += completeness_score
        factors['completeness'] = round(completeness_score, 1)
        
        # Factor 2: Experience quality (40 points)
        experience = resume_json.get('experience', [])
        if experience:
            # Check for metrics
            total_bullets = sum(len(exp.get('achievements', [])) for exp in experience)
            metrics_bullets = sum(1 for exp in experience for ach in exp.get('achievements', []) 
                                if any(char.isdigit() for char in ach))
            
            if total_bullets > 0:
                metrics_ratio = metrics_bullets / total_bullets
                experience_score = metrics_ratio * 40
            else:
                experience_score = 0
        else:
            experience_score = 0
        
        score += experience_score
        factors['experience_quality'] = round(experience_score, 1)
        
        # Factor 3: Skill alignment (30 points if JD provided)
        if job_description:
            skills = set(s.lower() for s in resume_json.get('skills', []))
            jd_lower = job_description.lower()
            common_skills = ['python', 'java', 'javascript', 'react', 'aws', 'docker', 'sql']
            required = set(s for s in common_skills if s in jd_lower)
            
            if required:
                matched = skills.intersection(required)
                alignment_score = (len(matched) / len(required)) * 30
            else:
                alignment_score = 25  # Neutral if no skills detected
        else:
            alignment_score = 25  # Neutral without JD
        
        score += alignment_score
        factors['skill_alignment'] = round(alignment_score, 1)
        
        # Convert to probability (0-100%)
        probability = min(100, score)
        
        # Categorize
        if probability >= 80:
            category = 'Very High'
            message = 'Strong candidate - likely to receive interview'
        elif probability >= 60:
            category = 'High'
            message = 'Good chance of interview with minor improvements'
        elif probability >= 40:
            category = 'Moderate'
            message = 'Competitive but needs optimization'
        elif probability >= 20:
            category = 'Low'
            message = 'Significant improvements needed'
        else:
            category = 'Very Low'
            message = 'Major overhaul recommended'
        
        return {
            'probability': round(probability, 1),
            'category': category,
            'message': message,
            'factors': factors
        }

    @staticmethod
    def generate_resume_analytics(user_id: int) -> Dict:
        """
        Generate advanced analytics for user's resume portfolio.
        """
        from app.models import Resume
        
        resumes = Resume.query.filter_by(user_id=user_id).all()
        
        if not resumes:
            return {
                'total_resumes': 0,
                'message': 'No resumes found. Create your first resume to see analytics.'
            }
        
        # Calculate metrics
        total = len(resumes)
        
        # Average health score (if available)
        # This would integrate with ResumeHealthService
        
        # Most recent activity
        latest = max(resumes, key=lambda r: r.updated_at)
        
        # Version tracking
        versions_per_resume = {}
        for resume in resumes:
            versions_per_resume[resume.id] = len(resume.versions) if hasattr(resume, 'versions') else 1
        
        avg_versions = sum(versions_per_resume.values()) / len(versions_per_resume) if versions_per_resume else 0
        
        return {
            'total_resumes': total,
            'last_updated': latest.updated_at.isoformat(),
            'average_versions_per_resume': round(avg_versions, 1),
            'most_edited_resume': max(versions_per_resume, key=versions_per_resume.get) if versions_per_resume else None,
            'activity_trend': 'active' if (datetime.utcnow() - latest.updated_at).days < 7 else 'inactive'
        }

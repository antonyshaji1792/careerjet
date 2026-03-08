"""
Recruiter Persona Simulation
Simulates different recruiter perspectives for resume evaluation
"""

from typing import Dict, List, Optional
from enum import Enum
import logging

from app.services.llm_service import ask_ai
from app.services.ats_scoring_service import ATSScoringService
from app.models.resume import Resume

logger = logging.getLogger(__name__)


class RecruiterPersona(Enum):
    """Available recruiter personas"""
    STARTUP_CTO = "startup_cto"
    FAANG_RECRUITER = "faang_recruiter"
    HR_GENERALIST = "hr_generalist"


class PersonaAgent:
    """
    Base class for recruiter persona agents.
    Each persona has unique evaluation criteria and feedback style.
    """
    
    # Persona configuration
    PERSONA_NAME = "Generic Recruiter"
    PERSONA_DESCRIPTION = "A generic recruiter"
    TEMPERATURE = 0.3  # Low for deterministic scoring
    
    # Evaluation weights (must sum to 100)
    WEIGHTS = {
        'technical_skills': 25,
        'experience': 25,
        'education': 15,
        'achievements': 20,
        'culture_fit': 15
    }
    
    # Scoring thresholds
    THRESHOLDS = {
        'strong_hire': 85,
        'hire': 70,
        'maybe': 50,
        'no_hire': 0
    }
    
    def __init__(self):
        self.logger = logger
    
    def evaluate_resume(
        self,
        resume_data: Dict,
        job_description: Optional[str] = None
    ) -> Dict:
        """
        Evaluate resume from persona's perspective.
        
        Args:
            resume_data: Resume content
            job_description: Optional job description
        
        Returns:
            Comprehensive evaluation
        """
        try:
            # Score each component
            scores = self._score_components(resume_data, job_description)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(scores)
            
            # Determine hiring likelihood
            likelihood = self._determine_hiring_likelihood(overall_score)
            
            # Generate feedback
            feedback = self._generate_feedback(resume_data, scores, job_description)
            
            # Identify strengths and weaknesses
            strengths = self._identify_strengths(scores, resume_data)
            weaknesses = self._identify_weaknesses(scores, resume_data)
            
            return {
                'persona': self.PERSONA_NAME,
                'overall_score': round(overall_score, 1),
                'hiring_likelihood': likelihood,
                'component_scores': scores,
                'feedback': feedback,
                'strengths': strengths,
                'weaknesses': weaknesses,
                'recommendation': self._generate_recommendation(overall_score, likelihood)
            }
            
        except Exception as e:
            self.logger.error(f"Evaluation failed: {str(e)}")
            raise
    
    def _score_components(
        self,
        resume_data: Dict,
        job_description: Optional[str]
    ) -> Dict:
        """Score individual components (to be overridden by subclasses)"""
        return {
            'technical_skills': 50,
            'experience': 50,
            'education': 50,
            'achievements': 50,
            'culture_fit': 50
        }
    
    def _calculate_overall_score(self, scores: Dict) -> float:
        """Calculate weighted overall score"""
        total = 0
        for component, score in scores.items():
            weight = self.WEIGHTS.get(component, 0)
            total += (score * weight / 100)
        return total
    
    def _determine_hiring_likelihood(self, score: float) -> Dict:
        """Determine hiring likelihood based on score"""
        if score >= self.THRESHOLDS['strong_hire']:
            decision = 'strong_hire'
            probability = 90
            label = 'Strong Hire'
        elif score >= self.THRESHOLDS['hire']:
            decision = 'hire'
            probability = 70
            label = 'Hire'
        elif score >= self.THRESHOLDS['maybe']:
            decision = 'maybe'
            probability = 40
            label = 'Maybe'
        else:
            decision = 'no_hire'
            probability = 10
            label = 'No Hire'
        
        return {
            'decision': decision,
            'probability': probability,
            'label': label
        }
    
    def _generate_feedback(
        self,
        resume_data: Dict,
        scores: Dict,
        job_description: Optional[str]
    ) -> str:
        """Generate persona-specific feedback"""
        prompt = self._build_feedback_prompt(resume_data, scores, job_description)
        
        feedback = ask_ai(
            prompt,
            temperature=self.TEMPERATURE,
            max_tokens=300
        )
        
        return feedback.strip()
    
    def _build_feedback_prompt(
        self,
        resume_data: Dict,
        scores: Dict,
        job_description: Optional[str]
    ) -> str:
        """Build prompt for feedback generation (to be overridden)"""
        return f"""Provide feedback on this resume.

Resume Summary:
{self._summarize_resume(resume_data)}

Scores:
{self._format_scores(scores)}

Feedback:"""
    
    def _identify_strengths(self, scores: Dict, resume_data: Dict) -> List[str]:
        """Identify strengths based on scores"""
        strengths = []
        
        for component, score in scores.items():
            if score >= 75:
                strengths.append(self._describe_strength(component, score, resume_data))
        
        return strengths[:3]  # Top 3
    
    def _identify_weaknesses(self, scores: Dict, resume_data: Dict) -> List[str]:
        """Identify weaknesses based on scores"""
        weaknesses = []
        
        for component, score in scores.items():
            if score < 60:
                weaknesses.append(self._describe_weakness(component, score, resume_data))
        
        return weaknesses[:3]  # Top 3
    
    def _describe_strength(self, component: str, score: float, resume_data: Dict) -> str:
        """Describe a strength (to be overridden)"""
        return f"Strong {component.replace('_', ' ')}"
    
    def _describe_weakness(self, component: str, score: float, resume_data: Dict) -> str:
        """Describe a weakness (to be overridden)"""
        return f"Weak {component.replace('_', ' ')}"
    
    def _generate_recommendation(self, score: float, likelihood: Dict) -> str:
        """Generate hiring recommendation"""
        decision = likelihood['decision']
        
        recommendations = {
            'strong_hire': "Strongly recommend moving forward with interview. This candidate shows excellent potential.",
            'hire': "Recommend proceeding to interview. Candidate meets key requirements.",
            'maybe': "Consider for interview if pipeline is thin. Has some potential but concerns remain.",
            'no_hire': "Do not recommend for interview. Significant gaps in required qualifications."
        }
        
        return recommendations.get(decision, "Further review needed.")
    
    def _summarize_resume(self, resume_data: Dict) -> str:
        """Create brief summary of resume"""
        parts = []
        
        if 'summary' in resume_data:
            parts.append(f"Summary: {resume_data['summary'][:150]}")
        
        if 'skills' in resume_data:
            skills = resume_data['skills'][:8]
            parts.append(f"Skills: {', '.join(skills)}")
        
        if 'experience' in resume_data:
            exp_count = len(resume_data['experience'])
            parts.append(f"Experience: {exp_count} positions")
        
        return '\n'.join(parts)
    
    def _format_scores(self, scores: Dict) -> str:
        """Format scores for display"""
        lines = []
        for component, score in scores.items():
            lines.append(f"- {component.replace('_', ' ').title()}: {score}/100")
        return '\n'.join(lines)


class StartupCTOAgent(PersonaAgent):
    """
    Startup CTO persona - focuses on hands-on skills, versatility, and speed.
    """
    
    PERSONA_NAME = "Startup CTO"
    PERSONA_DESCRIPTION = "Technical leader at a fast-growing startup"
    TEMPERATURE = 0.3
    
    # Startup CTOs prioritize technical skills and versatility
    WEIGHTS = {
        'technical_skills': 35,
        'experience': 20,
        'education': 10,
        'achievements': 25,
        'culture_fit': 10
    }
    
    # More lenient thresholds (startups need to move fast)
    THRESHOLDS = {
        'strong_hire': 80,
        'hire': 65,
        'maybe': 45,
        'no_hire': 0
    }
    
    def _score_components(self, resume_data: Dict, job_description: Optional[str]) -> Dict:
        """Score from startup CTO perspective"""
        scores = {}
        
        # Technical skills (most important)
        skills = resume_data.get('skills', [])
        modern_tech = ['python', 'javascript', 'react', 'node', 'docker', 'kubernetes', 'aws', 'gcp']
        modern_count = sum(1 for skill in skills if any(tech in skill.lower() for tech in modern_tech))
        scores['technical_skills'] = min(100, (modern_count / 5) * 100)
        
        # Experience (quality over quantity)
        experience = resume_data.get('experience', [])
        if experience:
            # Look for startup experience, full-stack, ownership
            startup_keywords = ['startup', 'founding', 'full-stack', 'led', 'built from scratch']
            exp_score = 0
            for exp in experience:
                exp_text = str(exp).lower()
                if any(kw in exp_text for kw in startup_keywords):
                    exp_score += 30
            scores['experience'] = min(100, exp_score + 40)
        else:
            scores['experience'] = 20
        
        # Education (less important for startups)
        education = resume_data.get('education', [])
        scores['education'] = 70 if education else 40
        
        # Achievements (very important - impact focus)
        achievements_score = self._score_achievements_startup(resume_data)
        scores['achievements'] = achievements_score
        
        # Culture fit (scrappy, self-starter)
        culture_score = self._score_culture_fit_startup(resume_data)
        scores['culture_fit'] = culture_score
        
        return scores
    
    def _score_achievements_startup(self, resume_data: Dict) -> float:
        """Score achievements from startup perspective"""
        experience = resume_data.get('experience', [])
        
        impact_keywords = ['built', 'launched', '0 to 1', 'scaled', 'grew', 'increased', 'reduced']
        metric_pattern = r'\d+[%xX]|\$\d+[KMB]?|\d+\+\s*(users|customers)'
        
        score = 40  # Base
        
        for exp in experience:
            achievements = exp.get('achievements', []) if isinstance(exp, dict) else []
            for achievement in achievements:
                achievement_str = str(achievement).lower()
                
                # Has impact keywords
                if any(kw in achievement_str for kw in impact_keywords):
                    score += 10
                
                # Has metrics
                import re
                if re.search(metric_pattern, achievement_str):
                    score += 15
        
        return min(100, score)
    
    def _score_culture_fit_startup(self, resume_data: Dict) -> float:
        """Score culture fit for startup"""
        summary = resume_data.get('summary', '').lower()
        experience = resume_data.get('experience', [])
        
        fit_keywords = ['fast-paced', 'startup', 'agile', 'self-starter', 'ownership', 'scrappy']
        
        score = 50  # Base
        
        # Check summary
        for keyword in fit_keywords:
            if keyword in summary:
                score += 10
        
        # Check for diverse experience
        if len(experience) >= 2:
            score += 10
        
        return min(100, score)
    
    def _build_feedback_prompt(self, resume_data: Dict, scores: Dict, job_description: Optional[str]) -> str:
        """Build startup CTO feedback prompt"""
        return f"""You are a Startup CTO evaluating a candidate. You care about:
- Modern technical skills and hands-on ability
- Track record of building and shipping products
- Ability to wear multiple hats
- Speed and execution

Resume Summary:
{self._summarize_resume(resume_data)}

Scores:
{self._format_scores(scores)}

Provide direct, practical feedback (2-3 sentences) on whether this person can ship code and move fast.

Feedback:"""
    
    def _describe_strength(self, component: str, score: float, resume_data: Dict) -> str:
        """Describe strength from startup perspective"""
        descriptions = {
            'technical_skills': "Strong modern tech stack - can hit the ground running",
            'experience': "Proven track record of building and shipping products",
            'achievements': "Clear impact and ownership mentality",
            'culture_fit': "Demonstrates startup mindset and versatility"
        }
        return descriptions.get(component, f"Strong {component.replace('_', ' ')}")
    
    def _describe_weakness(self, component: str, score: float, resume_data: Dict) -> str:
        """Describe weakness from startup perspective"""
        descriptions = {
            'technical_skills': "Limited modern tech stack - may need ramp-up time",
            'experience': "Lacks hands-on product building experience",
            'achievements': "Missing quantifiable impact and ownership examples",
            'culture_fit': "Unclear if comfortable with startup pace and ambiguity"
        }
        return descriptions.get(component, f"Weak {component.replace('_', ' ')}")


class FAANGRecruiterAgent(PersonaAgent):
    """
    FAANG recruiter persona - focuses on prestige, scale, and bar-raising.
    """
    
    PERSONA_NAME = "FAANG Recruiter"
    PERSONA_DESCRIPTION = "Recruiter at a top-tier tech company"
    TEMPERATURE = 0.3
    
    # FAANG prioritizes education, experience quality, and high bar
    WEIGHTS = {
        'technical_skills': 30,
        'experience': 25,
        'education': 20,
        'achievements': 20,
        'culture_fit': 5
    }
    
    # High bar - strict thresholds
    THRESHOLDS = {
        'strong_hire': 90,
        'hire': 75,
        'maybe': 60,
        'no_hire': 0
    }
    
    def _score_components(self, resume_data: Dict, job_description: Optional[str]) -> Dict:
        """Score from FAANG perspective"""
        scores = {}
        
        # Technical skills (depth and breadth)
        skills = resume_data.get('skills', [])
        faang_tech = ['python', 'java', 'c++', 'go', 'distributed systems', 'algorithms', 'system design']
        faang_count = sum(1 for skill in skills if any(tech in skill.lower() for tech in faang_tech))
        scores['technical_skills'] = min(100, (faang_count / 4) * 100)
        
        # Experience (prestige and scale)
        experience = resume_data.get('experience', [])
        exp_score = self._score_experience_faang(experience)
        scores['experience'] = exp_score
        
        # Education (very important - top schools)
        education = resume_data.get('education', [])
        edu_score = self._score_education_faang(education)
        scores['education'] = edu_score
        
        # Achievements (scale and impact)
        achievements_score = self._score_achievements_faang(resume_data)
        scores['achievements'] = achievements_score
        
        # Culture fit (bar-raiser, leadership principles)
        culture_score = self._score_culture_fit_faang(resume_data)
        scores['culture_fit'] = culture_score
        
        return scores
    
    def _score_experience_faang(self, experience: List) -> float:
        """Score experience from FAANG perspective"""
        if not experience:
            return 30
        
        score = 40  # Base
        
        prestige_companies = ['google', 'facebook', 'meta', 'amazon', 'apple', 'microsoft', 'netflix']
        scale_keywords = ['million', 'billion', 'scale', 'distributed', 'global']
        
        for exp in experience:
            exp_text = str(exp).lower()
            company = exp.get('company', '').lower() if isinstance(exp, dict) else ''
            
            # Prestige company
            if any(pc in company for pc in prestige_companies):
                score += 20
            
            # Scale indicators
            if any(kw in exp_text for kw in scale_keywords):
                score += 15
        
        return min(100, score)
    
    def _score_education_faang(self, education: List) -> float:
        """Score education from FAANG perspective"""
        if not education:
            return 40
        
        score = 50  # Base
        
        top_schools = ['stanford', 'mit', 'berkeley', 'carnegie mellon', 'harvard', 'princeton']
        cs_degrees = ['computer science', 'cs', 'software engineering', 'electrical engineering']
        
        for edu in education:
            edu_text = str(edu).lower()
            institution = edu.get('institution', '').lower() if isinstance(edu, dict) else ''
            degree = edu.get('degree', '').lower() if isinstance(edu, dict) else ''
            
            # Top school
            if any(school in institution for school in top_schools):
                score += 30
            
            # CS degree
            if any(deg in degree for deg in cs_degrees):
                score += 20
        
        return min(100, score)
    
    def _score_achievements_faang(self, resume_data: Dict) -> float:
        """Score achievements from FAANG perspective"""
        experience = resume_data.get('experience', [])
        
        scale_keywords = ['million', 'billion', 'global', 'distributed']
        leadership_keywords = ['led', 'managed', 'directed', 'mentored']
        
        score = 40  # Base
        
        for exp in experience:
            achievements = exp.get('achievements', []) if isinstance(exp, dict) else []
            for achievement in achievements:
                achievement_str = str(achievement).lower()
                
                # Scale
                if any(kw in achievement_str for kw in scale_keywords):
                    score += 15
                
                # Leadership
                if any(kw in achievement_str for kw in leadership_keywords):
                    score += 10
        
        return min(100, score)
    
    def _score_culture_fit_faang(self, resume_data: Dict) -> float:
        """Score culture fit for FAANG"""
        summary = resume_data.get('summary', '').lower()
        
        fit_keywords = ['leadership', 'innovation', 'customer', 'impact', 'excellence']
        
        score = 60  # Base (less critical than other factors)
        
        for keyword in fit_keywords:
            if keyword in summary:
                score += 8
        
        return min(100, score)
    
    def _build_feedback_prompt(self, resume_data: Dict, scores: Dict, job_description: Optional[str]) -> str:
        """Build FAANG recruiter feedback prompt"""
        return f"""You are a FAANG recruiter evaluating a candidate. You have a high bar and care about:
- Top-tier education and prestigious company experience
- Working at scale (millions/billions of users)
- Technical depth and breadth
- Leadership and impact

Resume Summary:
{self._summarize_resume(resume_data)}

Scores:
{self._format_scores(scores)}

Provide professional feedback (2-3 sentences) on whether this candidate meets the FAANG bar.

Feedback:"""
    
    def _describe_strength(self, component: str, score: float, resume_data: Dict) -> str:
        """Describe strength from FAANG perspective"""
        descriptions = {
            'technical_skills': "Strong technical foundation with relevant depth",
            'experience': "Impressive track record at scale",
            'education': "Top-tier educational background",
            'achievements': "Demonstrated impact at significant scale"
        }
        return descriptions.get(component, f"Strong {component.replace('_', ' ')}")
    
    def _describe_weakness(self, component: str, score: float, resume_data: Dict) -> str:
        """Describe weakness from FAANG perspective"""
        descriptions = {
            'technical_skills': "Technical skills don't demonstrate required depth",
            'experience': "Limited experience at scale or prestigious companies",
            'education': "Educational background below typical bar",
            'achievements': "Achievements lack scale and measurable impact"
        }
        return descriptions.get(component, f"Weak {component.replace('_', ' ')}")


class HRGeneralistAgent(PersonaAgent):
    """
    HR Generalist persona - focuses on completeness, professionalism, and fit.
    """
    
    PERSONA_NAME = "HR Generalist"
    PERSONA_DESCRIPTION = "HR professional screening candidates"
    TEMPERATURE = 0.3
    
    # HR balances all factors
    WEIGHTS = {
        'technical_skills': 20,
        'experience': 25,
        'education': 20,
        'achievements': 15,
        'culture_fit': 20
    }
    
    # Moderate thresholds
    THRESHOLDS = {
        'strong_hire': 85,
        'hire': 70,
        'maybe': 55,
        'no_hire': 0
    }
    
    def _score_components(self, resume_data: Dict, job_description: Optional[str]) -> Dict:
        """Score from HR perspective"""
        scores = {}
        
        # Technical skills (basic check)
        skills = resume_data.get('skills', [])
        scores['technical_skills'] = min(100, len(skills) * 10)
        
        # Experience (stability and progression)
        experience = resume_data.get('experience', [])
        exp_score = self._score_experience_hr(experience)
        scores['experience'] = exp_score
        
        # Education (completeness)
        education = resume_data.get('education', [])
        scores['education'] = 80 if education else 50
        
        # Achievements (professionalism)
        achievements_score = self._score_achievements_hr(resume_data)
        scores['achievements'] = achievements_score
        
        # Culture fit (most important for HR)
        culture_score = self._score_culture_fit_hr(resume_data)
        scores['culture_fit'] = culture_score
        
        return scores
    
    def _score_experience_hr(self, experience: List) -> float:
        """Score experience from HR perspective"""
        if not experience:
            return 30
        
        score = 50  # Base
        
        # Stability (not too many job hops)
        if len(experience) <= 5:
            score += 15
        
        # Progression (increasing responsibility)
        titles = [exp.get('role', '').lower() if isinstance(exp, dict) else '' for exp in experience]
        if any('senior' in t or 'lead' in t for t in titles):
            score += 20
        
        # Completeness (all fields filled)
        complete_count = sum(1 for exp in experience if isinstance(exp, dict) and 
                           exp.get('company') and exp.get('role') and exp.get('duration'))
        if complete_count == len(experience):
            score += 15
        
        return min(100, score)
    
    def _score_achievements_hr(self, resume_data: Dict) -> float:
        """Score achievements from HR perspective"""
        experience = resume_data.get('experience', [])
        
        score = 50  # Base
        
        # Has achievements listed
        total_achievements = 0
        for exp in experience:
            if isinstance(exp, dict):
                achievements = exp.get('achievements', [])
                total_achievements += len(achievements)
        
        if total_achievements >= 5:
            score += 30
        elif total_achievements >= 3:
            score += 20
        
        return min(100, score)
    
    def _score_culture_fit_hr(self, resume_data: Dict) -> float:
        """Score culture fit from HR perspective"""
        summary = resume_data.get('summary', '')
        
        score = 50  # Base
        
        # Has professional summary
        if summary and len(summary) > 50:
            score += 20
        
        # Professional language
        professional_keywords = ['professional', 'team', 'collaborative', 'communication', 'dedicated']
        for keyword in professional_keywords:
            if keyword in summary.lower():
                score += 6
        
        return min(100, score)
    
    def _build_feedback_prompt(self, resume_data: Dict, scores: Dict, job_description: Optional[str]) -> str:
        """Build HR generalist feedback prompt"""
        return f"""You are an HR Generalist screening a candidate. You care about:
- Complete and professional resume
- Stable work history with progression
- Good cultural fit and soft skills
- Meeting basic job requirements

Resume Summary:
{self._summarize_resume(resume_data)}

Scores:
{self._format_scores(scores)}

Provide professional, balanced feedback (2-3 sentences) on this candidate's fit.

Feedback:"""
    
    def _describe_strength(self, component: str, score: float, resume_data: Dict) -> str:
        """Describe strength from HR perspective"""
        descriptions = {
            'technical_skills': "Good technical skill coverage",
            'experience': "Solid work history with clear progression",
            'education': "Strong educational background",
            'achievements': "Well-documented accomplishments",
            'culture_fit': "Excellent cultural fit indicators"
        }
        return descriptions.get(component, f"Strong {component.replace('_', ' ')}")
    
    def _describe_weakness(self, component: str, score: float, resume_data: Dict) -> str:
        """Describe weakness from HR perspective"""
        descriptions = {
            'technical_skills': "Limited technical skills listed",
            'experience': "Work history shows gaps or frequent changes",
            'education': "Educational background needs strengthening",
            'achievements': "Achievements not well documented",
            'culture_fit': "Cultural fit unclear from resume"
        }
        return descriptions.get(component, f"Weak {component.replace('_', ' ')}")


class RecruiterPersonaSimulation:
    """
    Main service for recruiter persona simulation.
    Manages multiple personas and provides comparative analysis.
    """
    
    PERSONAS = {
        RecruiterPersona.STARTUP_CTO: StartupCTOAgent,
        RecruiterPersona.FAANG_RECRUITER: FAANGRecruiterAgent,
        RecruiterPersona.HR_GENERALIST: HRGeneralistAgent
    }
    
    def __init__(self):
        self.logger = logger
    
    def evaluate_with_persona(
        self,
        persona: RecruiterPersona,
        resume_id: int,
        user_id: int,
        job_description: Optional[str] = None
    ) -> Dict:
        """
        Evaluate resume with specific persona.
        
        Args:
            persona: Recruiter persona to use
            resume_id: Resume ID
            user_id: User ID
            job_description: Optional job description
        
        Returns:
            Persona evaluation
        """
        try:
            # Get resume
            resume = Resume.query.filter_by(
                id=resume_id,
                user_id=user_id
            ).first()
            
            if not resume:
                raise ValueError("Resume not found")
            
            # Get persona agent
            agent_class = self.PERSONAS.get(persona)
            if not agent_class:
                raise ValueError(f"Invalid persona: {persona}")
            
            agent = agent_class()
            
            # Evaluate
            evaluation = agent.evaluate_resume(
                resume_data=resume.content_json,
                job_description=job_description
            )
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Persona evaluation failed: {str(e)}")
            raise
    
    def evaluate_with_all_personas(
        self,
        resume_id: int,
        user_id: int,
        job_description: Optional[str] = None
    ) -> Dict:
        """
        Evaluate resume with all personas for comparison.
        
        Args:
            resume_id: Resume ID
            user_id: User ID
            job_description: Optional job description
        
        Returns:
            Comparative analysis from all personas
        """
        try:
            evaluations = {}
            
            for persona in RecruiterPersona:
                evaluation = self.evaluate_with_persona(
                    persona=persona,
                    resume_id=resume_id,
                    user_id=user_id,
                    job_description=job_description
                )
                evaluations[persona.value] = evaluation
            
            # Generate comparison
            comparison = self._generate_comparison(evaluations)
            
            return {
                'evaluations': evaluations,
                'comparison': comparison
            }
            
        except Exception as e:
            self.logger.error(f"Multi-persona evaluation failed: {str(e)}")
            raise
    
    def _generate_comparison(self, evaluations: Dict) -> Dict:
        """Generate comparison across personas"""
        scores = {persona: eval['overall_score'] for persona, eval in evaluations.items()}
        
        avg_score = sum(scores.values()) / len(scores)
        highest = max(scores.items(), key=lambda x: x[1])
        lowest = min(scores.items(), key=lambda x: x[1])
        
        # Consensus check
        hiring_decisions = [eval['hiring_likelihood']['decision'] for eval in evaluations.values()]
        consensus = len(set(hiring_decisions)) == 1
        
        return {
            'average_score': round(avg_score, 1),
            'highest_score': {'persona': highest[0], 'score': highest[1]},
            'lowest_score': {'persona': lowest[0], 'score': lowest[1]},
            'score_variance': round(max(scores.values()) - min(scores.values()), 1),
            'consensus': consensus,
            'consensus_decision': hiring_decisions[0] if consensus else 'mixed'
        }

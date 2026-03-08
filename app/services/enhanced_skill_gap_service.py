"""
Enhanced Skill Gap Analysis Service
Integrates with SkillExtractionService and skill intelligence database
"""

from typing import Dict, List, Optional, Tuple
from collections import Counter
import logging

from app.models.skill_intelligence import (
    ResumeSkillExtracted,
    JobSkillExtracted,
    SkillGapAnalysis,
    SkillImpactScore,
    ProficiencyLevel
)
from app.services.skill_extraction_service import SkillExtractionService
from app.extensions import db

logger = logging.getLogger(__name__)


class GapSeverity:
    """Gap severity levels"""
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


class EnhancedSkillGapService:
    """
    Enhanced skill gap analysis with database integration.
    Provides explainable, actionable insights.
    """
    
    # ATS impact scores per gap type
    ATS_IMPACT_SCORES = {
        'missing_mandatory': 15.0,      # Critical impact
        'missing_preferred': 8.0,       # High impact
        'missing_nice_to_have': 3.0,    # Medium impact
        'weak_proficiency': 5.0,        # Medium impact
        'matched_strong': 2.0,          # Positive impact
        'matched_weak': 1.0             # Minimal positive impact
    }
    
    # Proficiency thresholds
    WEAK_PROFICIENCY_LEVELS = [
        ProficiencyLevel.BEGINNER,
        ProficiencyLevel.UNKNOWN
    ]
    
    STRONG_PROFICIENCY_LEVELS = [
        ProficiencyLevel.ADVANCED,
        ProficiencyLevel.EXPERT
    ]
    
    def __init__(self):
        self.logger = logger
        self.extraction_service = SkillExtractionService()
    
    # ========================================================================
    # Main Analysis Methods
    # ========================================================================
    
    def analyze_gap(
        self,
        resume_id: int,
        job_id: int,
        user_id: int,
        save_to_db: bool = True,
        force_refresh: bool = False
    ) -> Dict:
        """
        Complete skill gap analysis between resume and job.
        
        Args:
            resume_id: Resume ID
            job_id: Job ID
            user_id: User ID
            save_to_db: Whether to save analysis to database
            force_refresh: Whether to ignore cached results
        
        Returns:
            Complete gap analysis with scores and recommendations
        """
        try:
            # Check for existing analysis (cache)
            if not force_refresh:
                cached = SkillGapAnalysis.query.filter_by(
                    resume_id=resume_id,
                    job_id=job_id,
                    user_id=user_id
                ).order_by(SkillGapAnalysis.created_at.desc()).first()
                
                if cached:
                    self.logger.info(f"Returning cached gap analysis for resume {resume_id}, job {job_id}")
                    return cached.to_dict()

            # Get extracted skills from database
            resume_skills = ResumeSkillExtracted.query.filter_by(
                resume_id=resume_id
            ).all()
            
            job_skills = JobSkillExtracted.query.filter_by(
                job_id=job_id
            ).all()
            
            if not resume_skills and not job_skills:
                # If neither has skills, it's an edge case
                self.logger.warning(f"No skills found for resume {resume_id} and job {job_id}")
                # We still might want to return an empty analysis rather than raising
                if not resume_skills and not job_skills:
                    raise ValueError("Skills not extracted for either resume or job.")
            
            # Perform analysis
            analysis = self._perform_gap_analysis(resume_skills, job_skills)
            
            # Calculate scores
            ats_impact = self._calculate_ats_impact(analysis)
            hiring_relevance = self._calculate_hiring_relevance(analysis)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analysis)
            
            # Build complete result
            result = {
                'summary': {
                    'total_job_skills': len(job_skills),
                    'total_resume_skills': len(resume_skills),
                    'matched_skills': len(analysis['matched']),
                    'missing_mandatory': len(analysis['missing_mandatory']),
                    'missing_preferred': len(analysis['missing_preferred']),
                    'missing_nice_to_have': len(analysis['missing_nice_to_have']),
                    'weak_proficiency': len(analysis['weak_proficiency']),
                    'match_percentage': self._calculate_match_percentage(analysis),
                    'current_ats_score': ats_impact['current_score'],
                    'potential_ats_score': ats_impact['potential_score'],
                    'hiring_relevance_score': hiring_relevance['overall_score']
                },
                'gaps': {
                    'missing_mandatory': analysis['missing_mandatory'],
                    'missing_preferred': analysis['missing_preferred'],
                    'missing_nice_to_have': analysis['missing_nice_to_have'],
                    'weak_proficiency': analysis['weak_proficiency']
                },
                'matched_skills': analysis['matched'],
                'gap_details': self._build_gap_details(analysis),
                'ats_impact': ats_impact,
                'hiring_relevance': hiring_relevance,
                'recommendations': recommendations,
                'explainability': self._generate_explainability(analysis, ats_impact)
            }
            
            # Save to database if requested
            if save_to_db:
                self._save_analysis_to_db(
                    user_id=user_id,
                    resume_id=resume_id,
                    job_id=job_id,
                    analysis_result=result
                )
            
            self.logger.info(f"Gap analysis complete: {result['summary']['match_percentage']}% match")
            return result
            
        except Exception as e:
            self.logger.error(f"Gap analysis failed: {str(e)}")
            raise
    
    # ========================================================================
    # Core Analysis Logic
    # ========================================================================
    
    def _perform_gap_analysis(
        self,
        resume_skills: List[ResumeSkillExtracted],
        job_skills: List[JobSkillExtracted]
    ) -> Dict:
        """Perform core gap analysis"""
        
        # Build skill maps
        resume_map = {
            skill.skill_name_normalized: skill
            for skill in resume_skills
        }
        
        job_map = {
            skill.skill_name_normalized: skill
            for skill in job_skills
        }
        
        # Classify gaps
        missing_mandatory = []
        missing_preferred = []
        missing_nice_to_have = []
        weak_proficiency = []
        matched = []
        
        # Check each job skill
        for job_skill in job_skills:
            skill_key = job_skill.skill_name_normalized
            
            if skill_key in resume_map:
                # Skill is present
                resume_skill = resume_map[skill_key]
                
                # Check proficiency
                if resume_skill.proficiency_level in self.WEAK_PROFICIENCY_LEVELS:
                    weak_proficiency.append({
                        'skill_name': job_skill.skill_name,
                        'skill_key': skill_key,
                        'current_proficiency': resume_skill.proficiency_level,
                        'required_proficiency': 'intermediate',  # Assumed minimum
                        'job_requirement': job_skill.requirement_type,
                        'ats_weight': job_skill.ats_weight,
                        'severity': self._determine_severity(job_skill.requirement_type, 'weak')
                    })
                
                # Add to matched
                matched.append({
                    'skill_name': job_skill.skill_name,
                    'skill_key': skill_key,
                    'proficiency': resume_skill.proficiency_level,
                    'years_experience': resume_skill.years_of_experience,
                    'job_requirement': job_skill.requirement_type,
                    'ats_weight': job_skill.ats_weight
                })
            else:
                # Skill is missing
                gap_data = {
                    'skill_name': job_skill.skill_name,
                    'skill_key': skill_key,
                    'category': job_skill.category,
                    'requirement_type': job_skill.requirement_type,
                    'priority_score': job_skill.priority_score,
                    'ats_weight': job_skill.ats_weight,
                    'market_demand': job_skill.market_demand_score,
                    'severity': self._determine_severity(job_skill.requirement_type, 'missing')
                }
                
                if job_skill.requirement_type == 'mandatory':
                    missing_mandatory.append(gap_data)
                elif job_skill.requirement_type == 'preferred':
                    missing_preferred.append(gap_data)
                else:
                    missing_nice_to_have.append(gap_data)
        
        return {
            'missing_mandatory': missing_mandatory,
            'missing_preferred': missing_preferred,
            'missing_nice_to_have': missing_nice_to_have,
            'weak_proficiency': weak_proficiency,
            'matched': matched
        }
    
    def _determine_severity(self, requirement_type: str, gap_type: str) -> str:
        """Determine gap severity"""
        if gap_type == 'missing':
            if requirement_type == 'mandatory':
                return GapSeverity.HIGH
            elif requirement_type == 'preferred':
                return GapSeverity.MEDIUM
            else:
                return GapSeverity.LOW
        else:  # weak proficiency
            if requirement_type == 'mandatory':
                return GapSeverity.MEDIUM
            else:
                return GapSeverity.LOW
    
    # ========================================================================
    # Scoring Methods
    # ========================================================================
    
    def _calculate_ats_impact(self, analysis: Dict) -> Dict:
        """Calculate ATS score impact"""
        
        # Current score (what you have)
        current_score = 0.0
        
        # Add points for matched skills
        for skill in analysis['matched']:
            if skill['proficiency'] in self.STRONG_PROFICIENCY_LEVELS:
                current_score += self.ATS_IMPACT_SCORES['matched_strong']
            else:
                current_score += self.ATS_IMPACT_SCORES['matched_weak']
        
        # Deduct points for weak proficiency
        for skill in analysis['weak_proficiency']:
            current_score -= self.ATS_IMPACT_SCORES['weak_proficiency'] * 0.5
        
        # Potential score (if all gaps filled)
        potential_score = current_score
        
        # Add potential gains
        for skill in analysis['missing_mandatory']:
            potential_score += self.ATS_IMPACT_SCORES['missing_mandatory']
        
        for skill in analysis['missing_preferred']:
            potential_score += self.ATS_IMPACT_SCORES['missing_preferred']
        
        for skill in analysis['missing_nice_to_have']:
            potential_score += self.ATS_IMPACT_SCORES['missing_nice_to_have']
        
        # Improve weak skills
        for skill in analysis['weak_proficiency']:
            potential_score += self.ATS_IMPACT_SCORES['weak_proficiency']
        
        # Normalize to 0-100 scale
        max_possible = potential_score
        current_normalized = min(100, max(0, (current_score / max_possible) * 100)) if max_possible > 0 else 0
        potential_normalized = 100.0
        
        # Calculate per-skill impact
        skill_impacts = []
        
        for skill in analysis['missing_mandatory']:
            skill_impacts.append({
                'skill_name': skill['skill_name'],
                'gap_type': 'missing_mandatory',
                'severity': skill['severity'],
                'ats_score_delta': self.ATS_IMPACT_SCORES['missing_mandatory'],
                'normalized_delta': (self.ATS_IMPACT_SCORES['missing_mandatory'] / max_possible) * 100 if max_possible > 0 else 0,
                'priority': 1
            })
        
        for skill in analysis['missing_preferred']:
            skill_impacts.append({
                'skill_name': skill['skill_name'],
                'gap_type': 'missing_preferred',
                'severity': skill['severity'],
                'ats_score_delta': self.ATS_IMPACT_SCORES['missing_preferred'],
                'normalized_delta': (self.ATS_IMPACT_SCORES['missing_preferred'] / max_possible) * 100 if max_possible > 0 else 0,
                'priority': 2
            })
        
        for skill in analysis['weak_proficiency']:
            skill_impacts.append({
                'skill_name': skill['skill_name'],
                'gap_type': 'weak_proficiency',
                'severity': skill['severity'],
                'ats_score_delta': self.ATS_IMPACT_SCORES['weak_proficiency'],
                'normalized_delta': (self.ATS_IMPACT_SCORES['weak_proficiency'] / max_possible) * 100 if max_possible > 0 else 0,
                'priority': 2
            })
        
        # Sort by impact
        skill_impacts.sort(key=lambda x: x['ats_score_delta'], reverse=True)
        
        return {
            'current_score': round(current_normalized, 1),
            'potential_score': round(potential_normalized, 1),
            'improvement_potential': round(potential_normalized - current_normalized, 1),
            'skill_impacts': skill_impacts,
            'top_impact_skills': skill_impacts[:5]
        }
    
    def _calculate_hiring_relevance(self, analysis: Dict) -> Dict:
        """Calculate hiring relevance score"""
        
        # Factors:
        # 1. Mandatory skills coverage (40%)
        # 2. Preferred skills coverage (30%)
        # 3. Overall match percentage (20%)
        # 4. Proficiency strength (10%)
        
        total_mandatory = len(analysis['missing_mandatory']) + sum(
            1 for s in analysis['matched'] if s.get('job_requirement') == 'mandatory'
        )
        
        total_preferred = len(analysis['missing_preferred']) + sum(
            1 for s in analysis['matched'] if s.get('job_requirement') == 'preferred'
        )
        
        # Mandatory coverage
        mandatory_matched = sum(
            1 for s in analysis['matched'] if s.get('job_requirement') == 'mandatory'
        )
        mandatory_score = (mandatory_matched / total_mandatory * 100) if total_mandatory > 0 else 100
        
        # Preferred coverage
        preferred_matched = sum(
            1 for s in analysis['matched'] if s.get('job_requirement') == 'preferred'
        )
        preferred_score = (preferred_matched / total_preferred * 100) if total_preferred > 0 else 100
        
        # Overall match
        match_percentage = self._calculate_match_percentage(analysis)
        
        # Proficiency strength
        strong_count = sum(
            1 for s in analysis['matched']
            if s.get('proficiency') in self.STRONG_PROFICIENCY_LEVELS
        )
        total_matched = len(analysis['matched'])
        proficiency_score = (strong_count / total_matched * 100) if total_matched > 0 else 0
        
        # Weighted average
        overall_score = (
            mandatory_score * 0.4 +
            preferred_score * 0.3 +
            match_percentage * 0.2 +
            proficiency_score * 0.1
        )
        
        # Determine hiring likelihood
        if overall_score >= 80:
            likelihood = 'strong_hire'
            message = 'Strong candidate - highly relevant skills'
        elif overall_score >= 60:
            likelihood = 'hire'
            message = 'Good candidate - meets most requirements'
        elif overall_score >= 40:
            likelihood = 'maybe'
            message = 'Potential candidate - some gaps to address'
        else:
            likelihood = 'no_hire'
            message = 'Significant skill gaps - not recommended'
        
        return {
            'overall_score': round(overall_score, 1),
            'mandatory_coverage': round(mandatory_score, 1),
            'preferred_coverage': round(preferred_score, 1),
            'match_percentage': round(match_percentage, 1),
            'proficiency_strength': round(proficiency_score, 1),
            'hiring_likelihood': likelihood,
            'message': message
        }
    
    def _calculate_match_percentage(self, analysis: Dict) -> float:
        """Calculate overall match percentage"""
        total_job_skills = (
            len(analysis['missing_mandatory']) +
            len(analysis['missing_preferred']) +
            len(analysis['missing_nice_to_have']) +
            len(analysis['matched'])
        )
        
        if total_job_skills == 0:
            return 0.0
        
        matched = len(analysis['matched'])
        return (matched / total_job_skills) * 100
    
    # ========================================================================
    # Gap Details
    # ========================================================================
    
    def _build_gap_details(self, analysis: Dict) -> List[Dict]:
        """Build detailed gap information"""
        gap_details = []
        
        # Missing mandatory skills
        for skill in analysis['missing_mandatory']:
            gap_details.append({
                'skill_name': skill['skill_name'],
                'gap_type': 'missing',
                'requirement_level': 'mandatory',
                'severity': skill['severity'],
                'ats_weight': skill['ats_weight'],
                'market_demand': skill['market_demand'],
                'explanation': f"Missing mandatory skill: {skill['skill_name']}. Critical for role.",
                'action': f"Learn {skill['skill_name']} immediately - high priority",
                'estimated_learning_time': self._estimate_learning_time(skill['skill_key']),
                'resources': self._get_learning_resources(skill['skill_key'])
            })
        
        # Missing preferred skills
        for skill in analysis['missing_preferred']:
            gap_details.append({
                'skill_name': skill['skill_name'],
                'gap_type': 'missing',
                'requirement_level': 'preferred',
                'severity': skill['severity'],
                'ats_weight': skill['ats_weight'],
                'market_demand': skill['market_demand'],
                'explanation': f"Missing preferred skill: {skill['skill_name']}. Recommended for role.",
                'action': f"Consider learning {skill['skill_name']} - medium priority",
                'estimated_learning_time': self._estimate_learning_time(skill['skill_key']),
                'resources': self._get_learning_resources(skill['skill_key'])
            })
        
        # Weak proficiency
        for skill in analysis['weak_proficiency']:
            gap_details.append({
                'skill_name': skill['skill_name'],
                'gap_type': 'weak_proficiency',
                'requirement_level': skill['job_requirement'],
                'severity': skill['severity'],
                'current_proficiency': skill['current_proficiency'],
                'required_proficiency': skill['required_proficiency'],
                'explanation': f"Weak proficiency in {skill['skill_name']}. Need to improve from {skill['current_proficiency']} to {skill['required_proficiency']}.",
                'action': f"Strengthen {skill['skill_name']} skills through practice and projects",
                'estimated_learning_time': '2-4 weeks',
                'resources': self._get_learning_resources(skill['skill_key'])
            })
        
        # Sort by severity
        severity_order = {GapSeverity.HIGH: 0, GapSeverity.MEDIUM: 1, GapSeverity.LOW: 2}
        gap_details.sort(key=lambda x: severity_order.get(x['severity'], 3))
        
        return gap_details
    
    # ========================================================================
    # Recommendations
    # ========================================================================
    
    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Critical: Missing mandatory skills
        if analysis['missing_mandatory']:
            recommendations.append({
                'priority': 'critical',
                'title': 'Add Missing Mandatory Skills',
                'description': f"You are missing {len(analysis['missing_mandatory'])} mandatory skills",
                'skills': [s['skill_name'] for s in analysis['missing_mandatory'][:3]],
                'action': 'Focus on learning these skills before applying',
                'impact': 'high',
                'estimated_time': f"{len(analysis['missing_mandatory']) * 4} weeks"
            })
        
        # High: Missing preferred skills
        if analysis['missing_preferred']:
            recommendations.append({
                'priority': 'high',
                'title': 'Acquire Preferred Skills',
                'description': f"{len(analysis['missing_preferred'])} preferred skills missing",
                'skills': [s['skill_name'] for s in analysis['missing_preferred'][:3]],
                'action': 'Consider learning to strengthen application',
                'impact': 'medium',
                'estimated_time': f"{len(analysis['missing_preferred']) * 3} weeks"
            })
        
        # Medium: Improve weak proficiency
        if analysis['weak_proficiency']:
            recommendations.append({
                'priority': 'medium',
                'title': 'Strengthen Existing Skills',
                'description': f"{len(analysis['weak_proficiency'])} skills need proficiency improvement",
                'skills': [s['skill_name'] for s in analysis['weak_proficiency'][:3]],
                'action': 'Practice and build projects to demonstrate expertise',
                'impact': 'medium',
                'estimated_time': '2-4 weeks per skill'
            })
        
        return recommendations
    
    # ========================================================================
    # Explainability
    # ========================================================================
    
    def _generate_explainability(self, analysis: Dict, ats_impact: Dict) -> Dict:
        """Generate explainable insights"""
        return {
            'why_this_score': self._explain_score(analysis, ats_impact),
            'what_to_improve': self._explain_improvements(analysis),
            'how_scoring_works': {
                'missing_mandatory': f"-{self.ATS_IMPACT_SCORES['missing_mandatory']} points each",
                'missing_preferred': f"-{self.ATS_IMPACT_SCORES['missing_preferred']} points each",
                'weak_proficiency': f"-{self.ATS_IMPACT_SCORES['weak_proficiency']} points each",
                'matched_strong': f"+{self.ATS_IMPACT_SCORES['matched_strong']} points each",
                'matched_weak': f"+{self.ATS_IMPACT_SCORES['matched_weak']} points each"
            }
        }
    
    def _explain_score(self, analysis: Dict, ats_impact: Dict) -> str:
        """Explain current score"""
        matched = len(analysis['matched'])
        missing_mandatory = len(analysis['missing_mandatory'])
        
        if missing_mandatory > 0:
            return f"Score is {ats_impact['current_score']}/100 because you're missing {missing_mandatory} mandatory skills. You have {matched} matching skills."
        elif matched < 5:
            return f"Score is {ats_impact['current_score']}/100 because you have only {matched} matching skills. Add more relevant skills to improve."
        else:
            return f"Score is {ats_impact['current_score']}/100. You have {matched} matching skills with room for improvement in proficiency."
    
    def _explain_improvements(self, analysis: Dict) -> List[str]:
        """Explain what to improve"""
        improvements = []
        
        if analysis['missing_mandatory']:
            improvements.append(f"Learn {len(analysis['missing_mandatory'])} mandatory skills: {', '.join([s['skill_name'] for s in analysis['missing_mandatory'][:3]])}")
        
        if analysis['weak_proficiency']:
            improvements.append(f"Improve proficiency in {len(analysis['weak_proficiency'])} skills: {', '.join([s['skill_name'] for s in analysis['weak_proficiency'][:3]])}")
        
        if analysis['missing_preferred']:
            improvements.append(f"Consider learning {len(analysis['missing_preferred'])} preferred skills for competitive advantage")
        
        return improvements
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _estimate_learning_time(self, skill_key: str) -> str:
        """Estimate time to learn a skill"""
        # Get from skill database if available
        skill_info = self.extraction_service.get_skill_info(skill_key)
        
        if skill_info:
            category = skill_info.get('category')
            if category == 'language':
                return '2-3 months'
            elif category == 'framework':
                return '1-2 months'
            elif category == 'tool':
                return '2-4 weeks'
            else:
                return '1-2 months'
        
        return '1-2 months'
    
    def _get_learning_resources(self, skill_key: str) -> List[str]:
        """Get learning resources for a skill"""
        # Simplified - could be expanded with real resource database
        return [
            f"Online courses for {skill_key}",
            f"Official {skill_key} documentation",
            f"Practice projects using {skill_key}"
        ]
    
    def _save_analysis_to_db(
        self,
        user_id: int,
        resume_id: int,
        job_id: int,
        analysis_result: Dict
    ):
        """Save analysis to database"""
        try:
            analysis = SkillGapAnalysis(
                user_id=user_id,
                resume_id=resume_id,
                job_id=job_id,
                match_percentage=analysis_result['summary']['match_percentage'],
                ats_score=analysis_result['summary']['current_ats_score'],
                potential_score=analysis_result['summary']['potential_ats_score'],
                total_jd_skills=analysis_result['summary']['total_job_skills'],
                total_resume_skills=analysis_result['summary']['total_resume_skills'],
                mandatory_missing=analysis_result['summary']['missing_mandatory'],
                preferred_missing=analysis_result['summary']['missing_preferred'],
                matched_skills_count=analysis_result['summary']['matched_skills'],
                skill_gaps=analysis_result['gaps'],
                matched_skills=[s['skill_name'] for s in analysis_result['matched_skills']],
                ranked_gaps=analysis_result['gap_details'],
                score_predictions=analysis_result['ats_impact']['skill_impacts'],
                recommendations=analysis_result['recommendations']
            )
            
            db.session.add(analysis)
            db.session.commit()
            
            self.logger.info(f"Saved gap analysis to database: {analysis.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save analysis: {str(e)}")
            db.session.rollback()

"""
ATS Impact Simulator
Predicts ATS score changes and simulates resume improvement scenarios
"""

from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging

from app.models.skill_intelligence import (
    ResumeSkillExtracted,
    JobSkillExtracted,
    SkillImpactScore,
    ProficiencyLevel
)

logger = logging.getLogger(__name__)


class ATSImpactSimulator:
    """
    Simulate ATS score impact of adding/improving skills.
    Deterministic scoring with before/after comparisons.
    """
    
    # ========================================================================
    # Scoring Constants (Deterministic)
    # ========================================================================
    
    # Base scores per skill match type
    SCORE_WEIGHTS = {
        'mandatory_match_expert': 20.0,
        'mandatory_match_advanced': 18.0,
        'mandatory_match_intermediate': 15.0,
        'mandatory_match_beginner': 10.0,
        'mandatory_missing': -20.0,
        
        'preferred_match_expert': 12.0,
        'preferred_match_advanced': 10.0,
        'preferred_match_intermediate': 8.0,
        'preferred_match_beginner': 5.0,
        'preferred_missing': -10.0,
        
        'nice_to_have_match': 5.0,
        'nice_to_have_missing': -2.0,
        
        'years_bonus_5plus': 5.0,
        'years_bonus_3plus': 3.0,
        'years_bonus_1plus': 1.0,
        
        'category_bonus_language': 2.0,
        'category_bonus_framework': 1.5,
        'category_bonus_platform': 2.0
    }
    
    # Maximum possible score (normalized to 100)
    MAX_SCORE = 100.0
    
    def __init__(self):
        self.logger = logger
    
    # ========================================================================
    # Main Prediction Methods
    # ========================================================================
    
    def predict_score_change(
        self,
        current_resume_skills: List[Dict],
        job_skills: List[Dict],
        skill_to_add: Dict,
        target_proficiency: str = ProficiencyLevel.INTERMEDIATE
    ) -> Dict:
        """
        Predict ATS score change if a skill is added.
        
        Args:
            current_resume_skills: Current resume skills
            job_skills: Job required skills
            skill_to_add: Skill to add (with metadata)
            target_proficiency: Target proficiency level
        
        Returns:
            Score change prediction with details
        """
        try:
            # Calculate current score
            current_score = self._calculate_ats_score(
                current_resume_skills,
                job_skills
            )
            
            # Simulate adding the skill
            simulated_skills = current_resume_skills.copy()
            simulated_skills.append({
                'skill_name_normalized': skill_to_add['skill_key'],
                'skill_name': skill_to_add['skill_name'],
                'proficiency_level': target_proficiency,
                'years_of_experience': 1.0,  # Assumed
                'category': skill_to_add.get('category', 'hard_skill')
            })
            
            # Calculate new score
            new_score = self._calculate_ats_score(
                simulated_skills,
                job_skills
            )
            
            # Calculate impact
            score_delta = new_score - current_score
            
            # Determine impact level
            impact_level = self._determine_impact_level(score_delta)
            
            return {
                'skill_name': skill_to_add['skill_name'],
                'skill_key': skill_to_add['skill_key'],
                'current_score': round(current_score, 1),
                'predicted_score': round(new_score, 1),
                'score_delta': round(score_delta, 1),
                'percentage_improvement': round((score_delta / current_score * 100) if current_score > 0 else 0, 1),
                'impact_level': impact_level,
                'target_proficiency': target_proficiency,
                'reasoning': self._explain_score_change(skill_to_add, score_delta, job_skills)
            }
            
        except Exception as e:
            self.logger.error(f"Score prediction failed: {str(e)}")
            raise
    
    def simulate_improvement_scenarios(
        self,
        current_resume_skills: List[Dict],
        job_skills: List[Dict],
        missing_skills: List[Dict]
    ) -> Dict:
        """
        Simulate multiple improvement scenarios.
        
        Args:
            current_resume_skills: Current resume skills
            job_skills: Job required skills
            missing_skills: List of missing skills
        
        Returns:
            Simulation results with scenarios
        """
        try:
            # Calculate baseline
            baseline_score = self._calculate_ats_score(
                current_resume_skills,
                job_skills
            )
            
            # Simulate adding each skill individually
            individual_impacts = []
            
            for skill in missing_skills:
                prediction = self.predict_score_change(
                    current_resume_skills,
                    job_skills,
                    skill
                )
                individual_impacts.append(prediction)
            
            # Sort by impact
            individual_impacts.sort(key=lambda x: x['score_delta'], reverse=True)
            
            # Simulate cumulative scenarios
            scenarios = self._simulate_cumulative_scenarios(
                current_resume_skills,
                job_skills,
                individual_impacts[:10]  # Top 10
            )
            
            # Find optimal path
            optimal_path = self._find_optimal_learning_path(
                individual_impacts,
                scenarios
            )
            
            return {
                'baseline_score': round(baseline_score, 1),
                'individual_impacts': individual_impacts,
                'scenarios': scenarios,
                'optimal_path': optimal_path,
                'top_3_skills': individual_impacts[:3],
                'summary': self._generate_simulation_summary(
                    baseline_score,
                    individual_impacts,
                    scenarios
                )
            }
            
        except Exception as e:
            self.logger.error(f"Simulation failed: {str(e)}")
            raise
    
    def get_top_skills_to_add(
        self,
        current_resume_skills: List[Dict],
        job_skills: List[Dict],
        missing_skills: List[Dict],
        count: int = 3
    ) -> List[Dict]:
        """
        Get top N skills to add first for maximum impact.
        
        Args:
            current_resume_skills: Current resume skills
            job_skills: Job required skills
            missing_skills: List of missing skills
            count: Number of top skills to return
        
        Returns:
            Top skills with impact predictions
        """
        try:
            # Predict impact for each missing skill
            predictions = []
            
            for skill in missing_skills:
                prediction = self.predict_score_change(
                    current_resume_skills,
                    job_skills,
                    skill
                )
                
                # Add additional context
                prediction['priority_rank'] = len(predictions) + 1
                prediction['learning_time'] = self._estimate_learning_time(skill)
                prediction['roi_score'] = self._calculate_roi(
                    prediction['score_delta'],
                    prediction['learning_time']
                )
                
                predictions.append(prediction)
            
            # Sort by ROI (score delta / learning time)
            predictions.sort(key=lambda x: x['roi_score'], reverse=True)
            
            # Return top N
            top_skills = predictions[:count]
            
            # Add ranking
            for i, skill in enumerate(top_skills, 1):
                skill['priority_rank'] = i
                skill['recommendation'] = self._generate_recommendation(skill, i)
            
            return top_skills
            
        except Exception as e:
            self.logger.error(f"Top skills calculation failed: {str(e)}")
            raise
    
    # ========================================================================
    # ATS Score Calculation (Deterministic)
    # ========================================================================
    
    def _calculate_ats_score(
        self,
        resume_skills: List[Dict],
        job_skills: List[Dict]
    ) -> float:
        """
        Calculate deterministic ATS score.
        
        Scoring logic:
        1. Match mandatory skills (high weight)
        2. Match preferred skills (medium weight)
        3. Match nice-to-have skills (low weight)
        4. Apply proficiency bonuses
        5. Apply years of experience bonuses
        6. Apply category bonuses
        7. Normalize to 0-100 scale
        """
        score = 0.0
        
        # Build resume skill map
        resume_map = {
            skill['skill_name_normalized']: skill
            for skill in resume_skills
        }
        
        # Track matches for normalization
        total_possible_score = 0.0
        
        # Score each job skill
        for job_skill in job_skills:
            skill_key = job_skill['skill_name_normalized']
            requirement_type = job_skill.get('requirement_type', 'nice_to_have')
            
            # Calculate possible score for this skill
            if requirement_type == 'mandatory':
                possible = self.SCORE_WEIGHTS['mandatory_match_expert']
            elif requirement_type == 'preferred':
                possible = self.SCORE_WEIGHTS['preferred_match_expert']
            else:
                possible = self.SCORE_WEIGHTS['nice_to_have_match']
            
            total_possible_score += possible
            
            # Check if skill is in resume
            if skill_key in resume_map:
                resume_skill = resume_map[skill_key]
                proficiency = resume_skill.get('proficiency_level', ProficiencyLevel.UNKNOWN)
                years = resume_skill.get('years_of_experience', 0)
                category = resume_skill.get('category', 'hard_skill')
                
                # Base match score
                if requirement_type == 'mandatory':
                    if proficiency == ProficiencyLevel.EXPERT:
                        score += self.SCORE_WEIGHTS['mandatory_match_expert']
                    elif proficiency == ProficiencyLevel.ADVANCED:
                        score += self.SCORE_WEIGHTS['mandatory_match_advanced']
                    elif proficiency == ProficiencyLevel.INTERMEDIATE:
                        score += self.SCORE_WEIGHTS['mandatory_match_intermediate']
                    else:
                        score += self.SCORE_WEIGHTS['mandatory_match_beginner']
                
                elif requirement_type == 'preferred':
                    if proficiency == ProficiencyLevel.EXPERT:
                        score += self.SCORE_WEIGHTS['preferred_match_expert']
                    elif proficiency == ProficiencyLevel.ADVANCED:
                        score += self.SCORE_WEIGHTS['preferred_match_advanced']
                    elif proficiency == ProficiencyLevel.INTERMEDIATE:
                        score += self.SCORE_WEIGHTS['preferred_match_intermediate']
                    else:
                        score += self.SCORE_WEIGHTS['preferred_match_beginner']
                
                else:  # nice_to_have
                    score += self.SCORE_WEIGHTS['nice_to_have_match']
                
                # Years of experience bonus
                if years >= 5:
                    score += self.SCORE_WEIGHTS['years_bonus_5plus']
                elif years >= 3:
                    score += self.SCORE_WEIGHTS['years_bonus_3plus']
                elif years >= 1:
                    score += self.SCORE_WEIGHTS['years_bonus_1plus']
                
                # Category bonus
                if category == 'language':
                    score += self.SCORE_WEIGHTS['category_bonus_language']
                elif category == 'framework':
                    score += self.SCORE_WEIGHTS['category_bonus_framework']
                elif category == 'platform':
                    score += self.SCORE_WEIGHTS['category_bonus_platform']
            
            else:
                # Skill is missing - apply penalty
                if requirement_type == 'mandatory':
                    score += self.SCORE_WEIGHTS['mandatory_missing']
                elif requirement_type == 'preferred':
                    score += self.SCORE_WEIGHTS['preferred_missing']
                else:
                    score += self.SCORE_WEIGHTS['nice_to_have_missing']
        
        # Normalize to 0-100 scale
        if total_possible_score > 0:
            normalized_score = (score / total_possible_score) * 100
            # Ensure within bounds
            normalized_score = max(0, min(100, normalized_score))
        else:
            normalized_score = 0.0
        
        return normalized_score
    
    # ========================================================================
    # Simulation Methods
    # ========================================================================
    
    def _simulate_cumulative_scenarios(
        self,
        current_resume_skills: List[Dict],
        job_skills: List[Dict],
        top_skills: List[Dict]
    ) -> List[Dict]:
        """Simulate cumulative skill additions"""
        scenarios = []
        simulated_skills = current_resume_skills.copy()
        
        for i, skill_pred in enumerate(top_skills, 1):
            # Add skill to simulation
            simulated_skills.append({
                'skill_name_normalized': skill_pred['skill_key'],
                'skill_name': skill_pred['skill_name'],
                'proficiency_level': skill_pred['target_proficiency'],
                'years_of_experience': 1.0,
                'category': 'hard_skill'
            })
            
            # Calculate cumulative score
            cumulative_score = self._calculate_ats_score(
                simulated_skills,
                job_skills
            )
            
            scenarios.append({
                'scenario_name': f'Add Top {i} Skill{"s" if i > 1 else ""}',
                'skills_added': [s['skill_name'] for s in top_skills[:i]],
                'predicted_score': round(cumulative_score, 1),
                'cumulative_improvement': round(cumulative_score - skill_pred['current_score'], 1),
                'skills_count': i
            })
        
        return scenarios
    
    def _find_optimal_learning_path(
        self,
        individual_impacts: List[Dict],
        scenarios: List[Dict]
    ) -> Dict:
        """Find optimal learning path based on ROI"""
        
        # Find best scenario (highest score with reasonable effort)
        best_scenario = None
        best_roi = 0
        
        for scenario in scenarios:
            # Calculate ROI (improvement per skill)
            roi = scenario['cumulative_improvement'] / scenario['skills_count']
            
            if roi > best_roi:
                best_roi = roi
                best_scenario = scenario
        
        if not best_scenario:
            return {}
        
        return {
            'recommended_scenario': best_scenario['scenario_name'],
            'skills_to_learn': best_scenario['skills_added'],
            'expected_score': best_scenario['predicted_score'],
            'total_improvement': best_scenario['cumulative_improvement'],
            'estimated_time': f"{best_scenario['skills_count'] * 6} weeks",
            'roi': round(best_roi, 1)
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _determine_impact_level(self, score_delta: float) -> str:
        """Determine impact level from score delta"""
        if score_delta >= 15:
            return 'critical'
        elif score_delta >= 10:
            return 'high'
        elif score_delta >= 5:
            return 'medium'
        else:
            return 'low'
    
    def _explain_score_change(
        self,
        skill: Dict,
        score_delta: float,
        job_skills: List[Dict]
    ) -> str:
        """Generate explanation for score change"""
        
        # Find if skill is in job requirements
        skill_key = skill['skill_key']
        job_skill = next(
            (js for js in job_skills if js['skill_name_normalized'] == skill_key),
            None
        )
        
        if not job_skill:
            return f"Adding {skill['skill_name']} provides minimal impact as it's not required."
        
        req_type = job_skill.get('requirement_type', 'nice_to_have')
        
        if req_type == 'mandatory':
            return f"Adding {skill['skill_name']} has critical impact (+{score_delta:.1f} points) as it's a mandatory requirement."
        elif req_type == 'preferred':
            return f"Adding {skill['skill_name']} has high impact (+{score_delta:.1f} points) as it's a preferred skill."
        else:
            return f"Adding {skill['skill_name']} has moderate impact (+{score_delta:.1f} points) as it's a nice-to-have skill."
    
    def _estimate_learning_time(self, skill: Dict) -> int:
        """Estimate learning time in weeks"""
        category = skill.get('category', 'hard_skill')
        
        time_map = {
            'language': 12,      # 3 months
            'framework': 8,      # 2 months
            'platform': 8,       # 2 months
            'tool': 4,           # 1 month
            'methodology': 2,    # 2 weeks
            'hard_skill': 6      # 1.5 months
        }
        
        return time_map.get(category, 6)
    
    def _calculate_roi(self, score_delta: float, learning_time: int) -> float:
        """Calculate ROI (score improvement per week)"""
        if learning_time == 0:
            return 0.0
        return score_delta / learning_time
    
    def _generate_recommendation(self, skill: Dict, rank: int) -> str:
        """Generate recommendation text"""
        if rank == 1:
            return f"🥇 Top priority: Learn {skill['skill_name']} first for maximum impact (+{skill['score_delta']:.1f} points)"
        elif rank == 2:
            return f"🥈 Second priority: Add {skill['skill_name']} next (+{skill['score_delta']:.1f} points)"
        else:
            return f"🥉 Third priority: Consider {skill['skill_name']} (+{skill['score_delta']:.1f} points)"
    
    def _generate_simulation_summary(
        self,
        baseline_score: float,
        individual_impacts: List[Dict],
        scenarios: List[Dict]
    ) -> Dict:
        """Generate simulation summary"""
        
        if not scenarios:
            return {}
        
        best_scenario = max(scenarios, key=lambda x: x['predicted_score'])
        
        return {
            'current_score': round(baseline_score, 1),
            'best_possible_score': best_scenario['predicted_score'],
            'maximum_improvement': round(best_scenario['predicted_score'] - baseline_score, 1),
            'skills_needed': best_scenario['skills_count'],
            'top_impact_skill': individual_impacts[0]['skill_name'] if individual_impacts else None,
            'top_impact_delta': individual_impacts[0]['score_delta'] if individual_impacts else 0
        }
    
    # ========================================================================
    # Before/After Comparison
    # ========================================================================
    
    def generate_before_after_comparison(
        self,
        current_resume_skills: List[Dict],
        job_skills: List[Dict],
        skills_to_add: List[Dict]
    ) -> Dict:
        """
        Generate detailed before/after comparison.
        
        Args:
            current_resume_skills: Current skills
            job_skills: Job requirements
            skills_to_add: Skills to add
        
        Returns:
            Before/after comparison with breakdown
        """
        # Calculate before score
        before_score = self._calculate_ats_score(
            current_resume_skills,
            job_skills
        )
        
        # Simulate after
        after_skills = current_resume_skills.copy()
        for skill in skills_to_add:
            after_skills.append({
                'skill_name_normalized': skill['skill_key'],
                'skill_name': skill['skill_name'],
                'proficiency_level': ProficiencyLevel.INTERMEDIATE,
                'years_of_experience': 1.0,
                'category': skill.get('category', 'hard_skill')
            })
        
        # Calculate after score
        after_score = self._calculate_ats_score(
            after_skills,
            job_skills
        )
        
        # Build comparison
        return {
            'before': {
                'score': round(before_score, 1),
                'skills_count': len(current_resume_skills),
                'grade': self._score_to_grade(before_score)
            },
            'after': {
                'score': round(after_score, 1),
                'skills_count': len(after_skills),
                'grade': self._score_to_grade(after_score)
            },
            'improvement': {
                'score_delta': round(after_score - before_score, 1),
                'percentage_change': round((after_score - before_score) / before_score * 100 if before_score > 0 else 0, 1),
                'grade_change': f"{self._score_to_grade(before_score)} → {self._score_to_grade(after_score)}",
                'skills_added': [s['skill_name'] for s in skills_to_add]
            },
            'visual_comparison': self._generate_visual_comparison(before_score, after_score)
        }
    
    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'A-'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 65:
            return 'B-'
        elif score >= 60:
            return 'C+'
        elif score >= 55:
            return 'C'
        else:
            return 'D'
    
    def _generate_visual_comparison(self, before: float, after: float) -> Dict:
        """Generate visual comparison data"""
        return {
            'before_bar': '█' * int(before / 5),
            'after_bar': '█' * int(after / 5),
            'improvement_bar': '▲' * int((after - before) / 5) if after > before else ''
        }

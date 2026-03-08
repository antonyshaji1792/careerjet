"""
Skills Gap Analyzer

Identifies missing skills for target roles and provides learning paths.
"""

import openai
import os
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class SkillsGapAnalyzer:
    """Analyze skills gaps and provide learning recommendations"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
    
    def analyze_gap(self, current_skills, target_role, target_company=''):
        """
        Analyze skills gap for a target role
        
        Args:
            current_skills (str): Current skills (comma-separated)
            target_role (str): Target job title
            target_company (str): Optional target company
            
        Returns:
            dict: Gap analysis
        """
        try:
            prompt = f"""
Analyze the skills gap for someone wanting to become a {target_role}{f' at {target_company}' if target_company else ''}.

**Current Skills:**
{current_skills}

Provide:
1. Required skills for the role (categorized: Must-have, Nice-to-have)
2. Skills you already have (matching)
3. Skills gap (missing critical skills)
4. Skill proficiency levels needed
5. Priority order for learning

Format as JSON with keys: required_skills, matching_skills, skills_gap, proficiency_levels, learning_priority
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a career development expert and skills analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1200
            )
            
            result = response.choices[0].message.content.strip()
            
            try:
                analysis = json.loads(result)
            except:
                analysis = self._parse_text_analysis(result, current_skills)
            
            # Calculate gap score
            total_required = len(analysis.get('required_skills', {}).get('must_have', [])) + len(analysis.get('required_skills', {}).get('nice_to_have', []))
            matching = len(analysis.get('matching_skills', []))
            gap_score = (matching / total_required * 100) if total_required > 0 else 0
            
            analysis['gap_score'] = round(gap_score, 1)
            analysis['readiness_level'] = self._get_readiness_level(gap_score)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing gap: {str(e)}")
            return {
                'required_skills': {'must_have': [], 'nice_to_have': []},
                'matching_skills': [],
                'skills_gap': [],
                'gap_score': 0,
                'readiness_level': 'Unknown'
            }
    
    def generate_learning_path(self, skills_gap, target_role, timeframe='3 months'):
        """
        Generate personalized learning path
        
        Args:
            skills_gap (list): List of missing skills
            target_role (str): Target role
            timeframe (str): Learning timeframe
            
        Returns:
            dict: Learning path
        """
        try:
            prompt = f"""
Create a {timeframe} learning path to acquire these skills for a {target_role} role:

**Skills to Learn:**
{', '.join(skills_gap[:10])}

For each skill, provide:
1. Learning resources (courses, books, tutorials)
2. Estimated time to learn
3. Practice projects
4. Difficulty level
5. Priority (High/Medium/Low)

Also include:
- Weekly study plan
- Milestones
- Portfolio project ideas

Format as JSON with keys: skills_roadmap, weekly_plan, milestones, portfolio_projects
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a learning and development expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            result = response.choices[0].message.content.strip()
            
            try:
                learning_path = json.loads(result)
            except:
                learning_path = {
                    'skills_roadmap': [{'skill': skill, 'resources': ['Online courses'], 'time': '2-4 weeks'} for skill in skills_gap[:5]],
                    'weekly_plan': result,
                    'milestones': [],
                    'portfolio_projects': []
                }
            
            return learning_path
            
        except Exception as e:
            logger.error(f"Error generating learning path: {str(e)}")
            return {
                'skills_roadmap': [],
                'weekly_plan': '',
                'milestones': [],
                'portfolio_projects': []
            }
    
    def recommend_resources(self, skill, proficiency_level='beginner'):
        """
        Recommend learning resources for a specific skill
        
        Args:
            skill (str): Skill to learn
            proficiency_level (str): Current proficiency
            
        Returns:
            dict: Resource recommendations
        """
        resources = {
            'online_courses': [
                {'name': f'{skill} Fundamentals', 'platform': 'Coursera', 'duration': '4-6 weeks', 'cost': 'Free'},
                {'name': f'Complete {skill} Bootcamp', 'platform': 'Udemy', 'duration': '8-12 weeks', 'cost': '$50-100'},
                {'name': f'{skill} Specialization', 'platform': 'edX', 'duration': '3-6 months', 'cost': '$200-500'}
            ],
            'books': [
                f'Learning {skill}: A Beginner\'s Guide',
                f'{skill} in Action',
                f'Mastering {skill}'
            ],
            'practice_platforms': [
                'LeetCode' if 'programming' in skill.lower() else 'Practice projects',
                'HackerRank' if 'coding' in skill.lower() else 'Real-world projects',
                'GitHub' if 'development' in skill.lower() else 'Portfolio building'
            ],
            'communities': [
                f'{skill} subreddit',
                f'{skill} Discord server',
                f'{skill} Stack Overflow tag'
            ],
            'certifications': [
                f'Certified {skill} Professional',
                f'{skill} Associate Certification'
            ]
        }
        
        return resources
    
    def track_progress(self, user_id, skill, progress_percentage):
        """
        Track learning progress for a skill
        
        Args:
            user_id (int): User ID
            skill (str): Skill being learned
            progress_percentage (int): Progress (0-100)
            
        Returns:
            dict: Progress tracking data
        """
        # In production, this would save to database
        progress = {
            'user_id': user_id,
            'skill': skill,
            'progress': progress_percentage,
            'status': self._get_progress_status(progress_percentage),
            'updated_at': datetime.utcnow(),
            'estimated_completion': self._estimate_completion(progress_percentage)
        }
        
        return progress
    
    def get_skill_demand_trends(self, skills_list):
        """
        Get demand trends for skills
        
        Args:
            skills_list (list): List of skills
            
        Returns:
            dict: Demand trends
        """
        # In production, this would integrate with job market APIs
        trends = {}
        
        for skill in skills_list[:10]:
            trends[skill] = {
                'demand_level': 'High',  # High/Medium/Low
                'growth_rate': '+15%',   # Year over year
                'avg_salary_impact': '+$10,000',
                'job_openings': '50,000+',
                'trending': True
            }
        
        return trends
    
    def suggest_complementary_skills(self, current_skills, target_role):
        """
        Suggest complementary skills that enhance marketability
        
        Args:
            current_skills (str): Current skills
            target_role (str): Target role
            
        Returns:
            list: Complementary skills
        """
        try:
            prompt = f"""
For someone with these skills: {current_skills}
Targeting role: {target_role}

Suggest 5-7 complementary skills that would:
1. Enhance their marketability
2. Open new opportunities
3. Increase earning potential
4. Make them stand out

Return as a simple list.
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a career strategist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse into list
            skills = [s.strip().lstrip('1234567890.-) ') for s in result.split('\n') if s.strip()]
            
            return skills[:7]
            
        except Exception as e:
            logger.error(f"Error suggesting skills: {str(e)}")
            return []
    
    def _get_readiness_level(self, gap_score):
        """Determine readiness level based on gap score"""
        
        if gap_score >= 80:
            return 'Ready to Apply'
        elif gap_score >= 60:
            return 'Almost Ready (1-2 months)'
        elif gap_score >= 40:
            return 'Developing (3-6 months)'
        else:
            return 'Early Stage (6+ months)'
    
    def _get_progress_status(self, progress):
        """Get progress status"""
        
        if progress >= 100:
            return 'Completed'
        elif progress >= 75:
            return 'Almost Done'
        elif progress >= 50:
            return 'Halfway There'
        elif progress >= 25:
            return 'In Progress'
        else:
            return 'Just Started'
    
    def _estimate_completion(self, progress):
        """Estimate completion time"""
        
        if progress >= 75:
            return '1-2 weeks'
        elif progress >= 50:
            return '3-4 weeks'
        elif progress >= 25:
            return '1-2 months'
        else:
            return '2-3 months'
    
    def _parse_text_analysis(self, text, current_skills):
        """Parse text analysis into structured format"""
        
        return {
            'required_skills': {
                'must_have': ['Skill analysis in progress'],
                'nice_to_have': []
            },
            'matching_skills': current_skills.split(',')[:3],
            'skills_gap': ['Analysis in progress'],
            'proficiency_levels': {},
            'learning_priority': []
        }


# Helper function
def analyze_skills_for_role(current_skills, target_role, target_company=''):
    """
    Quick function to analyze skills gap
    
    Args:
        current_skills (str): Current skills
        target_role (str): Target role
        target_company (str): Optional company
        
    Returns:
        dict: Complete analysis
    """
    analyzer = SkillsGapAnalyzer()
    
    analysis = analyzer.analyze_gap(current_skills, target_role, target_company)
    
    if analysis['skills_gap']:
        learning_path = analyzer.generate_learning_path(
            analysis['skills_gap'],
            target_role
        )
        analysis['learning_path'] = learning_path
    
    return analysis

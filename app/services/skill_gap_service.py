"""
Skill Gap Intelligence System
Analyzes skill gaps, ranks by ATS impact, and suggests learning paths
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class SkillGapService:
    """
    Intelligent skill gap analysis and learning path recommendations.
    Compares resume against job descriptions and provides actionable insights.
    """
    
    # Skill categories with ATS weights
    SKILL_CATEGORIES = {
        'programming_languages': {
            'weight': 25,
            'keywords': ['python', 'java', 'javascript', 'typescript', 'go', 'rust', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin']
        },
        'frameworks': {
            'weight': 20,
            'keywords': ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'express', 'fastapi', 'rails', 'laravel']
        },
        'databases': {
            'weight': 15,
            'keywords': ['postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'cassandra', 'dynamodb', 'oracle']
        },
        'cloud_platforms': {
            'weight': 20,
            'keywords': ['aws', 'azure', 'gcp', 'google cloud', 'amazon web services', 'kubernetes', 'docker']
        },
        'tools': {
            'weight': 10,
            'keywords': ['git', 'jenkins', 'gitlab', 'github', 'jira', 'confluence', 'terraform', 'ansible']
        },
        'methodologies': {
            'weight': 10,
            'keywords': ['agile', 'scrum', 'kanban', 'ci/cd', 'tdd', 'devops', 'microservices']
        }
    }
    
    # Learning resources database
    LEARNING_RESOURCES = {
        'python': {
            'courses': [
                {'name': 'Python for Everybody (Coursera)', 'duration': '8 weeks', 'level': 'beginner'},
                {'name': 'Complete Python Bootcamp (Udemy)', 'duration': '22 hours', 'level': 'beginner'},
                {'name': 'Advanced Python (Pluralsight)', 'duration': '12 hours', 'level': 'advanced'}
            ],
            'certifications': [
                {'name': 'PCEP - Certified Entry-Level Python Programmer', 'provider': 'Python Institute'},
                {'name': 'PCAP - Certified Associate Python Programmer', 'provider': 'Python Institute'}
            ],
            'projects': [
                'Build a REST API with Flask/FastAPI',
                'Create a data analysis dashboard with Pandas',
                'Develop a web scraper with BeautifulSoup'
            ]
        },
        'aws': {
            'courses': [
                {'name': 'AWS Certified Solutions Architect (A Cloud Guru)', 'duration': '30 hours', 'level': 'intermediate'},
                {'name': 'AWS Fundamentals (Coursera)', 'duration': '4 weeks', 'level': 'beginner'}
            ],
            'certifications': [
                {'name': 'AWS Certified Cloud Practitioner', 'provider': 'Amazon'},
                {'name': 'AWS Certified Solutions Architect - Associate', 'provider': 'Amazon'}
            ],
            'projects': [
                'Deploy a web app on EC2 with auto-scaling',
                'Build a serverless API with Lambda and API Gateway',
                'Set up a CI/CD pipeline with CodePipeline'
            ]
        },
        'kubernetes': {
            'courses': [
                {'name': 'Kubernetes for Developers (Linux Foundation)', 'duration': '40 hours', 'level': 'intermediate'},
                {'name': 'Kubernetes Mastery (Udemy)', 'duration': '15 hours', 'level': 'intermediate'}
            ],
            'certifications': [
                {'name': 'Certified Kubernetes Administrator (CKA)', 'provider': 'CNCF'},
                {'name': 'Certified Kubernetes Application Developer (CKAD)', 'provider': 'CNCF'}
            ],
            'projects': [
                'Deploy a microservices app on Kubernetes',
                'Set up monitoring with Prometheus and Grafana',
                'Implement auto-scaling and load balancing'
            ]
        },
        'react': {
            'courses': [
                {'name': 'React - The Complete Guide (Udemy)', 'duration': '48 hours', 'level': 'beginner'},
                {'name': 'Advanced React Patterns (Frontend Masters)', 'duration': '8 hours', 'level': 'advanced'}
            ],
            'certifications': [
                {'name': 'Meta Front-End Developer Certificate', 'provider': 'Meta/Coursera'}
            ],
            'projects': [
                'Build a full-stack e-commerce site',
                'Create a real-time chat application',
                'Develop a task management dashboard'
            ]
        },
        'docker': {
            'courses': [
                {'name': 'Docker Mastery (Udemy)', 'duration': '19 hours', 'level': 'beginner'},
                {'name': 'Docker Deep Dive (Pluralsight)', 'duration': '6 hours', 'level': 'intermediate'}
            ],
            'certifications': [
                {'name': 'Docker Certified Associate', 'provider': 'Docker'}
            ],
            'projects': [
                'Containerize a multi-tier application',
                'Create a Docker Compose setup for microservices',
                'Build and optimize Docker images'
            ]
        }
    }
    
    # ATS impact scores per skill type
    ATS_IMPACT_SCORES = {
        'mandatory': 10.0,      # Missing mandatory skill: -10 points
        'preferred': 5.0,       # Missing preferred skill: -5 points
        'nice_to_have': 2.0,    # Missing nice-to-have: -2 points
        'bonus': 1.0            # Bonus skill: +1 point
    }
    
    def __init__(self):
        self.logger = logger
    
    def analyze_skill_gap(
        self,
        resume_skills: List[str],
        job_description: str,
        resume_text: Optional[str] = None
    ) -> Dict:
        """
        Comprehensive skill gap analysis.
        
        Args:
            resume_skills: List of skills from resume
            job_description: Target job description
            resume_text: Optional full resume text for context
        
        Returns:
            Detailed skill gap analysis with recommendations
        """
        try:
            # Extract skills from job description
            jd_skills = self._extract_skills_from_jd(job_description)
            
            # Categorize skills
            categorized_jd = self._categorize_skills(jd_skills)
            categorized_resume = self._categorize_skills(resume_skills)
            
            # Identify gaps
            gaps = self._identify_gaps(categorized_resume, categorized_jd)
            
            # Rank skills by ATS impact
            ranked_gaps = self._rank_by_ats_impact(gaps, jd_skills)
            
            # Suggest learning paths
            learning_paths = self._suggest_learning_paths(ranked_gaps)
            
            # Predict ATS score improvement
            score_predictions = self._predict_score_improvements(ranked_gaps)
            
            # Calculate current match score
            current_score = self._calculate_match_score(categorized_resume, categorized_jd)
            
            # Build comprehensive report
            report = {
                'summary': {
                    'total_jd_skills': len(jd_skills['all']),
                    'total_resume_skills': len(resume_skills),
                    'mandatory_missing': len(gaps['mandatory']),
                    'preferred_missing': len(gaps['preferred']),
                    'match_percentage': current_score,
                    'potential_score': current_score + sum(s['score_gain'] for s in score_predictions[:5])
                },
                'skill_gaps': {
                    'mandatory': gaps['mandatory'],
                    'preferred': gaps['preferred'],
                    'nice_to_have': gaps['nice_to_have']
                },
                'matched_skills': gaps['matched'],
                'ranked_gaps': ranked_gaps,
                'learning_paths': learning_paths,
                'score_predictions': score_predictions,
                'category_breakdown': self._analyze_by_category(categorized_resume, categorized_jd),
                'recommendations': self._generate_recommendations(gaps, ranked_gaps)
            }
            
            self.logger.info(f"Skill gap analysis complete: {len(gaps['mandatory'])} mandatory gaps")
            return report
            
        except Exception as e:
            self.logger.error(f"Skill gap analysis failed: {str(e)}")
            raise
    
    # ========================================================================
    # Skill Extraction & Categorization
    # ========================================================================
    
    def _extract_skills_from_jd(self, job_description: str) -> Dict:
        """Extract and categorize skills from job description"""
        jd_lower = job_description.lower()
        
        # Initialize skill sets
        mandatory = set()
        preferred = set()
        nice_to_have = set()
        all_skills = set()
        
        # Extract from different sections
        sections = self._split_jd_sections(jd_lower)
        
        # Required/Mandatory skills
        if 'required' in sections or 'mandatory' in sections:
            required_text = sections.get('required', '') + sections.get('mandatory', '')
            mandatory = self._extract_skills_from_text(required_text)
        
        # Preferred/Nice-to-have skills
        if 'preferred' in sections or 'nice to have' in sections:
            preferred_text = sections.get('preferred', '') + sections.get('nice to have', '')
            preferred = self._extract_skills_from_text(preferred_text)
        
        # Extract all technical skills
        all_skills = self._extract_skills_from_text(jd_lower)
        
        # Classify remaining skills
        nice_to_have = all_skills - mandatory - preferred
        
        return {
            'mandatory': list(mandatory),
            'preferred': list(preferred),
            'nice_to_have': list(nice_to_have),
            'all': list(all_skills)
        }
    
    def _split_jd_sections(self, jd_text: str) -> Dict[str, str]:
        """Split job description into sections"""
        sections = {}
        
        # Common section headers
        patterns = {
            'required': r'(?:required|must have|mandatory)[\s\S]*?(?=preferred|nice to have|responsibilities|$)',
            'preferred': r'(?:preferred|nice to have|bonus)[\s\S]*?(?=responsibilities|required|$)',
            'responsibilities': r'(?:responsibilities|duties|what you\'ll do)[\s\S]*?(?=required|preferred|$)'
        }
        
        for section, pattern in patterns.items():
            match = re.search(pattern, jd_text, re.IGNORECASE)
            if match:
                sections[section] = match.group(0)
        
        return sections
    
    def _extract_skills_from_text(self, text: str) -> Set[str]:
        """Extract technical skills from text"""
        skills = set()
        
        # Extract from all skill categories
        for category, data in self.SKILL_CATEGORIES.items():
            for keyword in data['keywords']:
                if keyword in text:
                    skills.add(keyword)
        
        # Extract multi-word skills
        multi_word_skills = [
            'machine learning', 'deep learning', 'natural language processing',
            'computer vision', 'data science', 'web development', 'mobile development',
            'cloud computing', 'distributed systems', 'rest api', 'graphql',
            'message queue', 'load balancing', 'auto scaling'
        ]
        
        for skill in multi_word_skills:
            if skill in text:
                skills.add(skill)
        
        return skills
    
    def _categorize_skills(self, skills: List[str]) -> Dict:
        """Categorize skills by type"""
        categorized = {category: [] for category in self.SKILL_CATEGORIES.keys()}
        categorized['other'] = []
        
        for skill in skills:
            skill_lower = skill.lower()
            categorized_flag = False
            
            for category, data in self.SKILL_CATEGORIES.items():
                if skill_lower in data['keywords']:
                    categorized[category].append(skill)
                    categorized_flag = True
                    break
            
            if not categorized_flag:
                categorized['other'].append(skill)
        
        return categorized
    
    # ========================================================================
    # Gap Analysis
    # ========================================================================
    
    def _identify_gaps(self, resume_skills: Dict, jd_skills: Dict) -> Dict:
        """Identify skill gaps between resume and JD"""
        # Flatten resume skills
        resume_flat = set()
        for skills in resume_skills.values():
            resume_flat.update(s.lower() for s in skills)
        
        # Identify gaps
        mandatory_gap = [s for s in jd_skills.get('mandatory', []) if s.lower() not in resume_flat]
        preferred_gap = [s for s in jd_skills.get('preferred', []) if s.lower() not in resume_flat]
        nice_to_have_gap = [s for s in jd_skills.get('nice_to_have', []) if s.lower() not in resume_flat]
        
        # Identify matches
        matched = [s for s in jd_skills.get('all', []) if s.lower() in resume_flat]
        
        return {
            'mandatory': mandatory_gap,
            'preferred': preferred_gap,
            'nice_to_have': nice_to_have_gap,
            'matched': matched
        }
    
    def _rank_by_ats_impact(self, gaps: Dict, jd_skills: Dict) -> List[Dict]:
        """Rank missing skills by ATS impact"""
        ranked = []
        
        # Mandatory skills (highest impact)
        for skill in gaps['mandatory']:
            ranked.append({
                'skill': skill,
                'type': 'mandatory',
                'ats_impact': self.ATS_IMPACT_SCORES['mandatory'],
                'priority': 'critical',
                'category': self._get_skill_category(skill)
            })
        
        # Preferred skills
        for skill in gaps['preferred']:
            ranked.append({
                'skill': skill,
                'type': 'preferred',
                'ats_impact': self.ATS_IMPACT_SCORES['preferred'],
                'priority': 'high',
                'category': self._get_skill_category(skill)
            })
        
        # Nice-to-have skills
        for skill in gaps['nice_to_have'][:10]:  # Limit to top 10
            ranked.append({
                'skill': skill,
                'type': 'nice_to_have',
                'ats_impact': self.ATS_IMPACT_SCORES['nice_to_have'],
                'priority': 'medium',
                'category': self._get_skill_category(skill)
            })
        
        # Sort by ATS impact
        ranked.sort(key=lambda x: x['ats_impact'], reverse=True)
        
        return ranked
    
    def _get_skill_category(self, skill: str) -> str:
        """Get category for a skill"""
        skill_lower = skill.lower()
        
        for category, data in self.SKILL_CATEGORIES.items():
            if skill_lower in data['keywords']:
                return category
        
        return 'other'
    
    # ========================================================================
    # Learning Path Suggestions
    # ========================================================================
    
    def _suggest_learning_paths(self, ranked_gaps: List[Dict]) -> List[Dict]:
        """Suggest learning paths for missing skills"""
        learning_paths = []
        
        for gap in ranked_gaps[:10]:  # Top 10 gaps
            skill = gap['skill'].lower()
            
            # Get learning resources
            resources = self.LEARNING_RESOURCES.get(skill, self._get_generic_resources(skill))
            
            learning_path = {
                'skill': gap['skill'],
                'priority': gap['priority'],
                'estimated_time': self._estimate_learning_time(skill),
                'difficulty': self._estimate_difficulty(skill, gap['category']),
                'courses': resources.get('courses', [])[:3],
                'certifications': resources.get('certifications', []),
                'projects': resources.get('projects', [])[:3],
                'learning_order': self._determine_learning_order(gap['skill'], ranked_gaps)
            }
            
            learning_paths.append(learning_path)
        
        return learning_paths
    
    def _get_generic_resources(self, skill: str) -> Dict:
        """Get generic learning resources for unknown skills"""
        return {
            'courses': [
                {'name': f'{skill.title()} Fundamentals (Udemy)', 'duration': '10-20 hours', 'level': 'beginner'},
                {'name': f'Complete {skill.title()} Course (Coursera)', 'duration': '4-8 weeks', 'level': 'intermediate'}
            ],
            'certifications': [],
            'projects': [
                f'Build a sample project using {skill}',
                f'Contribute to open-source {skill} projects',
                f'Create a portfolio piece demonstrating {skill}'
            ]
        }
    
    def _estimate_learning_time(self, skill: str) -> str:
        """Estimate time to learn a skill"""
        # Simple heuristic based on skill type
        if skill in ['python', 'java', 'javascript']:
            return '2-3 months'
        elif skill in ['aws', 'kubernetes', 'docker']:
            return '1-2 months'
        elif skill in ['react', 'angular', 'vue']:
            return '1-2 months'
        else:
            return '2-4 weeks'
    
    def _estimate_difficulty(self, skill: str, category: str) -> str:
        """Estimate learning difficulty"""
        if category == 'programming_languages':
            return 'intermediate'
        elif category == 'cloud_platforms':
            return 'intermediate'
        elif category == 'frameworks':
            return 'beginner-intermediate'
        else:
            return 'beginner'
    
    def _determine_learning_order(self, skill: str, all_gaps: List[Dict]) -> int:
        """Determine optimal learning order"""
        # Prerequisites mapping
        prerequisites = {
            'react': ['javascript'],
            'kubernetes': ['docker'],
            'django': ['python'],
            'flask': ['python']
        }
        
        skill_lower = skill.lower()
        
        # Check if skill has prerequisites
        if skill_lower in prerequisites:
            prereqs = prerequisites[skill_lower]
            # Check if prerequisites are in gaps
            missing_prereqs = [g for g in all_gaps if g['skill'].lower() in prereqs]
            if missing_prereqs:
                return 2  # Learn after prerequisites
        
        return 1  # Can learn immediately
    
    # ========================================================================
    # Score Prediction
    # ========================================================================
    
    def _predict_score_improvements(self, ranked_gaps: List[Dict]) -> List[Dict]:
        """Predict ATS score improvement per skill"""
        predictions = []
        
        for gap in ranked_gaps:
            # Calculate potential score gain
            base_gain = gap['ats_impact']
            
            # Adjust based on category weight
            category = gap['category']
            if category in self.SKILL_CATEGORIES:
                category_weight = self.SKILL_CATEGORIES[category]['weight']
                adjusted_gain = base_gain * (category_weight / 100)
            else:
                adjusted_gain = base_gain * 0.5
            
            prediction = {
                'skill': gap['skill'],
                'current_impact': 0,
                'potential_impact': gap['ats_impact'],
                'score_gain': round(adjusted_gain, 1),
                'priority': gap['priority'],
                'effort': self._estimate_effort(gap['skill']),
                'roi': round(adjusted_gain / self._get_effort_score(gap['skill']), 2)
            }
            
            predictions.append(prediction)
        
        # Sort by ROI (return on investment)
        predictions.sort(key=lambda x: x['roi'], reverse=True)
        
        return predictions
    
    def _estimate_effort(self, skill: str) -> str:
        """Estimate effort to learn skill"""
        if skill.lower() in ['python', 'java', 'javascript']:
            return 'high'
        elif skill.lower() in ['docker', 'git', 'agile']:
            return 'low'
        else:
            return 'medium'
    
    def _get_effort_score(self, skill: str) -> float:
        """Get numerical effort score"""
        effort = self._estimate_effort(skill)
        return {'low': 1.0, 'medium': 2.0, 'high': 3.0}.get(effort, 2.0)
    
    # ========================================================================
    # Scoring & Analysis
    # ========================================================================
    
    def _calculate_match_score(self, resume_skills: Dict, jd_skills: Dict) -> float:
        """Calculate current skill match score"""
        # Flatten skills
        resume_flat = set()
        for skills in resume_skills.values():
            resume_flat.update(s.lower() for s in skills)
        
        jd_flat = set(s.lower() for s in jd_skills.get('all', []))
        
        if not jd_flat:
            return 0.0
        
        matched = len(resume_flat & jd_flat)
        total = len(jd_flat)
        
        return round((matched / total) * 100, 1)
    
    def _analyze_by_category(self, resume_skills: Dict, jd_skills: Dict) -> Dict:
        """Analyze skill gaps by category"""
        analysis = {}
        
        # Flatten JD skills by category
        jd_by_category = self._categorize_skills(jd_skills.get('all', []))
        
        for category in self.SKILL_CATEGORIES.keys():
            resume_cat = set(s.lower() for s in resume_skills.get(category, []))
            jd_cat = set(s.lower() for s in jd_by_category.get(category, []))
            
            if jd_cat:
                matched = len(resume_cat & jd_cat)
                total = len(jd_cat)
                match_pct = (matched / total) * 100
            else:
                match_pct = 100.0
            
            analysis[category] = {
                'match_percentage': round(match_pct, 1),
                'matched': list(resume_cat & jd_cat),
                'missing': list(jd_cat - resume_cat),
                'weight': self.SKILL_CATEGORIES[category]['weight']
            }
        
        return analysis
    
    def _generate_recommendations(self, gaps: Dict, ranked_gaps: List[Dict]) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Critical: Missing mandatory skills
        if gaps['mandatory']:
            recommendations.append({
                'priority': 'critical',
                'title': 'Add Missing Mandatory Skills',
                'description': f'You are missing {len(gaps["mandatory"])} mandatory skills',
                'action': f'Focus on learning: {", ".join(gaps["mandatory"][:3])}',
                'impact': 'high'
            })
        
        # High: Missing preferred skills
        if gaps['preferred']:
            recommendations.append({
                'priority': 'high',
                'title': 'Acquire Preferred Skills',
                'description': f'{len(gaps["preferred"])} preferred skills missing',
                'action': f'Consider learning: {", ".join(gaps["preferred"][:3])}',
                'impact': 'medium'
            })
        
        # Medium: Optimize skill presentation
        if ranked_gaps:
            top_roi = ranked_gaps[0]
            recommendations.append({
                'priority': 'medium',
                'title': 'Highest ROI Skill',
                'description': f'Learning {top_roi["skill"]} has the best ROI',
                'action': f'Start with {top_roi["skill"]} - {self._estimate_learning_time(top_roi["skill"])} to learn',
                'impact': 'medium'
            })
        
        return recommendations

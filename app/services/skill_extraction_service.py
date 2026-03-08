"""
Skill Extraction Engine
Deterministic, token-efficient skill extraction from resumes and job descriptions
"""

import re
import json
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter
import logging

from app.models.skill_intelligence import (
    SkillCategory,
    SkillSource,
    ProficiencyLevel
)

logger = logging.getLogger(__name__)


class SkillExtractionService:
    """
    Intelligent skill extraction with normalization and categorization.
    Deterministic output, no AI hallucination.
    """
    
    # ========================================================================
    # Skill Database with Synonyms and Categories
    # ========================================================================
    
    SKILL_DATABASE = {
        # Programming Languages
        'python': {
            'canonical': 'Python',
            'synonyms': ['py', 'python3', 'python2', 'cpython'],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 10.0
        },
        'javascript': {
            'canonical': 'JavaScript',
            'synonyms': ['js', 'ecmascript', 'es6', 'es2015', 'node.js', 'nodejs'],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 10.0
        },
        'typescript': {
            'canonical': 'TypeScript',
            'synonyms': ['ts'],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 9.0
        },
        'java': {
            'canonical': 'Java',
            'synonyms': ['jdk', 'jre', 'java se', 'java ee'],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 10.0
        },
        'c++': {
            'canonical': 'C++',
            'synonyms': ['cpp', 'c plus plus'],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 9.0
        },
        'c#': {
            'canonical': 'C#',
            'synonyms': ['csharp', 'c sharp', '.net'],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 9.0
        },
        'go': {
            'canonical': 'Go',
            'synonyms': ['golang'],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 8.0
        },
        'rust': {
            'canonical': 'Rust',
            'synonyms': [],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 7.0
        },
        'ruby': {
            'canonical': 'Ruby',
            'synonyms': [],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 7.0
        },
        'php': {
            'canonical': 'PHP',
            'synonyms': ['php7', 'php8'],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 7.0
        },
        'swift': {
            'canonical': 'Swift',
            'synonyms': [],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 7.0
        },
        'kotlin': {
            'canonical': 'Kotlin',
            'synonyms': [],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 7.0
        },
        'sql': {
            'canonical': 'SQL',
            'synonyms': ['structured query language'],
            'category': SkillCategory.LANGUAGE,
            'ats_weight': 9.0
        },
        
        # Frameworks
        'react': {
            'canonical': 'React',
            'synonyms': ['reactjs', 'react.js', 'react native'],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 9.0
        },
        'angular': {
            'canonical': 'Angular',
            'synonyms': ['angularjs', 'angular.js'],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 8.0
        },
        'vue': {
            'canonical': 'Vue.js',
            'synonyms': ['vuejs', 'vue.js'],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 7.0
        },
        'django': {
            'canonical': 'Django',
            'synonyms': [],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 8.0
        },
        'flask': {
            'canonical': 'Flask',
            'synonyms': [],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 7.0
        },
        'fastapi': {
            'canonical': 'FastAPI',
            'synonyms': ['fast api'],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 7.0
        },
        'spring': {
            'canonical': 'Spring',
            'synonyms': ['spring boot', 'spring framework'],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 8.0
        },
        'express': {
            'canonical': 'Express.js',
            'synonyms': ['expressjs', 'express.js'],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 7.0
        },
        'rails': {
            'canonical': 'Ruby on Rails',
            'synonyms': ['ruby on rails', 'ror'],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 7.0
        },
        'laravel': {
            'canonical': 'Laravel',
            'synonyms': [],
            'category': SkillCategory.FRAMEWORK,
            'ats_weight': 6.0
        },
        
        # Databases
        'postgresql': {
            'canonical': 'PostgreSQL',
            'synonyms': ['postgres', 'psql'],
            'category': SkillCategory.TOOL,
            'ats_weight': 8.0
        },
        'mysql': {
            'canonical': 'MySQL',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 8.0
        },
        'mongodb': {
            'canonical': 'MongoDB',
            'synonyms': ['mongo'],
            'category': SkillCategory.TOOL,
            'ats_weight': 8.0
        },
        'redis': {
            'canonical': 'Redis',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 7.0
        },
        'elasticsearch': {
            'canonical': 'Elasticsearch',
            'synonyms': ['elastic search', 'es'],
            'category': SkillCategory.TOOL,
            'ats_weight': 7.0
        },
        'cassandra': {
            'canonical': 'Cassandra',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 6.0
        },
        'dynamodb': {
            'canonical': 'DynamoDB',
            'synonyms': ['dynamo db'],
            'category': SkillCategory.TOOL,
            'ats_weight': 7.0
        },
        
        # Cloud Platforms
        'aws': {
            'canonical': 'AWS',
            'synonyms': ['amazon web services', 'amazon aws'],
            'category': SkillCategory.PLATFORM,
            'ats_weight': 10.0
        },
        'azure': {
            'canonical': 'Azure',
            'synonyms': ['microsoft azure'],
            'category': SkillCategory.PLATFORM,
            'ats_weight': 9.0
        },
        'gcp': {
            'canonical': 'Google Cloud Platform',
            'synonyms': ['google cloud', 'gcp'],
            'category': SkillCategory.PLATFORM,
            'ats_weight': 9.0
        },
        'kubernetes': {
            'canonical': 'Kubernetes',
            'synonyms': ['k8s'],
            'category': SkillCategory.PLATFORM,
            'ats_weight': 9.0
        },
        'docker': {
            'canonical': 'Docker',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 9.0
        },
        
        # Tools
        'git': {
            'canonical': 'Git',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 8.0
        },
        'github': {
            'canonical': 'GitHub',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 6.0
        },
        'gitlab': {
            'canonical': 'GitLab',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 6.0
        },
        'jenkins': {
            'canonical': 'Jenkins',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 7.0
        },
        'jira': {
            'canonical': 'Jira',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 6.0
        },
        'terraform': {
            'canonical': 'Terraform',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 8.0
        },
        'ansible': {
            'canonical': 'Ansible',
            'synonyms': [],
            'category': SkillCategory.TOOL,
            'ats_weight': 7.0
        },
        
        # Methodologies
        'agile': {
            'canonical': 'Agile',
            'synonyms': [],
            'category': SkillCategory.METHODOLOGY,
            'ats_weight': 5.0
        },
        'scrum': {
            'canonical': 'Scrum',
            'synonyms': [],
            'category': SkillCategory.METHODOLOGY,
            'ats_weight': 5.0
        },
        'kanban': {
            'canonical': 'Kanban',
            'synonyms': [],
            'category': SkillCategory.METHODOLOGY,
            'ats_weight': 4.0
        },
        'devops': {
            'canonical': 'DevOps',
            'synonyms': ['dev ops'],
            'category': SkillCategory.METHODOLOGY,
            'ats_weight': 8.0
        },
        'ci/cd': {
            'canonical': 'CI/CD',
            'synonyms': ['continuous integration', 'continuous deployment', 'cicd'],
            'category': SkillCategory.METHODOLOGY,
            'ats_weight': 7.0
        },
        'tdd': {
            'canonical': 'Test-Driven Development',
            'synonyms': ['test driven development', 'tdd'],
            'category': SkillCategory.METHODOLOGY,
            'ats_weight': 6.0
        },
        'microservices': {
            'canonical': 'Microservices',
            'synonyms': ['micro services'],
            'category': SkillCategory.METHODOLOGY,
            'ats_weight': 8.0
        },
        
        # Soft Skills
        'leadership': {
            'canonical': 'Leadership',
            'synonyms': ['team leadership', 'leading teams'],
            'category': SkillCategory.SOFT_SKILL,
            'ats_weight': 5.0
        },
        'communication': {
            'canonical': 'Communication',
            'synonyms': ['verbal communication', 'written communication'],
            'category': SkillCategory.SOFT_SKILL,
            'ats_weight': 5.0
        },
        'problem solving': {
            'canonical': 'Problem Solving',
            'synonyms': ['problem-solving', 'analytical thinking'],
            'category': SkillCategory.SOFT_SKILL,
            'ats_weight': 5.0
        },
        'teamwork': {
            'canonical': 'Teamwork',
            'synonyms': ['team collaboration', 'collaboration'],
            'category': SkillCategory.SOFT_SKILL,
            'ats_weight': 4.0
        }
    }
    
    # Build reverse lookup for synonyms
    SYNONYM_MAP = {}
    for canonical_key, data in SKILL_DATABASE.items():
        SYNONYM_MAP[canonical_key] = canonical_key
        for synonym in data['synonyms']:
            SYNONYM_MAP[synonym.lower()] = canonical_key
    
    # ========================================================================
    # Proficiency Patterns
    # ========================================================================
    
    PROFICIENCY_PATTERNS = {
        ProficiencyLevel.EXPERT: [
            r'expert\s+(?:in|with|at)',
            r'mastery\s+(?:of|in)',
            r'deep\s+(?:knowledge|expertise)',
            r'extensive\s+experience',
            r'advanced\s+(?:knowledge|skills)'
        ],
        ProficiencyLevel.ADVANCED: [
            r'advanced',
            r'proficient',
            r'strong\s+(?:knowledge|skills)',
            r'solid\s+understanding',
            r'experienced\s+(?:in|with)'
        ],
        ProficiencyLevel.INTERMEDIATE: [
            r'intermediate',
            r'working\s+knowledge',
            r'familiar\s+with',
            r'experience\s+(?:in|with)',
            r'knowledge\s+of'
        ],
        ProficiencyLevel.BEGINNER: [
            r'basic',
            r'beginner',
            r'learning',
            r'exposure\s+to',
            r'some\s+experience'
        ]
    }
    
    # ========================================================================
    # Years of Experience Patterns
    # ========================================================================
    
    YEARS_PATTERN = re.compile(
        r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)?',
        re.IGNORECASE
    )
    
    def __init__(self):
        self.logger = logger
    
    # ========================================================================
    # Main Extraction Methods
    # ========================================================================
    
    def extract_from_resume(
        self,
        resume_text: str,
        resume_sections: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Extract skills from resume with proficiency and context.
        
        Args:
            resume_text: Full resume text
            resume_sections: Optional dict with sections (skills, experience, etc.)
        
        Returns:
            List of extracted skills with metadata
        """
        try:
            extracted_skills = []
            
            # Extract from skills section if available
            if resume_sections and 'skills' in resume_sections:
                skills_text = resume_sections['skills']
                skills = self._extract_skills_from_text(skills_text)
                
                for skill_key in skills:
                    skill_data = self._build_skill_dict(
                        skill_key,
                        context=skills_text[:200],
                        source=SkillSource.RESUME
                    )
                    extracted_skills.append(skill_data)
            
            # Extract from full text
            all_skills = self._extract_skills_from_text(resume_text)
            
            for skill_key in all_skills:
                # Skip if already extracted from skills section
                if any(s['skill_name_normalized'] == skill_key for s in extracted_skills):
                    continue
                
                # Find context
                context = self._find_skill_context(resume_text, skill_key)
                
                # Detect proficiency
                proficiency = self._detect_proficiency(context)
                
                # Extract years of experience
                years = self._extract_years_of_experience(context)
                
                skill_data = self._build_skill_dict(
                    skill_key,
                    context=context,
                    proficiency_level=proficiency,
                    years_of_experience=years,
                    source=SkillSource.RESUME
                )
                
                extracted_skills.append(skill_data)
            
            # De-duplicate
            extracted_skills = self._deduplicate_skills(extracted_skills)
            
            self.logger.info(f"Extracted {len(extracted_skills)} skills from resume")
            return extracted_skills
            
        except Exception as e:
            self.logger.error(f"Resume skill extraction failed: {str(e)}")
            raise
    
    def extract_from_job_description(
        self,
        job_description: str
    ) -> List[Dict]:
        """
        Extract skills from job description with requirement levels.
        
        Args:
            job_description: Job description text
        
        Returns:
            List of extracted skills with requirement metadata
        """
        try:
            extracted_skills = []
            
            # Split into sections
            sections = self._split_jd_sections(job_description)
            
            # Extract from required/mandatory section
            if 'required' in sections or 'mandatory' in sections:
                required_text = sections.get('required', '') + sections.get('mandatory', '')
                skills = self._extract_skills_from_text(required_text)
                
                for skill_key in skills:
                    context = self._find_skill_context(required_text, skill_key)
                    skill_data = self._build_job_skill_dict(
                        skill_key,
                        requirement_type='mandatory',
                        context=context,
                        section='required'
                    )
                    extracted_skills.append(skill_data)
            
            # Extract from preferred section
            if 'preferred' in sections or 'nice to have' in sections:
                preferred_text = sections.get('preferred', '') + sections.get('nice to have', '')
                skills = self._extract_skills_from_text(preferred_text)
                
                for skill_key in skills:
                    # Skip if already in mandatory
                    if any(s['skill_name_normalized'] == skill_key and s['requirement_type'] == 'mandatory' 
                           for s in extracted_skills):
                        continue
                    
                    context = self._find_skill_context(preferred_text, skill_key)
                    skill_data = self._build_job_skill_dict(
                        skill_key,
                        requirement_type='preferred',
                        context=context,
                        section='preferred'
                    )
                    extracted_skills.append(skill_data)
            
            # Extract from full text (nice-to-have)
            all_skills = self._extract_skills_from_text(job_description)
            
            for skill_key in all_skills:
                # Skip if already categorized
                if any(s['skill_name_normalized'] == skill_key for s in extracted_skills):
                    continue
                
                context = self._find_skill_context(job_description, skill_key)
                skill_data = self._build_job_skill_dict(
                    skill_key,
                    requirement_type='nice_to_have',
                    context=context
                )
                extracted_skills.append(skill_data)
            
            # De-duplicate
            extracted_skills = self._deduplicate_skills(extracted_skills)
            
            self.logger.info(f"Extracted {len(extracted_skills)} skills from job description")
            return extracted_skills
            
        except Exception as e:
            self.logger.error(f"Job description skill extraction failed: {str(e)}")
            raise
    
    # ========================================================================
    # Core Extraction Logic
    # ========================================================================
    
    def _extract_skills_from_text(self, text: str) -> Set[str]:
        """Extract all known skills from text"""
        text_lower = text.lower()
        found_skills = set()
        
        # Check each skill and its synonyms
        for canonical_key, skill_data in self.SKILL_DATABASE.items():
            # Check canonical name
            if canonical_key in text_lower:
                found_skills.add(canonical_key)
                continue
            
            # Check synonyms
            for synonym in skill_data['synonyms']:
                if synonym.lower() in text_lower:
                    found_skills.add(canonical_key)
                    break
        
        return found_skills
    
    def _normalize_skill(self, skill_text: str) -> Optional[str]:
        """Normalize skill name to canonical form"""
        skill_lower = skill_text.lower().strip()
        
        # Direct lookup
        if skill_lower in self.SYNONYM_MAP:
            return self.SYNONYM_MAP[skill_lower]
        
        # Fuzzy matching for common variations
        for key, synonyms in self.SKILL_DATABASE.items():
            if skill_lower == key or skill_lower in [s.lower() for s in synonyms]:
                return key
        
        return None
    
    def _find_skill_context(self, text: str, skill_key: str, context_length: int = 200) -> str:
        """Find context around skill mention"""
        skill_data = self.SKILL_DATABASE.get(skill_key, {})
        canonical = skill_data.get('canonical', skill_key)
        
        # Find position of skill
        text_lower = text.lower()
        pos = text_lower.find(skill_key)
        
        if pos == -1:
            # Try synonyms
            for synonym in skill_data.get('synonyms', []):
                pos = text_lower.find(synonym.lower())
                if pos != -1:
                    break
        
        if pos == -1:
            return ""
        
        # Extract context
        start = max(0, pos - context_length // 2)
        end = min(len(text), pos + context_length // 2)
        
        return text[start:end].strip()
    
    def _detect_proficiency(self, context: str) -> str:
        """Detect proficiency level from context"""
        context_lower = context.lower()
        
        for level, patterns in self.PROFICIENCY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, context_lower):
                    return level
        
        return ProficiencyLevel.UNKNOWN
    
    def _extract_years_of_experience(self, context: str) -> Optional[float]:
        """Extract years of experience from context"""
        match = self.YEARS_PATTERN.search(context)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
        
        return None
    
    def _split_jd_sections(self, jd_text: str) -> Dict[str, str]:
        """Split job description into sections"""
        sections = {}
        
        patterns = {
            'required': r'(?:required|must have|mandatory|requirements)[:\s]+(.*?)(?=preferred|nice to have|responsibilities|$)',
            'preferred': r'(?:preferred|nice to have|bonus|plus)[:\s]+(.*?)(?=required|responsibilities|$)',
            'responsibilities': r'(?:responsibilities|duties|what you.*ll do)[:\s]+(.*?)(?=required|preferred|$)'
        }
        
        for section, pattern in patterns.items():
            match = re.search(pattern, jd_text, re.IGNORECASE | re.DOTALL)
            if match:
                sections[section] = match.group(1).strip()
        
        return sections
    
    # ========================================================================
    # Skill Dict Builders
    # ========================================================================
    
    def _build_skill_dict(
        self,
        skill_key: str,
        context: str = "",
        proficiency_level: str = ProficiencyLevel.UNKNOWN,
        years_of_experience: Optional[float] = None,
        source: str = SkillSource.AI_EXTRACTED
    ) -> Dict:
        """Build skill dictionary for resume"""
        skill_data = self.SKILL_DATABASE.get(skill_key, {})
        
        return {
            'skill_name': skill_data.get('canonical', skill_key.title()),
            'skill_name_normalized': skill_key,
            'category': skill_data.get('category', SkillCategory.HARD_SKILL),
            'proficiency_level': proficiency_level,
            'years_of_experience': years_of_experience,
            'context': context[:500] if context else None,
            'ats_weight': skill_data.get('ats_weight', 5.0),
            'confidence_score': 1.0,  # Deterministic extraction = high confidence
            'source': source,
            'extraction_method': 'pattern_matching'
        }
    
    def _build_job_skill_dict(
        self,
        skill_key: str,
        requirement_type: str = 'nice_to_have',
        context: str = "",
        section: Optional[str] = None
    ) -> Dict:
        """Build skill dictionary for job"""
        skill_data = self.SKILL_DATABASE.get(skill_key, {})
        
        # Calculate priority score based on requirement type
        priority_map = {
            'mandatory': 10.0,
            'preferred': 7.0,
            'nice_to_have': 5.0
        }
        
        return {
            'skill_name': skill_data.get('canonical', skill_key.title()),
            'skill_name_normalized': skill_key,
            'category': skill_data.get('category', SkillCategory.HARD_SKILL),
            'requirement_type': requirement_type,
            'priority_score': priority_map.get(requirement_type, 5.0),
            'market_demand_score': 5.0,  # Default, updated later
            'context': context[:500] if context else None,
            'section': section,
            'ats_weight': skill_data.get('ats_weight', 5.0),
            'confidence_score': 1.0,
            'source': SkillSource.AI_EXTRACTED,
            'extraction_method': 'pattern_matching'
        }
    
    def _deduplicate_skills(self, skills: List[Dict]) -> List[Dict]:
        """Intelligently de-duplicate skills"""
        seen = {}
        
        for skill in skills:
            key = skill['skill_name_normalized']
            
            if key not in seen:
                seen[key] = skill
            else:
                # Keep the one with more information
                existing = seen[key]
                
                # Prefer higher proficiency
                if skill.get('proficiency_level') != ProficiencyLevel.UNKNOWN:
                    existing['proficiency_level'] = skill['proficiency_level']
                
                # Prefer higher years of experience
                if skill.get('years_of_experience'):
                    existing['years_of_experience'] = skill['years_of_experience']
                
                # Prefer higher requirement type for jobs
                if skill.get('requirement_type') == 'mandatory':
                    existing['requirement_type'] = 'mandatory'
                    existing['priority_score'] = 10.0
        
        return list(seen.values())
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_skill_info(self, skill_name: str) -> Optional[Dict]:
        """Get information about a skill"""
        normalized = self._normalize_skill(skill_name)
        if normalized:
            return self.SKILL_DATABASE.get(normalized)
        return None
    
    def list_all_skills(self) -> List[str]:
        """List all known skills"""
        return [data['canonical'] for data in self.SKILL_DATABASE.values()]
    
    def list_skills_by_category(self, category: str) -> List[str]:
        """List skills by category"""
        return [
            data['canonical']
            for data in self.SKILL_DATABASE.values()
            if data['category'] == category
        ]

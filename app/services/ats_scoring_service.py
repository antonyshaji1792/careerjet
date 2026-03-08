"""
ATS Optimization Engine
Comprehensive scoring, analysis, and recommendations for ATS compatibility
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Set
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class ATSScoringService:
    """
    ATS (Applicant Tracking System) scoring and optimization service.
    Analyzes resumes for ATS compatibility and provides actionable feedback.
    """
    
    # Scoring weights (total = 100)
    WEIGHTS = {
        'formatting': 20,
        'keywords': 30,
        'structure': 20,
        'readability': 15,
        'content': 15
    }
    
    # ATS-friendly section names
    STANDARD_SECTIONS = {
        'summary', 'objective', 'professional summary',
        'experience', 'work experience', 'employment history',
        'education', 'academic background',
        'skills', 'technical skills', 'core competencies',
        'certifications', 'licenses',
        'projects', 'portfolio',
        'awards', 'achievements'
    }
    
    # Recommended section order
    RECOMMENDED_ORDER = [
        'summary',
        'skills',
        'experience',
        'education',
        'certifications',
        'projects'
    ]
    
    # ATS red flags
    RED_FLAGS = {
        'tables': 'Tables may not parse correctly in ATS',
        'images': 'Images and graphics are ignored by ATS',
        'headers_footers': 'Headers/footers may be skipped by ATS',
        'columns': 'Multi-column layouts can confuse ATS',
        'text_boxes': 'Text boxes may not be read by ATS',
        'special_chars': 'Special characters may cause parsing errors',
        'unsupported_fonts': 'Fancy fonts may not render correctly',
        'graphics': 'Graphics and charts are not ATS-friendly'
    }
    
    # Common ATS-unfriendly fonts
    UNSUPPORTED_FONTS = {
        'script', 'cursive', 'decorative', 'fantasy',
        'brush script', 'lucida handwriting', 'comic sans'
    }
    
    # Stop words to exclude from keyword analysis
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }
    
    def __init__(self):
        self.logger = logger
    
    def calculate_ats_score(
        self,
        resume_data: Dict,
        job_description: Optional[str] = None,
        resume_text: Optional[str] = None
    ) -> Dict:
        """
        Calculate comprehensive ATS score with detailed breakdown.
        
        Args:
            resume_data: Structured resume data (dict)
            job_description: Optional job description for keyword matching
            resume_text: Optional raw resume text for format analysis
        
        Returns:
            Dict with score, breakdown, recommendations, and red flags
        """
        try:
            # Calculate component scores
            formatting_score = self._score_formatting(resume_data, resume_text)
            keywords_score = self._score_keywords(resume_data, job_description)
            structure_score = self._score_structure(resume_data)
            readability_score = self._score_readability(resume_data)
            content_score = self._score_content(resume_data)
            
            # Calculate weighted overall score
            overall_score = (
                formatting_score * self.WEIGHTS['formatting'] / 100 +
                keywords_score * self.WEIGHTS['keywords'] / 100 +
                structure_score * self.WEIGHTS['structure'] / 100 +
                readability_score * self.WEIGHTS['readability'] / 100 +
                content_score * self.WEIGHTS['content'] / 100
            )
            
            # Detect red flags
            red_flags = self._detect_red_flags(resume_data, resume_text)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                formatting_score,
                keywords_score,
                structure_score,
                readability_score,
                content_score,
                red_flags,
                resume_data,
                job_description
            )
            
            # Keyword gap analysis
            keyword_analysis = self._analyze_keyword_gaps(resume_data, job_description)
            
            # Section ordering suggestions
            section_suggestions = self._suggest_section_order(resume_data)
            
            # Build report
            report = {
                'overall_score': round(overall_score, 1),
                'grade': self._get_grade(overall_score),
                'breakdown': {
                    'formatting': {
                        'score': round(formatting_score, 1),
                        'weight': self.WEIGHTS['formatting'],
                        'weighted_score': round(formatting_score * self.WEIGHTS['formatting'] / 100, 1)
                    },
                    'keywords': {
                        'score': round(keywords_score, 1),
                        'weight': self.WEIGHTS['keywords'],
                        'weighted_score': round(keywords_score * self.WEIGHTS['keywords'] / 100, 1)
                    },
                    'structure': {
                        'score': round(structure_score, 1),
                        'weight': self.WEIGHTS['structure'],
                        'weighted_score': round(structure_score * self.WEIGHTS['structure'] / 100, 1)
                    },
                    'readability': {
                        'score': round(readability_score, 1),
                        'weight': self.WEIGHTS['readability'],
                        'weighted_score': round(readability_score * self.WEIGHTS['readability'] / 100, 1)
                    },
                    'content': {
                        'score': round(content_score, 1),
                        'weight': self.WEIGHTS['content'],
                        'weighted_score': round(content_score * self.WEIGHTS['content'] / 100, 1)
                    }
                },
                'red_flags': red_flags,
                'keyword_analysis': keyword_analysis,
                'section_suggestions': section_suggestions,
                'recommendations': recommendations,
                'explainability': self._explain_score(
                    overall_score,
                    formatting_score,
                    keywords_score,
                    structure_score,
                    readability_score,
                    content_score,
                    red_flags
                )
            }
            
            self.logger.info(f"ATS score calculated: {overall_score:.1f}")
            return report
            
        except Exception as e:
            self.logger.error(f"ATS scoring failed: {str(e)}")
            raise
    
    # ========================================================================
    # Component Scoring Methods
    # ========================================================================
    
    def _score_formatting(self, resume_data: Dict, resume_text: Optional[str]) -> float:
        """Score formatting (0-100)"""
        score = 100.0
        
        # Check for standard sections
        sections = set(k.lower() for k in resume_data.keys())
        standard_sections_found = len(sections & self.STANDARD_SECTIONS)
        if standard_sections_found < 3:
            score -= 20
        
        # Check for clean structure
        if resume_text:
            # Penalize excessive special characters
            special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s\.,;:()\-]', resume_text)) / max(len(resume_text), 1)
            if special_char_ratio > 0.05:
                score -= 15
            
            # Penalize very long lines (likely tables)
            lines = resume_text.split('\n')
            long_lines = sum(1 for line in lines if len(line) > 120)
            if long_lines > len(lines) * 0.2:
                score -= 10
        
        # Check header structure
        if 'header' in resume_data:
            header = resume_data['header']
            required_fields = ['full_name', 'email']
            missing = [f for f in required_fields if f not in header or not header[f]]
            score -= len(missing) * 10
        else:
            score -= 20
        
        return max(0, min(100, score))
    
    def _score_keywords(self, resume_data: Dict, job_description: Optional[str]) -> float:
        """Score keyword matching (0-100)"""
        if not job_description:
            return 50.0  # Neutral score without JD
        
        # Extract keywords from JD
        jd_keywords = self._extract_keywords(job_description)
        
        # Extract keywords from resume
        resume_text = json.dumps(resume_data).lower()
        resume_keywords = self._extract_keywords(resume_text)
        
        # Calculate match percentage
        if not jd_keywords:
            return 50.0
        
        matched = len(jd_keywords & resume_keywords)
        match_percentage = (matched / len(jd_keywords)) * 100
        
        # Bonus for having more keywords than required
        if len(resume_keywords) > len(jd_keywords):
            match_percentage = min(100, match_percentage * 1.1)
        
        return round(match_percentage, 1)
    
    def _score_structure(self, resume_data: Dict) -> float:
        """Score resume structure (0-100)"""
        score = 100.0
        
        # Check for required sections
        required = ['experience', 'skills']
        for section in required:
            if section not in resume_data or not resume_data[section]:
                score -= 25
        
        # Check for recommended sections
        recommended = ['summary', 'education']
        for section in recommended:
            if section not in resume_data or not resume_data[section]:
                score -= 10
        
        # Check section order
        current_order = [k.lower() for k in resume_data.keys() if k.lower() in self.STANDARD_SECTIONS]
        if current_order != self.RECOMMENDED_ORDER[:len(current_order)]:
            score -= 10
        
        # Check for logical flow
        if 'experience' in resume_data and isinstance(resume_data['experience'], list):
            if len(resume_data['experience']) > 0:
                # Check if experiences are in reverse chronological order
                # (This is a simplified check)
                score += 5
        
        return max(0, min(100, score))
    
    def _score_readability(self, resume_data: Dict) -> float:
        """Score readability (0-100)"""
        score = 100.0
        
        # Check summary length
        if 'summary' in resume_data:
            summary = resume_data['summary']
            if isinstance(summary, str):
                words = len(summary.split())
                if words < 20:
                    score -= 15
                elif words > 100:
                    score -= 10
        
        # Check bullet point lengths
        if 'experience' in resume_data and isinstance(resume_data['experience'], list):
            for exp in resume_data['experience']:
                if 'achievements' in exp:
                    achievements = exp['achievements']
                    if isinstance(achievements, list):
                        for achievement in achievements:
                            if len(achievement) > 300:
                                score -= 5
                            elif len(achievement) < 20:
                                score -= 3
        
        # Check for action verbs
        action_verbs = {
            'led', 'managed', 'developed', 'implemented', 'created', 'designed',
            'built', 'improved', 'increased', 'reduced', 'achieved', 'delivered'
        }
        resume_text = json.dumps(resume_data).lower()
        verbs_found = sum(1 for verb in action_verbs if verb in resume_text)
        if verbs_found < 3:
            score -= 10
        
        return max(0, min(100, score))
    
    def _score_content(self, resume_data: Dict) -> float:
        """Score content quality (0-100)"""
        score = 100.0
        
        # Check for quantifiable achievements
        resume_text = json.dumps(resume_data)
        numbers = re.findall(r'\d+%|\d+\+|\$\d+|\d+ years?', resume_text)
        if len(numbers) < 3:
            score -= 15
        
        # Check skills count
        if 'skills' in resume_data:
            skills = resume_data['skills']
            if isinstance(skills, list):
                if len(skills) < 5:
                    score -= 20
                elif len(skills) > 30:
                    score -= 10
        
        # Check experience count
        if 'experience' in resume_data and isinstance(resume_data['experience'], list):
            if len(resume_data['experience']) == 0:
                score -= 30
        
        # Check education
        if 'education' not in resume_data or not resume_data['education']:
            score -= 10
        
        return max(0, min(100, score))
    
    # ========================================================================
    # Analysis Methods
    # ========================================================================
    
    def _detect_red_flags(self, resume_data: Dict, resume_text: Optional[str]) -> List[Dict]:
        """Detect ATS red flags"""
        flags = []
        
        if resume_text:
            # Check for tables (multiple tabs or pipes)
            if resume_text.count('\t') > 10 or resume_text.count('|') > 10:
                flags.append({
                    'type': 'tables',
                    'severity': 'high',
                    'message': self.RED_FLAGS['tables'],
                    'recommendation': 'Convert tables to simple text with bullet points'
                })
            
            # Check for special characters
            special_chars = len(re.findall(r'[★☆●○■□▪▫◆◇]', resume_text))
            if special_chars > 5:
                flags.append({
                    'type': 'special_chars',
                    'severity': 'medium',
                    'message': self.RED_FLAGS['special_chars'],
                    'recommendation': 'Replace special characters with standard bullets (•, -)'
                })
        
        # Check for unsupported fonts (if font info available)
        if 'formatting' in resume_data and 'font' in resume_data['formatting']:
            font = resume_data['formatting']['font'].lower()
            if any(unsupported in font for unsupported in self.UNSUPPORTED_FONTS):
                flags.append({
                    'type': 'unsupported_fonts',
                    'severity': 'medium',
                    'message': self.RED_FLAGS['unsupported_fonts'],
                    'recommendation': 'Use standard fonts: Arial, Calibri, Times New Roman, or Helvetica'
                })
        
        # Check for images/graphics indicators
        if 'images' in resume_data or 'graphics' in resume_data:
            flags.append({
                'type': 'images',
                'severity': 'high',
                'message': self.RED_FLAGS['images'],
                'recommendation': 'Remove all images and graphics; use text only'
            })
        
        return flags
    
    def _analyze_keyword_gaps(self, resume_data: Dict, job_description: Optional[str]) -> Dict:
        """Analyze keyword gaps between resume and JD"""
        if not job_description:
            return {
                'matched_keywords': [],
                'missing_keywords': [],
                'keyword_density': 0,
                'match_percentage': 0
            }
        
        # Extract keywords
        jd_keywords = self._extract_keywords(job_description)
        resume_text = json.dumps(resume_data).lower()
        resume_keywords = self._extract_keywords(resume_text)
        
        # Find matches and gaps
        matched = list(jd_keywords & resume_keywords)
        missing = list(jd_keywords - resume_keywords)
        
        # Calculate density
        total_words = len(resume_text.split())
        keyword_count = sum(resume_text.count(kw) for kw in matched)
        density = (keyword_count / total_words * 100) if total_words > 0 else 0
        
        # Calculate match percentage
        match_pct = (len(matched) / len(jd_keywords) * 100) if jd_keywords else 0
        
        return {
            'matched_keywords': sorted(matched)[:20],  # Top 20
            'missing_keywords': sorted(missing)[:20],  # Top 20
            'keyword_density': round(density, 2),
            'match_percentage': round(match_pct, 1),
            'total_jd_keywords': len(jd_keywords),
            'total_matched': len(matched)
        }
    
    def _suggest_section_order(self, resume_data: Dict) -> Dict:
        """Suggest optimal section ordering"""
        current_sections = [k for k in resume_data.keys() if k.lower() in self.STANDARD_SECTIONS]
        current_order = [s.lower() for s in current_sections]
        
        # Recommended order
        recommended = []
        for section in self.RECOMMENDED_ORDER:
            if section in current_order:
                recommended.append(section)
        
        # Add any sections not in recommended list
        for section in current_order:
            if section not in recommended:
                recommended.append(section)
        
        needs_reorder = current_order != recommended
        
        return {
            'current_order': current_order,
            'recommended_order': recommended,
            'needs_reordering': needs_reorder,
            'explanation': 'ATS systems prefer: Summary → Skills → Experience → Education → Certifications'
        }
    
    def _extract_keywords(self, text: str, min_length: int = 3) -> Set[str]:
        """Extract meaningful keywords from text"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Filter keywords
        keywords = set()
        for word in words:
            if (len(word) >= min_length and 
                word not in self.STOP_WORDS and
                not word.isdigit()):
                keywords.add(word)
        
        # Also extract multi-word phrases (2-3 words)
        phrases = []
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if all(w not in self.STOP_WORDS for w in [words[i], words[i+1]]):
                phrases.append(phrase)
        
        keywords.update(phrases[:50])  # Limit phrases
        
        return keywords
    
    # ========================================================================
    # Recommendation & Explanation Methods
    # ========================================================================
    
    def _generate_recommendations(
        self,
        formatting_score: float,
        keywords_score: float,
        structure_score: float,
        readability_score: float,
        content_score: float,
        red_flags: List[Dict],
        resume_data: Dict,
        job_description: Optional[str]
    ) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Formatting recommendations
        if formatting_score < 70:
            recommendations.append({
                'category': 'formatting',
                'priority': 'high',
                'title': 'Improve Resume Formatting',
                'description': 'Use standard section headers and clean formatting',
                'actions': [
                    'Use standard section names (Summary, Experience, Skills, Education)',
                    'Avoid tables, text boxes, and multi-column layouts',
                    'Use simple bullet points (• or -)',
                    'Ensure contact information is clearly visible'
                ]
            })
        
        # Keyword recommendations
        if keywords_score < 70 and job_description:
            recommendations.append({
                'category': 'keywords',
                'priority': 'high',
                'title': 'Add Missing Keywords',
                'description': 'Include more keywords from the job description',
                'actions': [
                    'Review missing keywords list',
                    'Naturally incorporate relevant keywords into your experience',
                    'Add technical skills mentioned in job description',
                    'Use industry-standard terminology'
                ]
            })
        
        # Structure recommendations
        if structure_score < 70:
            recommendations.append({
                'category': 'structure',
                'priority': 'medium',
                'title': 'Improve Resume Structure',
                'description': 'Organize sections in ATS-friendly order',
                'actions': [
                    'Follow recommended section order',
                    'Include all essential sections (Summary, Experience, Skills, Education)',
                    'Use reverse chronological order for experience',
                    'Keep consistent formatting throughout'
                ]
            })
        
        # Readability recommendations
        if readability_score < 70:
            recommendations.append({
                'category': 'readability',
                'priority': 'medium',
                'title': 'Enhance Readability',
                'description': 'Make your resume easier to scan',
                'actions': [
                    'Start bullets with strong action verbs',
                    'Keep bullet points concise (under 300 characters)',
                    'Write a clear 2-3 sentence summary',
                    'Use quantifiable achievements'
                ]
            })
        
        # Content recommendations
        if content_score < 70:
            recommendations.append({
                'category': 'content',
                'priority': 'high',
                'title': 'Strengthen Content',
                'description': 'Add more impactful content',
                'actions': [
                    'Include quantifiable achievements (numbers, percentages)',
                    'Add 8-15 relevant skills',
                    'Describe 3-5 recent work experiences',
                    'Include education details'
                ]
            })
        
        # Red flag recommendations
        for flag in red_flags:
            if flag['severity'] == 'high':
                recommendations.append({
                    'category': 'red_flags',
                    'priority': 'critical',
                    'title': f'Fix: {flag["type"].replace("_", " ").title()}',
                    'description': flag['message'],
                    'actions': [flag['recommendation']]
                })
        
        return recommendations
    
    def _explain_score(
        self,
        overall_score: float,
        formatting_score: float,
        keywords_score: float,
        structure_score: float,
        readability_score: float,
        content_score: float,
        red_flags: List[Dict]
    ) -> Dict:
        """Explain why the score is what it is"""
        explanation = {
            'summary': '',
            'strengths': [],
            'weaknesses': [],
            'impact_analysis': {}
        }
        
        # Determine overall assessment
        if overall_score >= 90:
            explanation['summary'] = 'Excellent! Your resume is highly ATS-compatible.'
        elif overall_score >= 75:
            explanation['summary'] = 'Good! Your resume should pass most ATS systems with minor improvements.'
        elif overall_score >= 60:
            explanation['summary'] = 'Fair. Your resume needs improvements to maximize ATS compatibility.'
        else:
            explanation['summary'] = 'Needs Work. Your resume may struggle with ATS systems.'
        
        # Identify strengths
        scores = {
            'Formatting': formatting_score,
            'Keywords': keywords_score,
            'Structure': structure_score,
            'Readability': readability_score,
            'Content': content_score
        }
        
        for category, score in scores.items():
            if score >= 80:
                explanation['strengths'].append(f'{category} is strong ({score:.0f}/100)')
            elif score < 60:
                explanation['weaknesses'].append(f'{category} needs improvement ({score:.0f}/100)')
        
        # Impact analysis
        for category, score in scores.items():
            weight = self.WEIGHTS[category.lower()]
            impact = (100 - score) * weight / 100
            explanation['impact_analysis'][category.lower()] = {
                'current_score': round(score, 1),
                'weight': weight,
                'points_lost': round(impact, 1),
                'potential_gain': round(impact, 1)
            }
        
        # Red flags impact
        if red_flags:
            critical_flags = [f for f in red_flags if f['severity'] == 'high']
            if critical_flags:
                explanation['weaknesses'].append(
                    f'{len(critical_flags)} critical ATS compatibility issues detected'
                )
        
        return explanation
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

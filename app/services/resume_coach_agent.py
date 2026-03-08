"""
AI Resume Coach Agent
Chat-based assistant for resume review, feedback, and improvement suggestions
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
import re

from app.services.ai_metering_service import AIMeteringService
from app.services.ats_scoring_service import ATSScoringService
from app.services.rewrite_service import RewriteService
from app.services.enhanced_skill_gap_service import EnhancedSkillGapService
from app.services.skill_extraction_service import SkillExtractionService
from app.models.resume import Resume
from app.models.resume_links import ResumeJobLink
from app.models.skill_intelligence import JobSkillExtracted, SkillImpactScore, SkillGapAnalysis

logger = logging.getLogger(__name__)


class ResumeCoachMode:
    """Coach interaction modes"""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    ROAST = "roast"
    RECRUITER_POV = "recruiter_pov"


class ResumeCoachAgent:
    """
    AI-powered resume coach providing personalized feedback and suggestions.
    Context-aware, safe, and explainable.
    """
    
    # Conversation context window
    MAX_CONTEXT_MESSAGES = 10
    
    # Safety filters
    BLOCKED_TOPICS = {
        'personal attacks', 'discrimination', 'illegal activities',
        'medical advice', 'financial advice', 'legal advice'
    }
    
    # Response templates
    GREETING_TEMPLATES = {
        ResumeCoachMode.PROFESSIONAL: "Hello! I'm your AI Resume Coach. I'm here to help you create a standout resume. What would you like to work on today?",
        ResumeCoachMode.FRIENDLY: "Hey there! 👋 Ready to make your resume awesome? I'm here to help! What should we focus on?",
        ResumeCoachMode.ROAST: "Alright, buckle up! I'm going to give you brutally honest feedback about your resume. Ready for some tough love? 🔥",
        ResumeCoachMode.RECRUITER_POV: "Welcome! I'll review your resume from a recruiter's perspective - what they look for in the first 6 seconds. Let's get started!"
    }
    
    def __init__(self, user_id: int, mode: str = ResumeCoachMode.PROFESSIONAL):
        self.user_id = user_id
        self.mode = mode
        self.conversation_history = []
        self.current_resume_context = None
        self.logger = logger
        self.skill_gap_service = EnhancedSkillGapService()
        self.skill_extractor = SkillExtractionService()
    
    async def chat(
        self,
        message: str,
        resume_id: Optional[int] = None,
        job_description: Optional[str] = None
    ) -> Dict:
        """
        Process user message and generate response.
        
        Args:
            message: User's message
            resume_id: Optional resume being discussed
            job_description: Optional job description for context
        
        Returns:
            Coach response with suggestions
        """
        try:
            # Safety check
            if not self._is_safe_message(message):
                return {
                    'response': "I'm here to help with resume-related questions only. Let's keep our conversation focused on improving your resume!",
                    'suggestions': [],
                    'blocked': True
                }
            
            # Load resume context if provided
            if resume_id and resume_id != self.current_resume_context:
                self._load_resume_context(resume_id)
            
            # Add to conversation history
            self._add_to_history('user', message)
            
            # Detect intent
            intent = self._detect_intent(message)
            
            # Generate response based on intent
            response = await self._generate_response(
                message,
                intent,
                job_description
            )
            
            # Add to history
            self._add_to_history('coach', response['response'])
            
            return response
            
        except Exception as e:
            self.logger.error(f"Chat failed: {str(e)}")
            return {
                'response': "I apologize, but I encountered an error. Could you please rephrase your question?",
                'suggestions': [],
                'error': str(e)
            }
    
    async def review_resume(
        self,
        resume_id: int,
        job_description: Optional[str] = None
    ) -> Dict:
        """
        Provide comprehensive resume review.
        
        Args:
            resume_id: Resume to review
            job_description: Optional job description
        
        Returns:
            Detailed review with feedback
        """
        try:
            # Load resume
            resume = Resume.query.filter_by(
                id=resume_id,
                user_id=self.user_id
            ).first()
            
            if not resume:
                raise ValueError("Resume not found")
            
            # Get ATS score
            ats_service = ATSScoringService()
            ats_report = ats_service.calculate_ats_score(
                resume_data=resume.content_json,
                job_description=job_description
            )
            
            # Generate review based on mode
            review = await self._generate_review(resume, ats_report, job_description)
            
            return review
            
        except Exception as e:
            self.logger.error(f"Resume review failed: {str(e)}")
            raise
    
    async def analyze_shortlisting_failure(
        self,
        resume_id: int,
        job_ids: List[int]
    ) -> Dict:
        """
        Analyze why resume might be getting rejected.
        
        Args:
            resume_id: Resume ID
            job_ids: List of job IDs where rejected
        
        Returns:
            Failure analysis with recommendations
        """
        try:
            # Get resume
            resume = Resume.query.get(resume_id)
            if not resume or resume.user_id != self.user_id:
                raise ValueError("Resume not found")
            
            # Get application links
            links = ResumeJobLink.query.filter(
                ResumeJobLink.resume_id == resume_id,
                ResumeJobLink.job_id.in_(job_ids)
            ).all()
            
            # Analyze patterns
            analysis = self._analyze_rejection_patterns(resume, links)
            
            # Generate explanation
            explanation = await self._generate_failure_explanation(analysis)
            
            return {
                'analysis': analysis,
                'explanation': explanation,
                'recommendations': self._generate_failure_recommendations(analysis)
            }
            
        except Exception as e:
            self.logger.error(f"Failure analysis failed: {str(e)}")
            raise
    
    async def get_improvement_suggestions(
        self,
        resume_id: int,
        focus_area: Optional[str] = None
    ) -> Dict:
        """
        Get targeted improvement suggestions.
        
        Args:
            resume_id: Resume ID
            focus_area: Optional area to focus on (summary, experience, skills, etc.)
        
        Returns:
            Improvement suggestions
        """
        try:
            resume = Resume.query.filter_by(
                id=resume_id,
                user_id=self.user_id
            ).first()
            
            if not resume:
                raise ValueError("Resume not found")
            
            # Get ATS analysis
            ats_service = ATSScoringService()
            ats_report = ats_service.calculate_ats_score(resume.content_json)
            
            # Generate suggestions
            suggestions = await self._generate_improvement_suggestions(
                resume,
                ats_report,
                focus_area
            )
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Suggestions failed: {str(e)}")
            raise
    
    # ========================================================================
    # Response Generation
    # ========================================================================
    
    async def _generate_response(
        self,
        message: str,
        intent: str,
        job_description: Optional[str]
    ) -> Dict:
        """Generate contextual response"""
        # Build prompt based on intent and mode
        prompt = self._build_response_prompt(message, intent, job_description)
        
        # Get metered AI response
        metered_resp = await AIMeteringService.ask_ai_metered(
            user_id=self.user_id,
            feature_type='resume_coach',
            prompt=prompt,
            temperature=temperature,
            max_tokens=300
        )
        
        if not metered_resp.get('success'):
            return {
                'response': metered_resp.get('message', 'AI Coach is temporarily unavailable.'),
                'suggestions': [],
                'intent': intent,
                'mode': self.mode
            }

        ai_response = metered_resp.get('text', '')
        
        # Extract suggestions
        suggestions = self._extract_suggestions(ai_response)
        
        # Format response
        response = self._format_response(ai_response, intent)
        
        return {
            'response': response,
            'suggestions': suggestions,
            'intent': intent,
            'mode': self.mode
        }
    
    async def recommend_resume_edits(
        self,
        resume_id: int,
        job_description: str
    ) -> Dict:
        """
        Recommend specific resume edits based on skill gaps.
        """
        try:
            # Perform gap analysis
            analysis = self.skill_gap_service.analyze_gap(
                resume_id=resume_id,
                job_id=0, # Use raw text analysis if no job_id
                user_id=self.user_id,
                save_to_db=False
            )
            
            # Generate recommendations using LLM for natural language edits
            prompt = f"""As an AI Resume Coach, recommend specific resume edits based on these skill gaps:
            
            Resume Context: {self._get_resume_context_text()}
            
            Missing Mandatory Skills: {', '.join([s['skill_name'] for s in analysis['gaps']['missing_mandatory']])}
            Missing Preferred Skills: {', '.join([s['skill_name'] for s in analysis['gaps']['missing_preferred']])}
            Weak Skills: {', '.join([s['skill_name'] for s in analysis['gaps']['weak_proficiency']])}
            
            Target Job Description (Snippet): {job_description[:500]}
            
            Provide:
            1. 3-5 Specific bullet points for the 'Experience' or 'Skills' section
            2. Advice on where to incorporate these naturally
            3. Explanation of how these changes improve the ATS score
            
            Recommendations:"""
            
            metered_resp = await AIMeteringService.ask_ai_metered(
                user_id=self.user_id,
                feature_type='resume_coach',
                prompt=prompt,
                temperature=0.5,
                max_tokens=600
            )
            
            if not metered_resp.get('success'):
                return {'error': metered_resp.get('message'), 'gaps': analysis['gaps']}

            ai_recommendation = metered_resp.get('text', '')
            
            return {
                'recommendations': ai_recommendation,
                'gaps': analysis['gaps'],
                'impact': analysis['ats_impact']
            }
            
        except Exception as e:
            self.logger.error(f"Resume edit recommendation failed: {str(e)}")
            raise
    
    async def _generate_review(
        self,
        resume: Resume,
        ats_report: Dict,
        job_description: Optional[str]
    ) -> Dict:
        """Generate comprehensive resume review"""
        prompt = self._build_review_prompt(resume, ats_report, job_description)
        
        # Get metered review
        temperature = 0.8 if self.mode == ResumeCoachMode.ROAST else 0.5
        metered_resp = await AIMeteringService.ask_ai_metered(
            user_id=self.user_id,
            feature_type='resume_coach',
            prompt=prompt,
            temperature=temperature,
            max_tokens=500
        )
        
        if not metered_resp.get('success'):
            review_text = metered_resp.get('message', 'Failed to generate review.')
        else:
            review_text = metered_resp.get('text', '')
        
        # Structure review
        return {
            'overall_feedback': review_text,
            'ats_score': ats_report['overall_score'],
            'grade': ats_report['grade'],
            'strengths': self._extract_strengths(review_text, ats_report),
            'weaknesses': self._extract_weaknesses(review_text, ats_report),
            'action_items': self._extract_action_items(review_text),
            'mode': self.mode
        }
    
    async def _generate_improvement_suggestions(
        self,
        resume: Resume,
        ats_report: Dict,
        focus_area: Optional[str]
    ) -> Dict:
        """Generate targeted improvement suggestions"""
        prompt = self._build_improvement_prompt(resume, ats_report, focus_area)
        
        metered_resp = await AIMeteringService.ask_ai_metered(
            user_id=self.user_id,
            feature_type='resume_coach',
            prompt=prompt,
            temperature=0.5,
            max_tokens=400
        )
        
        if not metered_resp.get('success'):
            suggestions_text = metered_resp.get('message', '')
        else:
            suggestions_text = metered_resp.get('text', '')
        
        return {
            'focus_area': focus_area or 'overall',
            'suggestions': self._parse_suggestions(suggestions_text),
            'priority': self._prioritize_suggestions(ats_report, focus_area)
        }
    
    # ========================================================================
    # Prompt Templates
    # ========================================================================
    
    def _build_response_prompt(
        self,
        message: str,
        intent: str,
        job_description: Optional[str]
    ) -> str:
        """Build prompt for chat response"""
        mode_context = self._get_mode_context()
        resume_context = self._get_resume_context_text()
        conversation_context = self._get_conversation_context()
        
        job_context = f"\nTarget Job:\n{job_description[:500]}" if job_description else ""
        
        # Inject Skill Intelligence if relevant
        skill_intelligence = self._get_skill_intelligence_context(message)
        
        # Inject Gap Analysis if relevant
        gap_analysis = ""
        if (intent == 'skill_gap' or 'gap' in message.lower()) and self.current_resume_context and job_description:
            gap_analysis = self._get_gap_analysis_context(self.current_resume_context['id'], job_description)
        
        return f"""{mode_context}
        
User's Question: {message}
Intent: {intent}

{resume_context}
{job_context}
{skill_intelligence}
{gap_analysis}

Recent Conversation:
{conversation_context}

Provide a helpful, {self.mode} response that:
1. Directly addresses the user's question
2. Provides specific, actionable advice
3. References their resume context and skill gaps if relevant
4. Explains why certain skills matter if asked (using the provided Skill Intelligence)
5. Stays focused on resume improvement and career success
6. Is encouraging and constructive

Response:"""
    
    def _build_review_prompt(
        self,
        resume: Resume,
        ats_report: Dict,
        job_description: Optional[str]
    ) -> str:
        """Build prompt for resume review"""
        mode_instructions = {
            ResumeCoachMode.PROFESSIONAL: "Provide professional, constructive feedback",
            ResumeCoachMode.FRIENDLY: "Provide friendly, encouraging feedback with emojis",
            ResumeCoachMode.ROAST: "Provide brutally honest, direct feedback (but still helpful)",
            ResumeCoachMode.RECRUITER_POV: "Provide feedback from a recruiter's perspective - what they see in 6 seconds"
        }
        
        instruction = mode_instructions.get(self.mode, mode_instructions[ResumeCoachMode.PROFESSIONAL])
        
        job_context = f"\nTarget Job:\n{job_description[:500]}" if job_description else ""
        
        return f"""You are a resume coach. {instruction}.

Resume Title: {resume.title}
ATS Score: {ats_report['overall_score']}/100 (Grade: {ats_report['grade']})

Resume Content:
{self._summarize_resume(resume.content_json)}

ATS Breakdown:
- Formatting: {ats_report['breakdown']['formatting']['score']}/100
- Keywords: {ats_report['breakdown']['keywords']['score']}/100
- Structure: {ats_report['breakdown']['structure']['score']}/100
- Readability: {ats_report['breakdown']['readability']['score']}/100
- Content: {ats_report['breakdown']['content']['score']}/100

Red Flags: {len(ats_report['red_flags'])}
{job_context}

Provide a comprehensive review covering:
1. Overall impression
2. Key strengths (2-3 points)
3. Critical weaknesses (2-3 points)
4. Top 3 action items for improvement

Review:"""
    
    def _build_improvement_prompt(
        self,
        resume: Resume,
        ats_report: Dict,
        focus_area: Optional[str]
    ) -> str:
        """Build prompt for improvement suggestions"""
        focus_text = f" focusing on the {focus_area} section" if focus_area else ""
        
        return f"""Provide specific improvement suggestions for this resume{focus_text}.

Resume Summary:
{self._summarize_resume(resume.content_json)}

Current ATS Score: {ats_report['overall_score']}/100

Weaknesses:
{self._format_weaknesses(ats_report)}

Provide 5 specific, actionable suggestions that will improve the ATS score.
For each suggestion:
1. What to change
2. Why it matters
3. Example of how to implement it

Suggestions:"""
    
    # ========================================================================
    # Analysis Methods
    # ========================================================================
    
    def _analyze_rejection_patterns(
        self,
        resume: Resume,
        links: List[ResumeJobLink]
    ) -> Dict:
        """Analyze patterns in rejections"""
        patterns = {
            'total_applications': len(links),
            'avg_match_score': 0,
            'common_issues': [],
            'timing_analysis': {}
        }
        
        if not links:
            return patterns
        
        # Calculate average match score
        match_scores = [l.match_score for l in links if l.match_score]
        if match_scores:
            patterns['avg_match_score'] = sum(match_scores) / len(match_scores)
        
        # Analyze timing
        viewed_count = sum(1 for l in links if l.viewed_at)
        patterns['timing_analysis'] = {
            'viewed_rate': (viewed_count / len(links) * 100) if links else 0,
            'avg_time_to_view': self._calculate_avg_time_to_view(links)
        }
        
        # Identify common issues
        if patterns['avg_match_score'] < 60:
            patterns['common_issues'].append('Low keyword match with job descriptions')
        
        if patterns['timing_analysis']['viewed_rate'] < 30:
            patterns['common_issues'].append('Resume not being viewed - likely ATS filtering')
        
        return patterns
    
    async def _generate_failure_explanation(self, analysis: Dict) -> str:
        """Generate explanation for shortlisting failures"""
        prompt = f"""Explain why this resume might be getting rejected based on this data:

Total Applications: {analysis['total_applications']}
Average Match Score: {analysis['avg_match_score']:.1f}%
Viewed Rate: {analysis['timing_analysis']['viewed_rate']:.1f}%

Common Issues:
{chr(10).join(f'- {issue}' for issue in analysis['common_issues'])}

Provide a clear, empathetic explanation of what's likely happening and why.

Explanation:"""
        
        return ask_ai(prompt, temperature=0.5, max_tokens=200)
    
    def _generate_failure_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate recommendations based on failure analysis"""
        recommendations = []
        
        if analysis['avg_match_score'] < 60:
            recommendations.append({
                'priority': 'high',
                'issue': 'Low keyword match',
                'action': 'Add more relevant keywords from job descriptions',
                'impact': 'Could improve match score by 20-30 points'
            })
        
        if analysis['timing_analysis']['viewed_rate'] < 30:
            recommendations.append({
                'priority': 'critical',
                'issue': 'Resume not being viewed',
                'action': 'Optimize for ATS - remove tables, images, fancy formatting',
                'impact': 'Essential for getting past ATS filters'
            })
        
        return recommendations
    
    # ========================================================================
    # Intent Detection
    # ========================================================================
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        # Review intent
        if any(word in message_lower for word in ['review', 'feedback', 'look at', 'check']):
            return 'review'
        
        # Improvement intent
        if any(word in message_lower for word in ['improve', 'better', 'enhance', 'fix']):
            return 'improve'
        
        # Question intent
        if any(word in message_lower for word in ['how', 'what', 'why', 'when', 'should', 'can']):
            # Check for skill importance questions
            if any(word in message_lower for word in ['important', 'needed', 'useful', 'matter', 'role']):
                return 'skill_intelligence'
            return 'question'
        
        # Skill gap intent
        if any(word in message_lower for word in ['gap', 'missing', 'requirement', 'needed skills']):
            return 'skill_gap'
        
        # Specific section
        if any(word in message_lower for word in ['summary', 'experience', 'skills', 'education']):
            return 'section_specific'
        
        # General conversation
        return 'general'
    
    # ========================================================================
    # Safety & Validation
    # ========================================================================
    
    def _is_safe_message(self, message: str) -> bool:
        """Check if message is safe and on-topic"""
        message_lower = message.lower()
        
        # Check for blocked topics
        for topic in self.BLOCKED_TOPICS:
            if topic in message_lower:
                return False
        
        # Check message length
        if len(message) > 1000:
            return False
        
        # Basic profanity filter (simplified)
        profanity_patterns = [
            r'\b(fuck|shit|damn|hell|ass)\b'
        ]
        
        for pattern in profanity_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                # Allow in roast mode
                if self.mode != ResumeCoachMode.ROAST:
                    return False
        
        # Prompt injection prevention
        injection_keywords = [
            'ignore previous instructions',
            'forget everything',
            'system prompt',
            'you are now a',
            'new rules',
            'bypass',
            'override'
        ]
        
        if any(keyword in message_lower for keyword in injection_keywords):
            self.logger.warning(f"Potential prompt injection detected: {message}")
            return False
            
        return True
    
    # ========================================================================
    # Context Management
    # ========================================================================
    
    def _load_resume_context(self, resume_id: int):
        """Load resume into context"""
        resume = Resume.query.filter_by(
            id=resume_id,
            user_id=self.user_id
        ).first()
        
        if resume:
            self.current_resume_context = {
                'id': resume.id,
                'title': resume.title,
                'content': resume.content_json,
                'ats_score': resume.ats_score
            }
    
    def _add_to_history(self, role: str, message: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            'role': role,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Keep only recent messages
        if len(self.conversation_history) > self.MAX_CONTEXT_MESSAGES:
            self.conversation_history = self.conversation_history[-self.MAX_CONTEXT_MESSAGES:]
    
    def _get_conversation_context(self) -> str:
        """Get recent conversation as text"""
        if not self.conversation_history:
            return "No previous conversation"
        
        context_lines = []
        for msg in self.conversation_history[-5:]:
            role = "User" if msg['role'] == 'user' else "Coach"
            context_lines.append(f"{role}: {msg['message'][:100]}")
        
        return '\n'.join(context_lines)
    
    def _get_resume_context_text(self) -> str:
        """Get resume context as text"""
        if not self.current_resume_context:
            return "No resume loaded"
        
        return f"""Current Resume: {self.current_resume_context['title']}
ATS Score: {self.current_resume_context.get('ats_score', 'N/A')}/100"""

    def _get_skill_intelligence_context(self, message: str) -> str:
        """Get market context and importance for skills mentioned in message"""
        try:
            # Extract skills from user message
            found_skills = self.skill_extractor._extract_skills_from_text(message)
            if not found_skills:
                return ""
            
            intelligence_parts = []
            for skill_key in found_skills:
                # Look up in SkillImpactScore
                skill_info = SkillImpactScore.query.filter(
                    SkillImpactScore.skill_name_normalized == skill_key
                ).first()
                
                if skill_info:
                    demand_msg = f"Market Demand: {skill_info.market_demand_score}/10"
                    salary_msg = f"Salary Impact: +{skill_info.salary_impact_percentage}%" if skill_info.salary_impact_percentage else "Salary Impact: Significant"
                    intelligence_parts.append(
                        f"Skill: {skill_info.skill_name}\n"
                        f"- {demand_msg}\n"
                        f"- {salary_msg}\n"
                        f"- Difficulty: {skill_info.difficulty_level}\n"
                        f"- Why it matters: Critical for this role category ({skill_info.category})"
                    )
            
            if intelligence_parts:
                return "\n--- Skill Intelligence ---\n" + "\n\n".join(intelligence_parts)
            return ""
        except Exception as e:
            self.logger.error(f"Skill intelligence context failed: {str(e)}")
            return ""

    def _get_gap_analysis_context(self, resume_id: int, job_description: str) -> str:
        """Get detailed gap analysis context between resume and job"""
        try:
            # Extract skills from JD temporarily to compare
            jd_skills = self.skill_extractor.extract_from_job_description(job_description)
            
            # Get resume skills
            resume = Resume.query.get(resume_id)
            if not resume:
                return ""
            
            resume_skills = self.skill_extractor.extract_from_resume(
                json.dumps(resume.content_json), 
                resume_sections=resume.content_json
            )
            
            # Perform a quick comparison
            resume_keys = {s['skill_name_normalized'] for s in resume_skills}
            
            missing_mandatory = []
            missing_preferred = []
            
            for s in jd_skills:
                if s['skill_name_normalized'] not in resume_keys:
                    if s['requirement_type'] == 'mandatory':
                        missing_mandatory.append(s['skill_name'])
                    elif s['requirement_type'] == 'preferred':
                        missing_preferred.append(s['skill_name'])
            
            context = "\n--- Skill Gap Analysis ---\n"
            if missing_mandatory:
                context += f"CRITICAL GAPS (Mandatory): {', '.join(missing_mandatory[:5])}\n"
            if missing_preferred:
                context += f"SUGGESTED GAPS (Preferred): {', '.join(missing_preferred[:5])}\n"
            
            if not missing_mandatory and not missing_preferred:
                context += "No major skill gaps detected compared to this job description!\n"
                
            return context
        except Exception as e:
            self.logger.error(f"Gap analysis context failed: {str(e)}")
            return ""

    def _get_mode_context(self) -> str:
        """Get mode-specific context"""
        contexts = {
            ResumeCoachMode.PROFESSIONAL: "You are a professional resume coach providing expert advice.",
            ResumeCoachMode.FRIENDLY: "You are a friendly resume coach who uses emojis and encouraging language.",
            ResumeCoachMode.ROAST: "You are giving brutally honest feedback. Be direct and critical, but ultimately helpful.",
            ResumeCoachMode.RECRUITER_POV: "You are explaining things from a recruiter's perspective - what they look for in 6 seconds."
        }
        
        return contexts.get(self.mode, contexts[ResumeCoachMode.PROFESSIONAL])
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _summarize_resume(self, content: Dict) -> str:
        """Create brief summary of resume"""
        summary_parts = []
        
        if 'summary' in content:
            summary_parts.append(f"Summary: {content['summary'][:200]}")
        
        if 'skills' in content:
            skills = content['skills'][:10]
            summary_parts.append(f"Skills: {', '.join(skills)}")
        
        if 'experience' in content:
            exp_count = len(content['experience'])
            summary_parts.append(f"Experience: {exp_count} positions")
        
        return '\n'.join(summary_parts)
    
    def _format_weaknesses(self, ats_report: Dict) -> str:
        """Format weaknesses from ATS report"""
        weaknesses = []
        
        for component, data in ats_report['breakdown'].items():
            if data['score'] < 70:
                weaknesses.append(f"- {component.title()}: {data['score']}/100")
        
        return '\n'.join(weaknesses) if weaknesses else "No major weaknesses detected"
    
    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract actionable suggestions from text"""
        # Simple extraction - look for numbered lists or bullet points
        suggestions = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Clean up
                cleaned = re.sub(r'^[\d\-•\.\)]+\s*', '', line)
                if cleaned:
                    suggestions.append(cleaned)
        
        return suggestions[:5]  # Top 5
    
    def _extract_strengths(self, review_text: str, ats_report: Dict) -> List[str]:
        """Extract strengths from review"""
        strengths = []
        
        # From ATS report
        for component, data in ats_report['breakdown'].items():
            if data['score'] >= 80:
                strengths.append(f"Strong {component}")
        
        return strengths[:3]
    
    def _extract_weaknesses(self, review_text: str, ats_report: Dict) -> List[str]:
        """Extract weaknesses from review"""
        weaknesses = []
        
        # From ATS report
        for component, data in ats_report['breakdown'].items():
            if data['score'] < 70:
                weaknesses.append(f"Weak {component} ({data['score']}/100)")
        
        return weaknesses[:3]
    
    def _extract_action_items(self, review_text: str) -> List[str]:
        """Extract action items from review"""
        return self._extract_suggestions(review_text)
    
    def _parse_suggestions(self, text: str) -> List[Dict]:
        """Parse suggestions into structured format"""
        suggestions = []
        
        lines = text.split('\n')
        current_suggestion = None
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                if current_suggestion:
                    suggestions.append(current_suggestion)
                
                current_suggestion = {
                    'text': re.sub(r'^[\d\-•\.\)]+\s*', '', line),
                    'priority': 'medium'
                }
        
        if current_suggestion:
            suggestions.append(current_suggestion)
        
        return suggestions
    
    def _prioritize_suggestions(self, ats_report: Dict, focus_area: Optional[str]) -> str:
        """Determine priority level"""
        if ats_report['overall_score'] < 60:
            return 'critical'
        elif ats_report['overall_score'] < 75:
            return 'high'
        else:
            return 'medium'
    
    def _format_response(self, response: str, intent: str) -> str:
        """Format response based on mode"""
        # Add emoji for friendly mode
        if self.mode == ResumeCoachMode.FRIENDLY and not any(emoji in response for emoji in ['👍', '✨', '🎯', '💪']):
            response += " 💪"
        
        return response.strip()
    
    def _calculate_avg_time_to_view(self, links: List[ResumeJobLink]) -> Optional[float]:
        """Calculate average time from application to view"""
        times = []
        
        for link in links:
            if link.applied_at and link.viewed_at:
                delta = (link.viewed_at - link.applied_at).total_seconds() / 3600  # hours
                times.append(delta)
        
        return sum(times) / len(times) if times else None

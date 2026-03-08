"""
AI Interview Preparation Service

Provides mock interviews, question generation, and feedback using AI.
"""

import openai
import os
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class InterviewPrep:
    """AI-powered interview preparation"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
    
    def generate_interview_questions(self, job_title, company_name='', difficulty='medium'):
        """
        Generate interview questions for a role
        
        Args:
            job_title (str): Job title
            company_name (str): Company name (optional)
            difficulty (str): easy, medium, hard
            
        Returns:
            list: Interview questions with categories
        """
        try:
            prompt = f"""
Generate a comprehensive list of interview questions for a {job_title} position{f' at {company_name}' if company_name else ''}.

Difficulty level: {difficulty}

Include:
1. 5 behavioral questions (STAR method)
2. 5 technical questions
3. 3 situational questions
4. 2 company-specific questions

For each question, provide:
- The question
- Category (behavioral/technical/situational/company)
- Difficulty (easy/medium/hard)
- Tips for answering

Format as JSON array with keys: question, category, difficulty, tips
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert interview coach and hiring manager."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content.strip()
            
            try:
                questions = json.loads(result)
            except:
                # Fallback parsing
                questions = self._get_default_questions(job_title)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            return self._get_default_questions(job_title)
    
    def evaluate_answer(self, question, answer, job_title):
        """
        Evaluate an interview answer
        
        Args:
            question (str): Interview question
            answer (str): User's answer
            job_title (str): Job title for context
            
        Returns:
            dict: Evaluation with score and feedback
        """
        try:
            prompt = f"""
Evaluate this interview answer for a {job_title} position:

**Question:** {question}

**Answer:** {answer}

Provide:
1. Score (0-10)
2. Strengths (what was good)
3. Weaknesses (what could be improved)
4. Improved version (how to answer better)
5. Overall feedback

Format as JSON with keys: score, strengths, weaknesses, improved_answer, feedback
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert interview coach providing constructive feedback."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content.strip()
            
            try:
                evaluation = json.loads(result)
            except:
                evaluation = {
                    'score': 7,
                    'strengths': ['Good attempt'],
                    'weaknesses': ['Could be more specific'],
                    'improved_answer': result,
                    'feedback': result
                }
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating answer: {str(e)}")
            return {
                'score': 0,
                'strengths': [],
                'weaknesses': [],
                'improved_answer': '',
                'feedback': f'Error: {str(e)}'
            }
    
    def generate_star_response(self, question, situation, task, action, result):
        """
        Generate a polished STAR response
        
        Args:
            question (str): Interview question
            situation (str): Situation description
            task (str): Task description
            action (str): Action taken
            result (str): Result achieved
            
        Returns:
            str: Polished STAR response
        """
        try:
            prompt = f"""
Create a polished STAR method response for this interview question:

**Question:** {question}

**Situation:** {situation}
**Task:** {task}
**Action:** {action}
**Result:** {result}

Create a cohesive, professional response that:
1. Flows naturally
2. Highlights achievements
3. Uses strong action verbs
4. Quantifies results
5. Is concise (2-3 minutes when spoken)

Provide the polished response:
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an interview coach helping craft compelling STAR responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            star_response = response.choices[0].message.content.strip()
            
            return star_response
            
        except Exception as e:
            logger.error(f"Error generating STAR response: {str(e)}")
            return f"In {situation}, I was tasked with {task}. I took action by {action}, which resulted in {result}."
    
    def get_company_questions(self, company_name):
        """
        Generate company-specific questions to ask
        
        Args:
            company_name (str): Company name
            
        Returns:
            list: Questions to ask the interviewer
        """
        try:
            prompt = f"""
Generate 10 thoughtful questions a candidate should ask when interviewing at {company_name}.

Include questions about:
1. Company culture and values
2. Team dynamics
3. Growth opportunities
4. Product/technology
5. Success metrics

Make them specific and insightful, not generic.

Return as a numbered list.
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a career coach helping candidates prepare for interviews."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=800
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse into list
            questions = [q.strip() for q in result.split('\n') if q.strip() and q.strip()[0].isdigit()]
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating company questions: {str(e)}")
            return [
                "What does success look like in this role?",
                "How does the team collaborate?",
                "What are the biggest challenges facing the team?",
                "What opportunities for growth exist?",
                "How is performance measured?"
            ]
    
    def get_interview_tips(self, interview_type='general'):
        """
        Get interview tips and best practices
        
        Args:
            interview_type (str): Type of interview
            
        Returns:
            dict: Tips organized by category
        """
        tips = {
            'general': {
                'before': [
                    'Research the company thoroughly',
                    'Practice common questions',
                    'Prepare questions to ask',
                    'Review your resume',
                    'Plan your outfit'
                ],
                'during': [
                    'Arrive 10-15 minutes early',
                    'Make eye contact and smile',
                    'Use the STAR method for behavioral questions',
                    'Ask clarifying questions if needed',
                    'Take notes'
                ],
                'after': [
                    'Send a thank-you email within 24 hours',
                    'Reflect on what went well',
                    'Note areas for improvement',
                    'Follow up if you don\'t hear back',
                    'Continue your job search'
                ]
            },
            'technical': {
                'before': [
                    'Review data structures and algorithms',
                    'Practice coding problems',
                    'Understand system design concepts',
                    'Review your projects',
                    'Prepare to explain your code'
                ],
                'during': [
                    'Think out loud',
                    'Ask clarifying questions',
                    'Start with a brute force solution',
                    'Optimize your solution',
                    'Test your code'
                ],
                'after': [
                    'Review problems you struggled with',
                    'Practice similar problems',
                    'Update your knowledge gaps',
                    'Send a thank-you email',
                    'Continue practicing'
                ]
            },
            'behavioral': {
                'before': [
                    'Prepare STAR stories',
                    'Review common behavioral questions',
                    'Identify your strengths and weaknesses',
                    'Prepare examples of teamwork',
                    'Think about challenges you\'ve overcome'
                ],
                'during': [
                    'Use the STAR method',
                    'Be specific and concise',
                    'Focus on your role and impact',
                    'Show self-awareness',
                    'Be authentic'
                ],
                'after': [
                    'Reflect on your answers',
                    'Note questions you struggled with',
                    'Prepare better examples',
                    'Send a thank-you email',
                    'Practice for next time'
                ]
            }
        }
        
        return tips.get(interview_type, tips['general'])
    
    def _get_default_questions(self, job_title):
        """Fallback default questions"""
        
        return [
            {
                'question': f'Tell me about yourself and why you\'re interested in this {job_title} role.',
                'category': 'behavioral',
                'difficulty': 'easy',
                'tips': 'Use a brief professional summary, highlight relevant experience, and show enthusiasm.'
            },
            {
                'question': 'Describe a challenging project you worked on and how you overcame obstacles.',
                'category': 'behavioral',
                'difficulty': 'medium',
                'tips': 'Use the STAR method: Situation, Task, Action, Result.'
            },
            {
                'question': f'What are the key skills needed for a {job_title}?',
                'category': 'technical',
                'difficulty': 'easy',
                'tips': 'Mention both technical and soft skills, and provide examples.'
            },
            {
                'question': 'How do you handle tight deadlines and pressure?',
                'category': 'situational',
                'difficulty': 'medium',
                'tips': 'Give a specific example showing your time management and stress handling.'
            },
            {
                'question': 'Where do you see yourself in 5 years?',
                'category': 'behavioral',
                'difficulty': 'easy',
                'tips': 'Show ambition while aligning with the company\'s growth path.'
            }
        ]


# Helper function
def prepare_for_interview(job_title, company_name=''):
    """
    Get comprehensive interview preparation
    
    Args:
        job_title (str): Job title
        company_name (str): Company name
        
    Returns:
        dict: Interview prep materials
    """
    prep = InterviewPrep()
    
    return {
        'questions': prep.generate_interview_questions(job_title, company_name),
        'company_questions': prep.get_company_questions(company_name) if company_name else [],
        'tips': prep.get_interview_tips('general')
    }

import logging
import json
from app.services.ai_metering_service import AIMeteringService

logger = logging.getLogger(__name__)

class InterviewService:
    """
    AI Service for generating interview questions and evaluating answers.
    Uses the central llm_service AI Gateway.
    """

    @staticmethod
    async def generate_questions(user_id, job_title, company_name='', job_description='', difficulty='medium'):
        """
        Generate interview questions based on job details.
        """
        try:
            prompt = f"""
            Generate a list of 5 interview questions for a {job_title} position{f' at {company_name}' if company_name else ''}.
            Difficulty: {difficulty}.
            
            Context (Job Description):
            {job_description[:500] if job_description else 'N/A'}

            Provide the output as a valid JSON array of objects.
            Each object should have:
            - "id": a unique index (1, 2, 3...)
            - "question": string
            - "category": "technical" | "behavioral" | "situational"
            - "difficulty": "easy" | "medium" | "hard"
            
            Example JSON:
            [
                {{"id": 1, "question": "Explain polymorphism.", "category": "technical", "difficulty": "medium"}}
            ]
            """

            metered_resp = await AIMeteringService.ask_ai_metered(
                user_id=user_id,
                feature_type='interview_coach',
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=1500,
                temperature=0.7
            )
            
            if not metered_resp.get('success'):
                logger.error(f"Metered Question Generation failed: {metered_resp.get('message')}")
                return [
                    {"id": 1, "question": f"Tell me about your experience relevant to {job_title}.", "category": "behavioral", "difficulty": "easy"},
                    {"id": 2, "question": "What is your biggest professional weakness?", "category": "behavioral", "difficulty": "medium"},
                    {"id": 3, "question": "Describe a difficult problem you solved.", "category": "situational", "difficulty": "medium"}
                ]

            response_text = metered_resp.get('text', '')
            
            # Simple cleanup for JSON parsing if the LLM wraps it in markdown blocks
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            
            questions = json.loads(clean_text)
            return questions

        except Exception as e:
            logger.error(f"Error generating interview questions: {str(e)}")
            # Fallback questions
            return [
                {"id": 1, "question": f"Tell me about your experience relevant to {job_title}.", "category": "behavioral", "difficulty": "easy"},
                {"id": 2, "question": "What is your biggest professional weakness?", "category": "behavioral", "difficulty": "medium"},
                {"id": 3, "question": "Describe a difficult problem you solved.", "category": "situational", "difficulty": "mean"}
            ]

    @staticmethod
    async def evaluate_answer(user_id, question, user_answer, job_title):
        """
        Evaluate a candidate's answer.
        """
        try:
            prompt = f"""
            Evaluate the following interview answer for a {job_title} role.

            Question: "{question}"
            Candidate Answer: "{user_answer}"

            Provide a constructive evaluation in valid JSON format with these fields:
            - "score": integer (0-100)
            - "strengths": list of strings (what they did well)
            - "weaknesses": list of strings (what is missing)
            - "improved_answer": string (a better version of the answer using STAR method if applicable)
            - "feedback": string (general constructive feedback)
            """

            system_prompt = "You are a supportive but critical interview coach."

            metered_resp = await AIMeteringService.ask_ai_metered(
                user_id=user_id,
                feature_type='interview_coach',
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=1000,
                temperature=0.7
            )
            
            if not metered_resp.get('success'):
                logger.error(f"Metered Answer Evaluation failed: {metered_resp.get('message')}")
                return {
                    "score": 0,
                    "strengths": [],
                    "weaknesses": [f"Error: {metered_resp.get('message')}"],
                    "improved_answer": "N/A",
                    "feedback": "Could not evaluate answer at this time due to credit or API issues."
                }

            response_text = metered_resp.get('text', '')
            
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            evaluation = json.loads(clean_text)
            return evaluation

        except Exception as e:
            logger.error(f"Error evaluating answer: {str(e)}")
            return {
                "score": 0,
                "strengths": [],
                "weaknesses": ["System error during evaluation"],
                "improved_answer": "N/A",
                "feedback": "Could not evaluate answer at this time."
            }

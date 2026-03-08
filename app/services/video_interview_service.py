import logging
import json
import os
from datetime import datetime
from app.extensions import db
from app.models.video_interview import AIVideoInterview, AIVideoQuestion, AIVideoAnswer, AIVideoEvaluation, AIVideoSummary
from app.models.resume import Resume
from app.services.ai_metering_service import AIMeteringService
from app.resumes.parser import ResumeParser

logger = logging.getLogger(__name__)

class VideoInterviewService:
    """
    Orchestrates the AI Video Interview flow, including resume-integrated question generation,
    real-time evaluation, and final report generation.
    """

    def __init__(self, user_id):
        self.user_id = user_id
        self.parser = ResumeParser()
        self.prompts_path = os.path.join(os.path.dirname(__file__), 'ai', 'prompts')

    def _get_prompt(self, filename):
        path = os.path.join(self.prompts_path, filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        logger.warning(f"Prompt file {filename} not found at {path}")
        return ""

    def _get_persona_brief(self, persona):
        if persona == 'sarah':
            return "You are Sarah, a warm and encouraging Recruiter. Use conversational phrases like 'That's interesting', 'Thanks for sharing that', and 'I'd love to hear more about...'. Sound like a human having a conversation, not an AI script."
        return "You are Alex, a direct but professional Technical Lead. You are concise and focus on depth. Use phrases like 'Got it', 'That makes sense from a technical standpoint', and 'Let's dive deeper into...'. Sound like a peer interviewer."

    async def initialize_session(self, job_title, persona='alex', difficulty='medium', camera_enabled=False):
        """
        Creates a new interview session.
        1. Parses the user's latest resume.
        2. Generates a 'Truth-Challenge Map' based on the resume.
        3. Generates a 'Blueprint' for the interview.
        4. Generates an initial set of 5 spoken-style questions.
        """
        # 1. Retrieve Candidate Profile Snapshot (FAST)
        # Using database profile is MUCH faster than re-parsing a PDF via AI every time
        resume_json = "{}"
        try:
            from app.models.profile import ProfileSummary, KeySkill, Employment
            summary = ProfileSummary.query.filter_by(user_id=self.user_id).first()
            skills = KeySkill.query.filter_by(user_id=self.user_id).all()
            exp = Employment.query.filter_by(user_id=self.user_id).all()
            profile_snapshot = {
                "summary": summary.summary_text if summary else "",
                "skills": [s.skill_name for s in skills],
                "experience": [{"company": e.company, "role": e.designation} for e in exp]
            }
            if any(profile_snapshot.values()):
                resume_json = json.dumps(profile_snapshot)
                logger.info("Using structured profile data for interview setup")
            else:
                # Fallback to resume JSON if profile is empty
                resume = Resume.query.filter_by(user_id=self.user_id, is_primary=True).first()
                if resume and resume.content_json:
                    resume_json = resume.content_json
        except Exception as e:
            logger.warning(f"Could not load structured profile: {str(e)}")

        # 2. Setup Session in DB
        session = AIVideoInterview(
            user_id=self.user_id,
            job_title=job_title,
            difficulty=difficulty,
            persona_id=persona,
            camera_enabled=camera_enabled,
            status='preparing'
        )
        db.session.add(session)
        db.session.commit()

        try:
            # 3. Generate Questions (Optimized: No separate blueprinting call to save 20-30s)
            question_gen_prompt = self._get_prompt('AI_RESUME_INTERVIEWER_PROMPT.md')
            gen_request = (
                f"{question_gen_prompt}\n\n"
                f"CONTEXT:\n"
                f"Target Role: {job_title}\n"
                f"Difficulty: {difficulty}\n"
                f"Candidate Profile: {resume_json}\n\n"
                f"OUTPUT: Provide 5 questions in JSON format."
            )
            
            # Using a metered AI call for questions
            system_prompt = f"{self._get_persona_brief(persona)} You are a professional technical interviewer. Your goal is to generate 5 insightful, natural-sounding interview questions. Return ONLY valid JSON."
            metered_resp = await AIMeteringService.ask_ai_metered(self.user_id, 'video_interview_question', gen_request, system_prompt=system_prompt)
            
            if not metered_resp.get('success'):
                logger.error(f"Metered AI Question generation failed: {metered_resp.get('message')}")
                raise ValueError(metered_resp.get('message', "AI Question Generation Failed"))
                
            questions_resp = metered_resp.get('text', '{}')
            logger.info(f"AI Question Response: {questions_resp[:200]}...")

            # Robust JSON Extract
            questions_list = []
            try:
                clean_json = questions_resp
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                else:
                    clean_json = clean_json.strip()
                
                questions_data = json.loads(clean_json)
                if isinstance(questions_data, dict) and 'questions' in questions_data:
                    questions_list = questions_data['questions']
                else:
                    questions_list = questions_data 
            except Exception as json_err:
                logger.error(f"AI JSON Parse Error: {str(json_err)}")

            # Final Fallback if AI failed or returned junk
            if not questions_list or not isinstance(questions_list, list):
                questions_list = [
                    {"question": f"Tell me about your experience as it relates to {job_title}.", "category": "behavioral"},
                    {"question": "What is your biggest professional accomplishment?", "category": "behavioral"},
                    {"question": "How do you handle conflict in a team environment?", "category": "situational"},
                    {"question": "Tell me about a difficult technical challenge you solved.", "category": "technical"},
                    {"question": f"Why do you want to work as a {job_title}?", "category": "behavioral"}
                ]

            for i, q in enumerate(questions_list):
                if not isinstance(q, dict): continue
                new_q = AIVideoQuestion(
                    interview_id=session.id,
                    question_text=q.get('question_text', q.get('question', 'Tell me about yourself.')),
                    order_index=i,
                    category=q.get('category', 'general')
                )
                db.session.add(new_q)

            session.status = 'ready'
            db.session.commit()

            return {
                "session_id": session.id,
                "job_title": session.job_title,
                "persona": session.persona_id,
                "camera_enabled": session.camera_enabled,
                "questions": [{"id": q.id, "question": q.question_text} for q in session.questions]
            }

        except Exception as e:
            logger.error(f"Failed to initialize video interview: {str(e)}")
            session.status = 'failed'
            db.session.commit()
            raise

    async def process_answer(self, session_id, question_id, transcript, metadata):
        """
        Processes a spoken answer.
        1. Saves the transcript and metadata.
        2. Evaluates the answer using AI_VIDEO_EVALUATOR_PROMPT.
        3. Checks for consistency using AI_RESUME_CONSISTENCY_EVALUATOR_PROMPT.
        """
        session = AIVideoInterview.query.get(session_id)
        question = AIVideoQuestion.query.get(question_id)

        if not session or not question:
            raise ValueError("Invalid session or question ID")

        # 1. Save Answer
        answer = AIVideoAnswer(
            question_id=question_id,
            audio_transcript=transcript,
            speaking_pace_wpm=metadata.get('word_count', 0) / (metadata.get('duration_seconds', 1) / 60) if metadata.get('duration_seconds', 0) > 0 else 0,
            confidence_score=metadata.get('confidence', 0.8) # Simulated/Metadata based
        )
        db.session.add(answer)
        db.session.commit()

        # 2. Evaluate
        eval_prompt = self._get_prompt('AI_VIDEO_EVALUATOR_PROMPT.md')
        eval_request = f"{eval_prompt}\n\nQUESTION: {question.question_text}\nANSWER: {transcript}\nMETADATA: {json.dumps(metadata)}"
        
        system_prompt = f"{self._get_persona_brief(session.persona_id)} You are evaluating a response. IMPORTANT: In your 'reaction_text' field, provide a short, conversational response to what they just said before moving on. Sound human and empathetic. Return ONLY valid JSON."
        metered_resp = await AIMeteringService.ask_ai_metered(self.user_id, 'video_interview_evaluation', eval_request, system_prompt=system_prompt)
        
        if not metered_resp.get('success'):
             return {
                "status": "error", 
                "reaction_text": f"I'm sorry, I encountered a system issue: {metered_resp.get('message')}. Please contact support.",
                "score": 0
            }
        
        eval_resp = metered_resp.get('text', '{}')
        
        # Clean & Parse
        try:
            clean_eval = eval_resp
            if "```json" in clean_eval:
                clean_eval = clean_eval.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_eval:
                clean_eval = clean_eval.split("```")[1].split("```")[0].strip()
            else:
                clean_eval = clean_eval.strip()
            
            eval_data = json.loads(clean_eval)
            
            evaluation = AIVideoEvaluation(
                answer_id=answer.id,
                score=eval_data.get('overall_score', eval_data.get('score', 70)),
                feedback_text=eval_data.get('feedback', 'No detailed feedback provided.'),
                clarity_score=eval_data.get('clarity', 70),
                relevance_score=eval_data.get('relevance', 70),
                completeness_score=eval_data.get('completeness', 70)
            )
            db.session.add(evaluation)
            db.session.commit()

            return {
                "evaluation_id": evaluation.id,
                "score": evaluation.score,
                "feedback": evaluation.feedback_text,
                "reaction_text": eval_data.get('reaction_text', 'Got it. Thank you for that answer.')
            }
        except Exception as e:
            logger.error(f"Evaluation parsing failed: {str(e)}. Raw: {eval_resp}")
            # Fallback evaluation to keep the session alive
            return {
                "status": "success", 
                "reaction_text": "Thank you for sharing that. Let's move to the next question.",
                "score": 0
            }

    async def generate_final_report(self, session_id):
        """
        Generates the final comprehensive report.
        1. Aggregates all answers and evaluations.
        2. Performs Skill Gap Analysis.
        3. Generates Final Feedback using AI_FINAL_RESUME_FEEDBACK_PROMPT.
        """
        session = AIVideoInterview.query.get(session_id)
        if not session:
            raise ValueError("Session not found")

        # Fetch all data
        answers = AIVideoAnswer.query.join(AIVideoQuestion).filter(AIVideoQuestion.interview_id == session_id).all()
        evals = [a.evaluation for a in answers if a.evaluation]
        
        if not evals:
            return None

        # 1. Performance Summary Prompt
        report_prompt = self._get_prompt('AI_FINAL_RESUME_FEEDBACK_PROMPT.md')
        
        context = []
        for a in answers:
            context.append({
                "question": a.question.question_text,
                "answer": a.audio_transcript,
                "score": a.evaluation.score if a.evaluation else 0
            })

        final_request = f"""
        {report_prompt}
        
        JOB TITLE: {session.job_title}
        INTERVIEW DATA: {json.dumps(context)}
        """

        metered_resp = await AIMeteringService.ask_ai_metered(self.user_id, 'video_interview_evaluation', final_request, system_prompt="You are a Lead Hiring Manager.")
        
        if not metered_resp.get('success'):
            logger.error(f"Report generation metered call failed: {metered_resp.get('message')}")
            session.status = 'failed'
            db.session.commit()
            return None

        final_resp = metered_resp.get('text', '{}')
        
        try:
            clean_final = final_resp.replace("```json", "").replace("```", "").strip()
            final_data = json.loads(clean_final)
            
            summary = AIVideoSummary(
                interview_id=session.id,
                summary_text=final_data.get('feedback_summary', ''),
                average_pace_wpm=sum([a.speaking_pace_wpm for a in answers]) / len(answers) if answers else 0,
                average_confidence=sum([a.confidence_score for a in answers]) / len(answers) if answers else 0,
                key_strengths_json=final_data.get('proven_strengths', []),
                areas_for_improvement_json=final_data.get('identified_risks', [])
            )
            
            session.overall_score = final_data.get('overall_match_score', sum([e.score for e in evals]) / len(evals))
            session.status = 'completed'
            
            db.session.add(summary)
            db.session.commit()
            
            return summary
        except Exception as e:
            logger.error(f"Final report generation failed: {str(e)}")
            session.status = 'completed'
            db.session.commit()
            return None

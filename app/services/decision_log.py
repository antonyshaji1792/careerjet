import logging
from app.models.decision_log import ResumeDecisionLog
from app.extensions import db

logger = logging.getLogger(__name__)

class ResumeDecisionLogService:
    """
    Service for recording and retrieving AI decision logs (Explainability).
    """

    @staticmethod
    def log_decision(resume_id, action_type, summary, rationale):
        """
        Records a decision log for a specific resume.
        """
        try:
            log = ResumeDecisionLog(
                resume_id=resume_id,
                action_type=action_type,
                decision_summary=summary,
                rationale=rationale
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            logger.error(f"Failed to record decision log for resume {resume_id}: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def get_logs(resume_id):
        """
        Retrieves all decision logs for a resume, newest first.
        """
        return ResumeDecisionLog.query.filter_by(resume_id=resume_id).order_by(ResumeDecisionLog.timestamp.desc()).all()

    @staticmethod
    def log_optimization_results(resume_id, results):
        """
        Helper to log multiple decisions from an optimization result.
        """
        # Log Score Change
        score = results.get('ats_score')
        if score:
            ResumeDecisionLogService.log_decision(
                resume_id, 
                'score_change',
                f"ATS Score: {score}/100",
                "Calculated based on keyword density and achievement impact matching the job description."
            )

        # Log Missing Keywords (Why they were identified)
        keywords = results.get('missing_keywords', [])
        if keywords:
            ResumeDecisionLogService.log_decision(
                resume_id,
                'skill_gap',
                f"Identified {len(keywords)} missing skills",
                f"Missing keywords prioritized based on job description frequency: {', '.join(keywords[:5])}..."
            )
            
        # Log Suggestions
        suggestions = results.get('suggestions', [])
        for sug in suggestions[:2]: # Log top 2 suggestions as decisions
            ResumeDecisionLogService.log_decision(
                resume_id,
                'optimization_suggestion',
                "AI Optimization Suggestion",
                sug
            )

import json
import logging
from app.services.resume_ai import ResumeAIService
from app.services.resume_validator import ResumeValidatorService
from app.services.resume_optimizer import ResumeOptimizerService
from app.resumes.parser import ResumeParser
from app.services.matching import MatchingEngine
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.models.user import UserProfile
from app.models.jobs import JobPost
from app.resumes.generator import ResumeGenerator
import os
from app.extensions import db

logger = logging.getLogger(__name__)

class ResumeService:
    """
    Main orchestration service for Resume management, generation, and job-specific optimization.
    Ensures transaction safety and strict integrity via Antigravity Guards.
    """
    
    OPTIMIZATION_THRESHOLD = 60 # Minimum match score to trigger AI optimization

    def __init__(self, user_id):
        self.user_id = user_id
        self.ai = ResumeAIService(user_id)
        self.validator = ResumeValidatorService()
        self.parser = ResumeParser()
        self.generator = ResumeGenerator()

    async def optimize_resume_for_job(self, resume_id, job_id):
        """
        Full flow: Parse -> Score -> (Threshold Filter) -> Optimize -> Validate -> Save Version.
        """
        # 1. Fetch Resources
        resume = Resume.query.filter_by(id=resume_id, user_id=self.user_id).first()
        job = db.session.get(JobPost, job_id)
        profile = UserProfile.query.filter_by(user_id=self.user_id).first()

        if not resume or not job or not profile:
            return None, "Required resources (resume, job, or profile) not found."

        try:
            # 2. Parse / Extract Base Content
            if resume.content_json:
                base_content = json.loads(resume.content_json)
            elif resume.file_path:
                # Extract and structure via AI if only file exists
                base_content = await self.parser.to_structured_json(resume.file_path, self.user_id)
                if not base_content:
                    return None, "Failed to parse resume file into structured data."
            else:
                return None, "Resume has no content or file path."

            # 3. Score against Job
            matching_engine = MatchingEngine(profile)
            match_score = matching_engine.calculate_score(job)
            logger.info(f"Resume {resume_id} scores {match_score} against job {job_id}")

            # 4. Threshold Check
            if match_score < self.OPTIMIZATION_THRESHOLD:
                return {
                    "status": "skipped",
                    "reason": f"Match score {match_score} is below threshold {self.OPTIMIZATION_THRESHOLD}.",
                    "score": match_score
                }, "Optimization skipped due to low match score."

            # 5. AI Optimization
            optimization_prompt = f"""
            Optimize the following resume for this job description.
            Focus on keyword alignment and impact while maintaining 100% factual accuracy.
            
            JOB TITLE: {job.title}
            JOB DESCRIPTION: {job.description}
            
            RESUME JSON: {json.dumps(base_content)}
            """
            
            optimized_json = await self.ai.generate_response(
                prompt=optimization_prompt,
                cache_key_data={"resume_id": resume_id, "job_id": job_id},
                schema_check=["header", "summary", "skills", "experience"]
            )

            if not optimized_json:
                return None, "AI Optimization failed."

            # 6. Antigravity Guard Validation
            is_valid, message = self.validator.validate_all(optimized_json, original_profile=base_content)
            if not is_valid:
                return None, f"Guard Violation: {message}"

            # 7. Save Version (Atomic Transaction)
            try:
                # Calculate version number
                last_version = ResumeVersion.query.filter_by(resume_id=resume_id).order_by(ResumeVersion.version_number.desc()).first()
                new_version_num = (last_version.version_number + 1) if last_version else 1
                
                version = ResumeVersion(
                    resume_id=resume_id,
                    job_id=job_id,
                    version_number=new_version_num,
                    content_json=json.dumps(optimized_json),
                    ats_score=int(match_score), # Using matching engine score as baseline
                    change_log=f"AI Optimized for {job.company} - {job.title}"
                )
                db.session.add(version)
                db.session.commit()
                
                # 8. Render to PDF automatically
                try:
                    filename = f"resume_v{new_version_num}_job{job_id}.pdf"
                    output_dir = os.path.join('uploads', 'resumes', str(self.user_id))
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, filename)
                    
                    if self.generator.export_pdf(optimized_json, output_path):
                        version.file_path = output_path
                        db.session.commit()
                        logger.info(f"Rendered optimized resume to {output_path}")
                except Exception as render_err:
                    logger.warning(f"Failed to render optimized resume PDF: {str(render_err)}")

                return {
                    "status": "success",
                    "version_id": version.id,
                    "version_number": version.version_number,
                    "match_score": match_score,
                    "metadata": version.to_dict()
                }, "Resume optimized and version saved."
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to save resume version: {str(e)}")
                return None, "Database error during version save."

        except Exception as e:
            logger.error(f"Error in optimization flow: {str(e)}")
            return None, f"Optimization flow failed: {str(e)}"

    async def create_base_resume(self, profile_data, target_role, tone="professional"):
        """
        Generates a master base resume from user profile.
        """
        prompt = f"Create a comprehensive master resume for a {target_role} role. Tone: {tone}. Data: {json.dumps(profile_data)}"
        
        resume_data = await self.ai.generate_response(
            prompt=prompt,
            schema_check=["header", "summary", "skills", "experience", "education"]
        )
        
        if not resume_data:
            return None, "AI Generation failed."
            
        try:
            new_resume = Resume(
                user_id=self.user_id,
                title=f"Master Resume - {target_role}",
                content_json=json.dumps(resume_data),
                is_generated=True,
                is_primary=True # Default to primary if it's the first or master
            )
            db.session.add(new_resume)
            db.session.commit()
            return new_resume, "Master resume created successfully."
        except Exception as e:
            db.session.rollback()
            return None, f"Failed to save master resume: {str(e)}"
    async def get_best_resume_for_job(self, job_id):
        """
        Returns the most relevant resume file path for a job.
        Priority: Optimized Version > Primary Resume > Latest Upload.
        """
        # 1. Try to find an optimized version for this job
        version = ResumeVersion.query.filter_by(job_id=job_id).order_by(ResumeVersion.created_at.desc()).first()
        if version and version.file_path and os.path.exists(version.file_path):
            return version.file_path, "optimized"

        # 2. Fallback to primary resume
        primary = Resume.query.filter_by(user_id=self.user_id, is_primary=True).first()
        if primary and primary.file_path and os.path.exists(primary.file_path):
            return primary.file_path, "primary"

        # 3. Fallback to latest resume
        latest = Resume.query.filter_by(user_id=self.user_id).order_by(Resume.created_at.desc()).first()
        if latest and latest.file_path and os.path.exists(latest.file_path):
            return latest.file_path, "latest"

        return None, "none"

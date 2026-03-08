import time
from playwright.sync_api import sync_playwright
from app.models import Application, JobPost, User
from app import db
from datetime import datetime

class AutoApplyService:
    def __init__(self, user_id):
        self.user = User.query.get(user_id)
        self.profile = self.user.profile

    def apply_to_job(self, job_id):
        job = JobPost.query.get(job_id)
        if not job:
            return False, "Job not found"

        # Check if already applied
        existing = Application.query.filter_by(user_id=self.user.id, job_id=job.id).first()
        if existing and existing.status == 'Applied':
            return False, "Already applied"

        # Mocking Playwright Application
        # In a real scenario, this would use Playwright to login and apply
        try:
            print(f"Applying to {job.title} at {job.company} for user {self.user.email}...")
            time.sleep(2) # Simulating browser action
            
            # Logic would vary by platform
            status = 'Applied'
            
            application = Application(
                user_id=self.user.id,
                job_id=job.id,
                status=status,
                applied_at=datetime.utcnow()
            )
            db.session.add(application)
            db.session.commit()
            return True, "Applied successfully"
        except Exception as e:
            application = Application(
                user_id=self.user.id,
                job_id=job.id,
                status='Failed',
                error_message=str(e)
            )
            db.session.add(application)
            db.session.commit()
            return False, str(e)

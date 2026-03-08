from playwright.sync_api import sync_playwright
from app.models import JobPost
from app import db
from datetime import datetime

class JobIngestionService:
    def __init__(self):
        self.platforms = {
            'linkedin': self.scrape_linkedin,
            'naukri': self.scrape_naukri
        }

    def scrape_linkedin(self, query):
        # Mocked scraping logic for LinkedIn
        # In production, this would use Playwright to navigate and extract
        jobs = [
            {'title': 'Senior Python Developer', 'company': 'Tech Corp', 'location': 'Remote', 'platform': 'LinkedIn', 'job_url': 'https://linkedin.com/jobs/1', 'description': 'Python, Flask, AWS experience required.'},
            {'title': 'Backend Engineer', 'company': 'Data Inc', 'location': 'New York', 'platform': 'LinkedIn', 'job_url': 'https://linkedin.com/jobs/2', 'description': 'SQL, Python, Celery.'}
        ]
        return jobs

    def scrape_naukri(self, query):
        # Mocked scraping logic for Naukri
        jobs = [
            {'title': 'Full Stack Developer', 'company': 'Web Solutions', 'location': 'Hybrid', 'platform': 'Naukri', 'job_url': 'https://naukri.com/jobs/1', 'description': 'JavaScript, Python, React.'}
        ]
        return jobs

    def ingest_jobs(self, query):
        all_jobs = []
        for platform, scraper in self.platforms.items():
            try:
                platform_jobs = scraper(query)
                all_jobs.extend(platform_jobs)
            except Exception as e:
                print(f"Error scraping {platform}: {e}")

        for job_data in all_jobs:
            existing = JobPost.query.filter_by(job_url=job_data['job_url']).first()
            if not existing:
                job = JobPost(**job_data, posted_at=datetime.utcnow())
                db.session.add(job)
        
        db.session.commit()
        return len(all_jobs)

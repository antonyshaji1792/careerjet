
import asyncio
import logging
from app.services.base_scraper import BaseScraper
from app.models import JobPost
from app import db

logger = logging.getLogger(__name__)

class IndeedScraper(BaseScraper):
    async def login(self, email, password):
        """Indeed login implementation"""
        try:
            logger.info(f"Logging into Indeed with {email}")
            await self.page.goto("https://secure.indeed.com/account/login", wait_until="networkidle")
            
            # Use selectors for Indeed login
            await self.page.fill('input[name="login_email"]', email)
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(2)
            
            # If prompted for password
            await self.page.fill('input[name="login_password"]', password)
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(5)
            
            # Check for success (e.g., presence of profile icon or redirect)
            return "indeed" in self.page.url.lower()
        except Exception as e:
            logger.error(f"Indeed login error: {str(e)}")
            return False

    async def search_jobs(self, keywords, location=None, limit=10, **kwargs):
        """Indeed job search implementation"""
        jobs_found = []
        try:
            search_url = f"https://www.indeed.com/jobs?q={keywords}&l={location or ''}"
            await self.page.goto(search_url, wait_until="networkidle")
            
            # Extract job details
            job_cards = await self.page.query_selector_all('.job_seen_beacon')
            for card in job_cards[:limit]:
                title_elem = await card.query_selector('h2.jobTitle span[title]')
                company_elem = await card.query_selector('.companyName')
                location_elem = await card.query_selector('.companyLocation')
                link_elem = await card.query_selector('a.jcs-JobTitle')
                
                if title_elem and link_elem:
                    job_url = await link_elem.get_attribute('href')
                    if job_url.startswith('/'):
                        job_url = "https://www.indeed.com" + job_url
                        
                    jobs_found.append({
                        'title': await title_elem.inner_text(),
                        'company': await company_elem.inner_text() if company_elem else "Unknown",
                        'location': await location_elem.inner_text() if location_elem else "Remote",
                        'job_url': job_url,
                        'platform': 'indeed'
                    })
            return jobs_found
        except Exception as e:
            logger.error(f"Indeed search error: {str(e)}")
            return []

    def save_jobs_to_db(self, jobs):
        """Helper to save indeed jobs to JobPost table"""
        saved = 0
        for job_data in jobs:
            existing = JobPost.query.filter_by(job_url=job_data['job_url']).first()
            if not existing:
                job = JobPost(
                    title=job_data['title'],
                    company=job_data['company'],
                    location=job_data['location'],
                    platform=job_data['platform'],
                    job_url=job_data['job_url']
                )
                db.session.add(job)
                saved += 1
        db.session.commit()
        return saved

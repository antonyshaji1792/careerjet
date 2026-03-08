"""
LinkedIn Scraper Service

This module handles scraping job postings from LinkedIn using Playwright.
It can extract job details, detect Easy Apply jobs, and store them in the database.
"""

import asyncio
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
from app.models import LinkedInJob, LinkedInCredentials, JobPost
from app import db
import logging

logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Scrape LinkedIn job postings"""
    
    def __init__(self, headless=False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self):
        """Initialize browser and page"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = await self.context.new_page()
        logger.info("LinkedIn scraper initialized")
    
    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
            logger.info("LinkedIn scraper closed")
    
    async def get_cookies(self):
        """Get current session cookies"""
        if self.context:
            return await self.context.cookies()
        return []
    
    async def set_cookies(self, cookies):
        """Set session cookies"""
        if self.context and cookies:
            await self.context.add_cookies(cookies)
            logger.info(f"Loaded {len(cookies)} cookies into session")
    
    async def login(self, email, password):
        """
        Login to LinkedIn with robust error handling and 'already logged in' check
        """
        try:
            logger.info(f"Attempting to login to LinkedIn with email: {email}")
            
            # Check if we are already logged in (maybe cookies were loaded)
            await self.page.goto('https://www.linkedin.com/', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            if await self._is_logged_in():
                logger.info("Already logged in to LinkedIn")
                return True
            
            # Navigate to LinkedIn login page
            await self.page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Double check if we were redirected to feed (already logged in)
            if await self._is_logged_in():
                logger.info("Already logged in to LinkedIn (redirected from login page)")
                return True
            
            # Wait for login form
            try:
                await self.page.wait_for_selector('input[name="session_key"]', timeout=5000)
            except:
                # If still not found, check one last time if logged in
                if await self._is_logged_in():
                    return True
                logger.error("LinkedIn login form not found and not logged in")
                return False
            
            # Fill login form
            await self.page.fill('input[name="session_key"]', email)
            await self.page.fill('input[name="session_password"]', password)
            
            # Click login button
            await self.page.click('button[type="submit"]')
            
            # Wait for navigation or check for verification
            # Increase wait time for potential slow redirects or checkpoints
            await asyncio.sleep(5)
            
            # Check for success
            if await self._is_logged_in():
                logger.info("LinkedIn login successful")
                return True
            
            # Check for specific failure cases
            current_url = self.page.url
            if 'checkpoint' in current_url:
                logger.warning("LinkedIn login: Security checkpoint encountered. Manual intervention may be required.")
                # We return True here because we are technically "at" a login stage that isn't a "failed credentials" error
                # and maybe the user can solve it if headless=False
                return True
                
            logger.error(f"LinkedIn login failed - current URL: {current_url}")
            return False
                
        except Exception as e:
            logger.error(f"LinkedIn login error: {str(e)}")
            return False
            
    async def _is_logged_in(self):
        """Check if currently logged in to LinkedIn"""
        try:
            # Check URL first
            current_url = self.page.url
            if any(x in current_url for x in ['feed', 'mynetwork', 'messaging', 'notifications', 'jobs']):
                return True
                
            # Check for common logged-in elements
            logged_in_selectors = [
                '.global-nav__me-photo',
                '#global-nav-typeahead',
                '.feed-identity-module',
                'button.global-nav__primary-link[data-test-global-nav-link="jobs"]'
            ]
            
            for selector in logged_in_selectors:
                if await self.page.query_selector(selector):
                    return True
                    
            return False
        except:
            return False
    
    async def search_jobs(self, keywords, location='', easy_apply_only=True, limit=25):
        """
        Search for jobs on LinkedIn with robust selectors
        """
        try:
            logger.info(f"Searching LinkedIn jobs: {keywords} in {location}")
            
            # Build search URL
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}"
            if location:
                search_url += f"&location={location}"
            if easy_apply_only:
                search_url += "&f_AL=true"  # Easy Apply filter
            
            # Navigate to search results
            await self.page.goto(search_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)  # Wait for dynamic content
            
            # Try multiple job card selectors
            card_selectors = [
                '.job-card-container',
                'li.jobs-search-results__list-item',
                '.jobs-search-results-list__item',
                'div[data-job-id]',
                '.base-card'
            ]
            
            job_cards = []
            for selector in card_selectors:
                job_cards = await self.page.query_selector_all(selector)
                if job_cards:
                    logger.info(f"Using selector '{selector}', found {len(job_cards)} job cards")
                    break
            
            if not job_cards:
                logger.warning("No job cards found with any selector")
                return []
            
            jobs = []
            for i, card in enumerate(job_cards[:limit]):
                try:
                    # Click on job card to load details
                    await card.click()
                    await asyncio.sleep(1.5)  # Wait for details to load
                    
                    # Extract job data
                    job_data = await self._extract_job_details(card)
                    if job_data:
                        jobs.append(job_data)
                        logger.info(f"Scraped job {i+1}: {job_data['title']} at {job_data['company']}")
                    
                except Exception as e:
                    logger.error(f"Error scraping job card {i}: {str(e)}")
                    continue
            
            logger.info(f"Successfully scraped {len(jobs)} jobs")
            return jobs
            
        except Exception as e:
            logger.error(f"Job search error: {str(e)}")
            return []
    
    async def _extract_job_details(self, card=None):
        """
        Extract job details with robust/fallback selectors
        """
        try:
            # Wait for detail pane to be visible
            details_pane_selectors = [
                '.jobs-search__job-details--wrapper',
                '.job-details',
                '.jobs-details__main-content',
                '#main'
            ]
            
            details_visible = False
            for selector in details_pane_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    details_visible = True
                    break
                except:
                    continue
            
            if not details_visible:
                logger.warning("Job details pane not visible")
                return None
            
            # Get page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract job ID from URL
            job_url = self.page.url
            job_id_match = re.search(r'(/jobs/view/|currentJobId=)(\d+)', job_url)
            linkedin_job_id = job_id_match.group(2) if job_id_match else None
            
            if not linkedin_job_id:
                # Try getting from data-job-id attribute in the DOM
                id_elem = soup.select_one('[data-job-id]')
                linkedin_job_id = id_elem.get('data-job-id') if id_elem else None
                
            if not linkedin_job_id:
                return None
            
            # Extract job title
            title_selectors = [
                'h1.t-24.t-bold.jobs-unified-top-card__job-title',
                '.job-details-jobs-unified-top-card__job-title',
                '.jobs-unified-top-card__job-title',
                '.jobs-details-top-card__job-title',
                'h2.job-details-jobs-unified-top-card__job-title',
                'h1.job-title',
                '.job-title',
                'h1.t-24',
                'h2.t-24',
                '.t-24',
                '.display-flex.t-24.t-bold',
                'div.jobs-details__main-content h2',
                '.jobs-details-cap-v2-header__title'
            ]
            title = "Unknown"
            
            # Try detail pane selectors first
            for selector in title_selectors:
                elem = soup.select_one(selector)
                if elem:
                    title = elem.get_text().strip()
                    if title: break
            
            # Fallback 1: Try any H1 in the details pane
            if title == "Unknown":
                details_elem = soup.select_one('.jobs-details__main-content, #main, .jobs-search__job-details--container')
                if details_elem:
                    h1 = details_elem.find('h1')
                    if h1:
                        title = h1.get_text().strip()

            # Fallback 2: Try extracting from the card itself if provided
            if title == "Unknown" and card:
                try:
                    title_elem = await card.query_selector('.job-card-list__title--link, .job-card-container__link, [class*="job-title"]')
                    if not title_elem:
                        # Even deeper search in card
                        title_elem = await card.query_selector('button[class*="job-title"], a[class*="job-title"]')
                        
                    if title_elem:
                        title = await title_elem.inner_text()
                        title = title.strip()
                except:
                    pass
            
            if title == "Unknown":
                logger.warning(f"Could not extract title for job {linkedin_job_id} at {job_url}")
            
            # Extract company
            company_selectors = [
                '.job-details-jobs-unified-top-card__company-name',
                '.jobs-unified-top-card__company-name',
                '.topcard__org-name-link',
                '.jobs-details-top-card__company-url',
                '.jobs-details-top-card__company-name',
                '.artdeco-entity-lockup__subtitle',
                '.jobs-unified-top-card__primary-description a[href*="/company/"]'
            ]
            company = "Unknown"
            for selector in company_selectors:
                elem = soup.select_one(selector)
                if elem:
                    company = elem.get_text().strip()
                    if company: break
            
            # Fallback for company from card
            if company == "Unknown" and card:
                try:
                    company_elem = await card.query_selector('.job-card-container__primary-description, .job-card-container__company-name, [class*="company-name"]')
                    if company_elem:
                        company = await company_elem.inner_text()
                        company = company.strip()
                except:
                    pass
                    
            location_selectors = [
                '.job-details-jobs-unified-top-card__primary-description span:nth-child(2)',
                '.job-details-jobs-unified-top-card__bullet',
                '.jobs-unified-top-card__bullet',
                '.topcard__flavor--bullet',
                '.jobs-details-top-card__bullet',
                '.jobs-unified-top-card__primary-description span:last-child',
                '.jobs-unified-top-card__primary-description'
            ]
            location = "Unknown"
            for selector in location_selectors:
                elem = soup.select_one(selector)
                if elem:
                    location = elem.get_text().strip()
                    # Clean up if it contains bullets or extra info
                    location = location.replace('·', '').replace('\n', ' ').strip()
                    if location and len(location) < 100: # Filter out long descriptions mistakenly caught
                        break
            
            # Fallback for location from card
            if (not location or location == "Unknown") and card:
                try:
                    loc_elem = await card.query_selector('.job-card-container__metadata-item--location, .job-card-container__location, [class*="location"]')
                    if loc_elem:
                        location = await loc_elem.inner_text()
                        location = location.strip()
                except:
                    pass
            
            # Extract description
            description_selectors = [
                '.jobs-description__content',
                '#job-details',
                '.jobs-box__html-content',
                '.description__text'
            ]
            description = ""
            for selector in description_selectors:
                elem = soup.select_one(selector)
                if elem:
                    description = elem.get_text().strip()
                    break
            
            # Check for Easy Apply button
            apply_selectors = [
                'button.jobs-apply-button',
                '.jobs-apply-button--top-card',
                '.jobs-s-apply'
            ]
            is_easy_apply = False
            for selector in apply_selectors:
                btn = soup.select_one(selector)
                if btn and 'Easy Apply' in btn.get_text():
                    is_easy_apply = True
                    break
            
            # Extract employment type and seniority
            insight_selectors = [
                '.job-details-jobs-unified-top-card__job-insight',
                '.jobs-unified-top-card__job-insight',
                '.jobs-description-details__list-item'
            ]
            criteria_items = []
            for selector in insight_selectors:
                criteria_items = soup.select(selector)
                if criteria_items:
                    break
            
            employment_type = None
            seniority_level = None
            
            for item in criteria_items:
                text = item.get_text().strip()
                if any(x in text for x in ['Full-time', 'Part-time', 'Contract', 'Temporary']):
                    employment_type = text
                elif any(x in text for x in ['Entry', 'Mid-Senior', 'Director', 'Executive', 'Internship']):
                    seniority_level = text
            
            job_data = {
                'linkedin_job_id': linkedin_job_id,
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'job_url': job_url,
                'is_easy_apply': is_easy_apply,
                'employment_type': employment_type,
                'seniority_level': seniority_level,
                'posted_at': datetime.utcnow(),
                'scraped_at': datetime.utcnow()
            }
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error extracting job details: {str(e)}")
            return None
    
    def save_jobs_to_db(self, jobs):
        """
        Save scraped jobs to database
        
        Args:
            jobs (list): List of job dictionaries
            
        Returns:
            int: Number of jobs saved
        """
        saved_count = 0
        
        for job_data in jobs:
            try:
                # Check if job already exists
                existing_job = LinkedInJob.query.filter_by(
                    linkedin_job_id=job_data['linkedin_job_id']
                ).first()
                
                if existing_job:
                    # Update existing job
                    job_data['is_active'] = True
                    for key, value in job_data.items():
                        setattr(existing_job, key, value)
                    logger.info(f"Updated existing job: {job_data['linkedin_job_id']}")
                else:
                    # Create new job
                    job_data['is_active'] = True
                    new_job = LinkedInJob(**job_data)
                    db.session.add(new_job)
                    saved_count += 1
                    logger.info(f"Saved new job: {job_data['linkedin_job_id']}")
                
                # Also save to general JobPost table
                self._save_to_job_post(job_data)
                
            except Exception as e:
                logger.error(f"Error saving job {job_data.get('linkedin_job_id')}: {str(e)}")
                continue
        
        try:
            db.session.commit()
            logger.info(f"Saved {saved_count} new jobs to database")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database commit error: {str(e)}")
            saved_count = 0
        
        return saved_count
    
    def _save_to_job_post(self, job_data):
        """Save LinkedIn job to general JobPost table"""
        try:
            # Check if already exists
            existing = JobPost.query.filter_by(job_url=job_data['job_url']).first()
            
            if not existing:
                job_post = JobPost(
                    title=job_data['title'],
                    company=job_data['company'],
                    location=job_data['location'],
                    platform='LinkedIn',
                    job_url=job_data['job_url'],
                    description=job_data['description'],
                    posted_at=job_data.get('posted_at'),
                    ingested_at=datetime.utcnow()
                )
                db.session.add(job_post)
                logger.info(f"Added job to JobPost table: {job_data['title']}")
        except Exception as e:
            logger.error(f"Error saving to JobPost: {str(e)}")


async def scrape_linkedin_jobs(user_id, keywords, location='', limit=25):
    """
    Main function to scrape LinkedIn jobs for a user
    
    Args:
        user_id (int): User ID
        keywords (str): Job search keywords
        location (str): Location filter
        limit (int): Maximum number of jobs
        
    Returns:
        dict: Results with job count and status
    """
    try:
        # Get user's LinkedIn credentials
        credentials = LinkedInCredentials.query.filter_by(
            user_id=user_id,
            is_active=True
        ).first()
        
        if not credentials:
            return {
                'success': False,
                'message': 'LinkedIn credentials not found. Please add your LinkedIn account.',
                'jobs_scraped': 0
            }
        
        # Initialize scraper
        async with LinkedInScraper(headless=False) as scraper:
            # Load cookies if available
            import json
            if credentials.session_cookies:
                try:
                    cookies = json.loads(credentials.session_cookies)
                    await scraper.set_cookies(cookies)
                except Exception as e:
                    logger.error(f"Error loading cookies: {str(e)}")
            
            # Login to LinkedIn
            email = credentials.email
            password = credentials.get_password()
            
            login_success = await scraper.login(email, password)
            
            if not login_success:
                return {
                    'success': False,
                    'message': 'LinkedIn login failed. Please check your credentials.',
                    'jobs_scraped': 0
                }
            
            # Save cookies after successful login
            try:
                new_cookies = await scraper.get_cookies()
                credentials.session_cookies = json.dumps(new_cookies)
                credentials.last_login = datetime.utcnow()
                db.session.commit()
            except Exception as e:
                logger.error(f"Error saving cookies: {str(e)}")
                db.session.rollback()
            
            # Search for jobs
            jobs = await scraper.search_jobs(
                keywords=keywords,
                location=location,
                easy_apply_only=True,
                limit=limit
            )
            
            # Save jobs to database
            new_count = scraper.save_jobs_to_db(jobs)
            total_found = len(jobs)
            
            if total_found == 0:
                return {
                    'success': True,
                    'message': f'No new jobs found matching "{keywords}" in "{location}". Try broadening your search or checking your LinkedIn account manually.',
                    'jobs_scraped': 0
                }
            
            return {
                'success': True,
                'message': f'Scraping complete! Found {total_found} jobs ({new_count} new, {total_found - new_count} updated).',
                'jobs_scraped': new_count,
                'jobs': jobs
            }
            
    except Exception as e:
        logger.error(f"LinkedIn scraping error: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'jobs_scraped': 0
        }

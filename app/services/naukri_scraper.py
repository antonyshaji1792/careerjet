import asyncio
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright
from app import db
from app.models import NaukriJob, NaukriCredentials, JobPost

logger = logging.getLogger(__name__)

class NaukriScraper:
    def __init__(self, headless=False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.webkit.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
            ]
        )
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
            java_script_enabled=True
        )
        self.page = await self.context.new_page()
        
        # Enhanced stealth: mask automation signatures
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({ query: (q) => Promise.resolve({ state: 'granted' }) })
            });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(navigator, 'appVersion', { get: () => '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36' });
            Object.defineProperty(navigator, 'productSub', { get: () => '20030107' });
        """)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def _check_login_success(self, timeout=5000):
        """Check if currently logged in using various indicators"""
        success_selectors = [
            ".nLogo", 
            "a.nI-gNb-header__logo", 
            ".nI-gNb-drawer", 
            "a[title='Logout']",
            ".nI-gNb-user-img"
        ]
        for sel in success_selectors:
            try:
                if await self.page.is_visible(sel) or await self.page.query_selector(sel):
                    return True
            except:
                continue
        return False

    async def login(self, email, password):
        """Login to Naukri.com"""
        try:
            logger.info(f"Attempting to login to Naukri with {email}")
            await self.page.goto("https://www.naukri.com/nlogin/login", wait_until="networkidle", timeout=60000, referer="https://www.naukri.com/")
            
            # Check if we are already logged in (redirected to home)
            if await self._check_login_success():
                logger.info("Already logged into Naukri")
                return True

            try:
                await self.page.wait_for_selector("#usernameField", timeout=10000)
                await self.page.fill("#usernameField", email)
                await self.page.fill("#passwordField", password)
                await self.page.click("button.blue-btn")
            except Exception as e:
                # Maybe already redirected or selectors changed
                if await self._check_login_success():
                    return True
                logger.warning(f"Login form not found or fill failed: {str(e)}")
                return False
            
            # Wait for navigation or success indicator
            try:
                # Try to wait for success
                for _ in range(10): # 10 seconds total polling
                    if await self._check_login_success():
                        logger.info("Successfully logged into Naukri")
                        return True
                    
                    # Check for error message
                    if await self.page.is_visible(".err-msg, .error-message, .error-text"):
                        err_text = await self.page.inner_text(".err-msg, .error-message, .error-text")
                        logger.error(f"Naukri login failed: {err_text}")
                        return False
                    
                    await asyncio.sleep(1)
                
                return False
            except Exception as e:
                logger.error(f"Error during login success verification: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Naukri login error: {str(e)}")
            return False

    async def search_jobs(self, keywords, location=None, limit=20, easy_apply_only=False):
        """Search and scrape jobs from Naukri"""
        try:
            # Step 1: Establish a "Safe" history by going to Google first
            logger.info("Hopping to Google to establish human-like history...")
            await self.page.goto("https://www.google.com/search?q=naukri+jobs", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # Step 2: Try Direct URL search if possible to avoid homepage block
            search_query = keywords.replace(" ", "-").lower()
            if location:
                loc_query = location.replace(" ", "-").lower()
                direct_url = f"https://www.naukri.com/{search_query}-jobs-in-{loc_query}"
            else:
                direct_url = f"https://www.naukri.com/{search_query}-jobs"
            
            logger.info(f"Trying direct search URL: {direct_url}")
            try:
                await self.page.goto(direct_url, wait_until="domcontentloaded", timeout=45000, referer="https://www.google.com/")
                await asyncio.sleep(5)
                
                content = await self.page.content()
                if "Access Denied" not in content and (await self.page.query_selector(".srp-jobtuple-wrapper, .cust-job-tuple, .job-tuple")):
                    logger.info("Direct search URL worked!")
                    # Skip UI typing and go straight to scraping
                    return await self._scrape_cards(limit)
            except Exception as e:
                logger.warning(f"Direct URL failed or blocked: {str(e)}")

            # Step 3: Fallback to homepage and UI Search (old method)
            logger.info("Falling back to homepage UI search...")
            await self.page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=60000, referer="https://www.google.com/")
            await asyncio.sleep(5)
            await self.page.screenshot(path="debug_naukri_homepage.png")
            
            # Check for Access Denied again
            content = await self.page.content()
            if "Access Denied" in content:
                logger.error("Still getting Access Denied on homepage. Scraping likely blocked.")
                return []
            
            # Clear overlays
            try: 
                if await self.page.is_visible(".crossIcon"):
                    await self.page.click(".crossIcon", timeout=2000)
                    logger.info("Closed overlay")
            except: pass

            # UI Search (Typing naturally)
            search_bar_sel = "input.suggestor-input, .search-jobs-here, [placeholder*='skills']"
            await self.page.wait_for_selector(search_bar_sel, timeout=10000)
            await self.page.click(search_bar_sel)
            await asyncio.sleep(1)
            await self.page.type(search_bar_sel, keywords, delay=100)
            logger.info(f"Typed keywords: {keywords}")
            
            if location:
                loc_sel = "input[placeholder*='location']"
                await self.page.click(loc_sel)
                await self.page.type(loc_sel, location, delay=100)
                await asyncio.sleep(2) # Wait for dropdown
                await self.page.keyboard.press("ArrowDown") # Ensure first item is highlighted
                await asyncio.sleep(0.5)
                await self.page.keyboard.press("Enter")
                logger.info(f"Typed and selected location: {location}")
            
            await self.page.screenshot(path="debug_naukri_pre_submit.png")
            await self.page.keyboard.press("Enter") # Final search trigger
            await asyncio.sleep(10) # Long wait for search redirect
            await self.page.screenshot(path="debug_naukri_post_submit.png")
            return await self._scrape_cards(limit)

        except Exception as e:
            logger.error(f"Naukri search error: {str(e)}")
            return []

    async def _scrape_cards(self, limit=20):
        """Helper to scrape job details from listing page"""
        try:
            # Check for no results
            if await self.page.is_visible(".no-result"):
                logger.info("No jobs found for this query on Naukri")
                return []

            # Scroll to trigger lazy loading
            for _ in range(3):
                await self.page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1)
            
            # Use unique selector for cards to avoid duplicates
            job_cards = await self.page.query_selector_all(".srp-jobtuple-wrapper, .cust-job-tuple, .job-tuple")
            
            if not job_cards:
                logger.warning(f"No job cards found with standard selectors. Page content length: {len(await self.page.content())}")
                await self.page.screenshot(path="naukri_zero_jobs_debug.png")
                # Try a last-ditch effort: any link containing '/job-listings-'
                job_cards = await self.page.query_selector_all("a[href*='/job-listings-']")
                if job_cards:
                    logger.info(f"Found {len(job_cards)} jobs using fallback link selector")
                
            logger.info(f"Found {len(job_cards)} job cards on Naukri")
            
            scraped_jobs = []
            seen_urls = set()
            
            for card in job_cards:
                if len(scraped_jobs) >= limit:
                    break
                    
                try:
                    # Title
                    title_elem = await card.query_selector("a.title, .title, .job-title")
                    if not title_elem: continue
                    
                    title = (await title_elem.inner_text()).strip()
                    job_url = await title_elem.get_attribute("href")
                    
                    if not job_url: continue
                    
                    # Ensure absolute URL
                    if not job_url.startswith("http"):
                        job_url = f"https://www.naukri.com{job_url}"
                    
                    # Avoid duplicates
                    clean_url = job_url.split('?')[0] # Remove query params for uniqueness check
                    if clean_url in seen_urls:
                        continue
                    seen_urls.add(clean_url)
                    
                    # Company
                    company_elem = await card.query_selector("a.comp-name")
                    company = await company_elem.get_attribute("title") or await company_elem.inner_text() if company_elem else "Unknown"
                    
                    # Experience
                    exp_elem = await card.query_selector(".exp-wrap")
                    experience = await exp_elem.inner_text() if exp_elem else "Not specified"
                    
                    # Location
                    loc_elem = await card.query_selector(".loc-wrap")
                    location_text = await loc_elem.inner_text() if loc_elem else "Multiple Locations"
                    
                    # Salary
                    sal_elem = await card.query_selector(".sal-wrap")
                    salary = await sal_elem.inner_text() if sal_elem else "Not disclosed"
                    
                    # Date Posted
                    posted_elem = await card.query_selector(".job-post-day")
                    posted_at_text = await posted_elem.inner_text() if posted_elem else "Recent"
                    
                    # Extract ID
                    naukri_job_id = None
                    if job_url:
                        import re
                        # Naukri IDs are typically 12-digit strings at the end of the URL
                        id_match = re.search(r'(\d{10,14})', job_url)
                        if id_match:
                            naukri_job_id = id_match.group(1)
                        else:
                            # Fallback: Hash the URL if no long digit string found
                            import hashlib
                            naukri_job_id = hashlib.md5(job_url.encode()).hexdigest()[:12]
                    
                    scraped_jobs.append({
                        'naukri_job_id': naukri_job_id,
                        'title': title.strip(),
                        'company': company.strip(),
                        'location': location_text.strip(),
                        'experience_required': experience.strip(),
                        'salary_range': salary.strip(),
                        'job_url': job_url,
                        'posted_at': posted_at_text.strip(),
                        'platform': 'Naukri'
                    })
                except Exception as card_err:
                    logger.error(f"Error parsing job card: {str(card_err)}")
                    continue
            
            return scraped_jobs
        except Exception as e:
            logger.error(f"Error during card scraping: {str(e)}")
            return []


    def save_jobs_to_db(self, jobs):
        """Save scraped jobs to database"""
        saved_count = 0
        for data in jobs:
            try:
                # Update cache table
                existing_cache = NaukriJob.query.filter_by(job_url=data['job_url']).first()
                if not existing_cache:
                    new_cache = NaukriJob(**data)
                    db.session.add(new_cache)
                    saved_count += 1
                
                # Update main JobPost table
                self._save_to_job_post(data)
            except Exception as e:
                logger.error(f"Error saving Naukri job {data.get('job_url')}: {str(e)}")
                continue
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Naukri DB commit error: {str(e)}")
            saved_count = 0
        return saved_count

    def _save_to_job_post(self, data):
        """Save Naukri job to general JobPost table"""
        try:
            existing = JobPost.query.filter_by(job_url=data['job_url']).first()
            if not existing:
                new_post = JobPost(
                    title=data['title'],
                    company=data['company'],
                    location=data['location'],
                    platform='Naukri',
                    job_url=data['job_url'],
                    description=f"Experience: {data.get('experience_required', 'N/A')}\nSalary: {data.get('salary_range', 'N/A')}"
                )
                db.session.add(new_post)
        except Exception as e:
            logger.error(f"Error saving to JobPost: {str(e)}")

async def scrape_naukri_jobs(user_id, keywords, location=None, limit=20):
    """Orchestrator for scraping Naukri jobs"""
    credentials = NaukriCredentials.query.filter_by(user_id=user_id, is_active=True).first()
    
    async with NaukriScraper(headless=True) as scraper:
        # Login if credentials available
        if credentials:
            await scraper.login(credentials.email, credentials.get_password())
        
        jobs_data = await scraper.search_jobs(keywords, location, limit)
        
        new_jobs_count = 0
        for data in jobs_data:
            # Update cache table
            existing_cache = NaukriJob.query.filter(
                (NaukriJob.job_url == data['job_url']) | 
                (NaukriJob.naukri_job_id == data['naukri_job_id'])
            ).first()
            if not existing_cache:
                # Filter data to only valid NaukriJob fields
                valid_fields = {k: v for k, v in data.items() if k in NaukriJob.__table__.columns.keys()}
                new_cache = NaukriJob(**valid_fields)
                db.session.add(new_cache)
                new_jobs_count += 1
            
            # Update main JobPost table
            existing_post = JobPost.query.filter_by(job_url=data['job_url']).first()
            if not existing_post:
                new_post = JobPost(
                    title=data['title'],
                    company=data['company'],
                    location=data['location'],
                    platform='Naukri',
                    job_url=data['job_url'],
                    description=f"Experience: {data['experience_required']}\nSalary: {data['salary_range']}"
                )
                db.session.add(new_post)
        
        db.session.commit()
        return {
            'success': True,
            'message': f"Successfully scraped {len(jobs_data)} jobs from Naukri. Found {new_jobs_count} new jobs.",
            'jobs_count': len(jobs_data),
            'new_jobs_count': new_jobs_count
        }

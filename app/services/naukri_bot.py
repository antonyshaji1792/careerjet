import asyncio
import logging
from playwright.async_api import async_playwright
from app import db
from app.models import NaukriCredentials, NaukriJob, JobPost, Application, UserProfile
from app.services.llm_service import ask_ai

logger = logging.getLogger(__name__)

class NaukriApplyBot:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def login(self, email, password):
        """Login to Naukri.com"""
        try:
            logger.info(f"Attempting login for {email}")
            await self.page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded")
            
            # Use the robust check from scraper
            if await self._check_login_success():
                logger.info("Already logged in to Naukri")
                return True

            await self.page.wait_for_selector("#usernameField", timeout=10000)
            await self.page.fill("#usernameField", email)
            await self.page.fill("#passwordField", password)
            await self.page.click("button.blue-btn")
            
            # Poll for success
            for _ in range(10):
                if await self._check_login_success():
                    logger.info("Login successful")
                    return True
                if await self.page.is_visible(".err-msg, .error-message"):
                    err = await self.page.inner_text(".err-msg, .error-message")
                    logger.error(f"Login error message: {err}")
                    return False
                await asyncio.sleep(1)
                
            return False
        except Exception as e:
            logger.error(f"Naukri login failed: {str(e)}")
            return False

    async def _check_login_success(self):
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

    async def apply_to_job(self, job_url, user_profile):
        """Apply to a single job on Naukri"""
        try:
            logger.info(f"Navigating to job: {job_url}")
            await self.page.goto(job_url)
            
            # Check for Apply button
            # Naukri has different apply button IDs/classes
            apply_selectors = [
                "#apply-button", 
                ".apply-button", 
                "button.apply", 
                "#login-apply-button",
                "#reg-apply-button",
                ".reg-apply-button",
                ".login-apply-button",
                "button:has-text('Apply')",
                "[class*='apply-button']"
            ]
            apply_btn = None
            
            # Wait a moment for dynamic buttons
            await asyncio.sleep(2)
            
            for selector in apply_selectors:
                try:
                    is_visible = await self.page.is_visible(selector, timeout=2000)
                    if is_visible:
                        apply_btn = selector
                        break
                except:
                    continue
            
            if not apply_btn:
                # Check for "Apply on company site"
                if await self.page.is_visible(".company-site-button"):
                    return {'success': False, 'message': 'Redirects to company site'}
                return {'success': False, 'message': 'Apply button not found'}
            
            await self.page.click(apply_btn)
            
            # Handle possible questionnaire or success screen
            await asyncio.sleep(2)  # Wait for transition
            
            # Check if applied successfully (look for success message)
            # Naukri often shows "Applied successfully"
            success_indicators = ["Applied successfully", "Congratulations", "Application sent"]
            content = await self.page.content()
            
            for indicator in success_indicators:
                if indicator in content:
                    return {'success': True, 'message': 'Applied successfully'}
            
            # Check for questionnaire
            if await self.page.is_visible(".question-container") or await self.page.is_visible("form"):
                result = await self._handle_questionnaire(user_profile)
                return result
                
            return {'success': True, 'message': 'Applied (assumed success)'}
            
        except Exception as e:
            logger.error(f"Error applying to Naukri job: {str(e)}")
            return {'success': False, 'message': f"Apply error: {str(e)}"}

    async def _handle_questionnaire(self, user_profile):
        """Handle Naukri application questions using AI"""
        try:
            # This is a placeholder for actual questionnaire handling
            # In a real scenario, we'd extract questions, use LLM, and fill fields
            logger.info("Naukri questionnaire detected. Attempting to skip or answer...")
            
            # For now, we'll try to find a "Submit" or "Continue" button
            submit_btns = ["button.submit", "button.continue", "button:has-text('Submit')"]
            for btn in submit_btns:
                if await self.page.is_visible(btn):
                    await self.page.click(btn)
                    await asyncio.sleep(2)
                    return {'success': True, 'message': 'Submitted questionnaire'}
            
            return {'success': False, 'message': 'Could not handle questionnaire'}
        except Exception as e:
            logger.error(f"Questionnaire error: {str(e)}")
            return {'success': False, 'message': f"Questionnaire error: {str(e)}"}

async def apply_to_naukri_job(user_id, job_id, resume_path=None):
    """Orchestrator for Naukri job application"""
    credentials = NaukriCredentials.query.filter_by(user_id=user_id, is_active=True).first()
    if not credentials:
        return {'success': False, 'message': 'Naukri credentials not found'}
    
    job_post = JobPost.query.get(job_id)
    if not job_post:
        return {'success': False, 'message': 'Job not found'}
    
    user_profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    async with NaukriApplyBot(headless=True) as bot:
        logged_in = await bot.login(credentials.email, credentials.get_password())
        if not logged_in:
            return {'success': False, 'message': 'Naukri login failed'}
        
        result = await bot.apply_to_job(job_post.job_url, user_profile)
        
        # Record application
        app = Application(
            user_id=user_id,
            job_id=job_id,
            status='Applied' if result['success'] else 'Failed',
            applied_at=datetime.utcnow() if result['success'] else None,
            error_message=result['message'] if not result['success'] else None
        )
        db.session.add(app)
        db.session.commit()
        
        return result

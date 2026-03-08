"""
LinkedIn Easy Apply Bot

This module automates the Easy Apply process on LinkedIn.
It handles multi-step applications, form filling, and resume uploads.
"""

import asyncio
import logging
import os
import openai
import random
from datetime import datetime
from playwright.async_api import async_playwright, Page
from app.models import LinkedInCredentials, Resume, UserProfile, Application, JobPost, AnswerCache
from app.services.ai_metering_service import AIMeteringService
from app import db

logger = logging.getLogger(__name__)


class LinkedInEasyApplyBot:
    """Automate LinkedIn Easy Apply applications"""
    
    def __init__(self, user_id, headless=True, application_id=None):
        self.user_id = user_id
        self.headless = headless
        self.application_id = application_id
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
        """Initialize browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()
        logger.info("Easy Apply bot initialized")
    
    async def _jitter(self, min_s=0.5, max_s=1.5):
        """Random delay to mimic human behavior"""
        await asyncio.sleep(random.uniform(min_s, max_s))
    
    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
            logger.info("Easy Apply bot closed")
            
    async def _update_status(self, message):
        """Update the status message in the database for real-time tracking"""
        if self.application_id:
            try:
                def update_db():
                    app = Application.query.get(self.application_id)
                    if app:
                        app.status_message = message
                        db.session.commit()
                await asyncio.to_thread(update_db)
                logger.info(f"Status Update [{self.application_id}]: {message}")
            except Exception as e:
                logger.warning(f"Failed to update status in DB: {str(e)}")

    async def _take_screenshot(self, name="failure"):
        """Capture screenshot for debugging failures"""
        if not self.page: return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_{name}_{timestamp}.png"
            # Using absolute path for uploads/screenshots
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            filepath = os.path.join(base_dir, 'uploads', 'screenshots', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            await self.page.screenshot(path=filepath)
            
            if self.application_id:
                def save_to_db():
                    app = Application.query.get(self.application_id)
                    if app:
                        app.screenshot_path = filename
                        db.session.commit()
                await asyncio.to_thread(save_to_db)
                
            return filename
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {str(e)}")
            return None
            
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
        """Login to LinkedIn with 'already logged in' check"""
        try:
            await self._update_status("Logging in to LinkedIn...")
            # Check if we are already logged in (maybe cookies were loaded)
            # Navigation with reduced wait
            if not self.page.url or self.page.url == 'about:blank':
                await self.page.goto('https://www.linkedin.com/', wait_until='domcontentloaded')
            
            if await self._is_logged_in():
                logger.info("Already logged in to LinkedIn")
                return True
                
            # If not logged in, go to login page
            await self.page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')
            
            # Re-check login state (sometimes session is restored on this redirect)
            if await self._is_logged_in():
                return True
                
            # Try to fill login form
            try:
                await self.page.wait_for_selector('input[name="session_key"]', timeout=3000)
                await self.page.fill('input[name="session_key"]', email)
                await self.page.fill('input[name="session_password"]', password)
                await self.page.click('button[type="submit"]')
                
                # Wait for navigation to a logged-in state or a checkpoint
                for _ in range(10): # Max 5 seconds polling
                    if await self._is_logged_in():
                        return True
                    if 'checkpoint' in self.page.url:
                        logger.warning("LinkedIn login: Security checkpoint encountered.")
                        return True # Return true to let the process try to continue or manual intervention
                    await asyncio.sleep(0.5)
            except:
                return await self._is_logged_in()
            
            return await self._is_logged_in()
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False
            
    async def _is_logged_in(self):
        """Check if currently logged in to LinkedIn"""
        try:
            current_url = self.page.url
            if any(x in current_url for x in ['feed', 'mynetwork', 'messaging', 'notifications', 'jobs']):
                return True
                
            # Check for common logged-in elements
            if await self.page.query_selector('.global-nav__me-photo'):
                return True
                
            return False
        except:
            return False

    async def _click_element(self, selector_or_el, timeout=5000):
        """Robust click that handles element being blocked by overlays"""
        try:
            el = selector_or_el
            if isinstance(selector_or_el, str):
                el = await self.page.wait_for_selector(selector_or_el, timeout=timeout)
            
            if el:
                try:
                    # Try normal click first
                    await el.click(timeout=timeout)
                except Exception as click_err:
                    if "intercepts pointer events" in str(click_err) or "Timeout" in str(click_err):
                        logger.warning(f"Normal click failed, trying forced click. Error: {str(click_err)}")
                        # Try forced click (bypasses actionability checks)
                        await el.click(force=True, timeout=timeout)
                    else:
                        raise click_err
                return True
            return False
        except Exception as e:
            logger.error(f"Click error: {str(e)}")
            # Try deep search for the element if it was a selector that failed
            if isinstance(selector_or_el, str):
                deep_el = await self._find_element_deep(selector_or_el)
                if deep_el:
                    try:
                        await deep_el.click(force=True)
                        return True
                    except: pass
            return False

    async def _find_element_deep(self, selector):
        """Search for an element through shadow roots and nested frames"""
        try:
            # Playwright's locator('selector') already pierces shadow-roots by default.
            # However, for extremely complex nested cases, we jump into JS.
            handle = await self.page.evaluate_handle(f"""
                (selector) => {{
                    function findDeep(root, sel) {{
                        if (root.querySelector(sel)) return root.querySelector(sel);
                        const nodes = root.querySelectorAll('*');
                        for (const node of nodes) {{
                            if (node.shadowRoot) {{
                                const found = findDeep(node.shadowRoot, sel);
                                if (found) return found;
                            }}
                        }}
                        return null;
                    }}
                    return findDeep(document, selector);
                }}
            """, selector)
            return handle.as_element() if handle else None
        except:
            return None

    async def _type_human(self, selector_or_el, text):
        """Typing with irregular delays between keystrokes"""
        el = selector_or_el
        if isinstance(selector_or_el, str):
            el = await self.page.wait_for_selector(selector_or_el)
        
        if el:
            await el.click()
            # Clear field first
            await self.page.keyboard.press('Control+A')
            await self.page.keyboard.press('Backspace')
            
            for char in str(text):
                await self.page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.2))
            await self._jitter(0.2, 0.5)
    
    async def apply_to_job(self, job_url, user_profile, resume_path=None, job_description=None):
        """
        Apply to a job using Easy Apply
        
        Args:
            job_url (str): LinkedIn job URL
            user_profile (UserProfile): User profile data
            resume_path (str): Path to resume file
            job_description (str): Job description text for context
            
        Returns:
            dict: Application result
        """
        try:
            logger.info(f"Applying to job: {job_url}")
            await self._update_status(f"Navigating to job page...")
            
            # Navigate to job page
            await self.page.goto(job_url, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            await self._update_status("Checking for Easy Apply button...")
            # Check if Easy Apply button exists
            easy_apply_button = await self.page.query_selector('button.jobs-apply-button')
            
            if not easy_apply_button:
                await self._take_screenshot("no_apply_button")
                return {
                    'success': False,
                    'message': 'Easy Apply button not found - job may not support Easy Apply or already applied'
                }
            
            # Click Easy Apply button
            await self._update_status("Clicking Easy Apply...")
            await self._click_element(easy_apply_button)
            await asyncio.sleep(1) # Reduced from 2
            
            # Handle multi-step application
            application_result = await self._complete_application(user_profile, resume_path, job_description)
            
            if not application_result['success']:
                await self._take_screenshot("application_failed")
            
            return application_result
            
        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    async def _complete_application(self, user_profile, resume_path, job_description=None):
        """
        Complete the Easy Apply application process with improved reliability
        """
        try:
            max_steps = 15  # Increased steps for complex applications
            current_step = 0
            last_page_content = ""
            
            while current_step < max_steps:
                await self._jitter(1.0, 2.0) # Jitter between steps
                current_step += 1
                status_msg = f"Processing application step {current_step}..."
                logger.info(status_msg)
                await self._update_status(status_msg)
                
                # Check for success message first
                if await self._check_success():
                    return {'success': True, 'message': 'Application submitted successfully!'}

                # Incremental scrolling to reveal all fields in the modal
                # IMPORTANT: LinkedIn often hides required fields at the bottom
                modal_content_selector = '.artdeco-modal__content'
                try:
                    modal_el = await self.page.query_selector(modal_content_selector)
                    if modal_el:
                        # Scroll in 3 parts to trigger dynamic loading of fields
                        for i in range(1, 4):
                            await modal_el.evaluate(f"node => node.scrollTop = node.scrollHeight * {i/3}")
                            await asyncio.sleep(0.5)
                            # Fill fields visible at this scroll level
                            await self._fill_form_fields(user_profile, job_description)
                        
                        # Return to top to ensure we didn't miss validation errors
                        await modal_el.evaluate("node => node.scrollTop = 0")
                except:
                    # Fallback if modal selector differs
                    await self._fill_form_fields(user_profile, job_description)
                
                # Handle resume upload
                if resume_path:
                    await self._upload_resume(resume_path)
                
                # Final check for submission
                submit_button = await self.page.query_selector('button[aria-label*="Submit"], button:has-text("Submit")')
                if submit_button and await submit_button.is_visible() and await submit_button.is_enabled():
                    logger.info("Submission button found. Clicking Submit.")
                    await self._click_element(submit_button)
                    await asyncio.sleep(3)
                    if await self._check_success():
                        return {'success': True, 'message': 'Application submitted successfully!'}
                
                # Navigation: Next, Continue, Review
                next_selectors = [
                    'button[aria-label*="Review"]',
                    'button[aria-label*="Next"]', 
                    'button[aria-label*="Continue"]',
                    'button:has-text("Review")',
                    'button:has-text("Next")',
                    'button:has-text("Continue")'
                ]
                
                next_button = None
                for selector in next_selectors:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible() and await btn.is_enabled():
                        next_button = btn
                        break
                
                if next_button:
                    # Check for validation errors before clicking
                    errors = await self.page.query_selector_all('.artdeco-inline-feedback--error')
                    if errors:
                        err_texts = [await e.inner_text() for e in errors]
                        logger.warning(f"Validation errors present before clicking Next: {err_texts}")
                        # Try to fix any specific empty required fields found
                        await self._fix_validation_errors(user_profile, job_description)

                    logger.info(f"Navigating to next step (Selector found)")
                    await self._click_element(next_button)
                    await asyncio.sleep(2)
                    
                    current_content = await self.page.content()
                    if current_content == last_page_content:
                        logger.warning("Stuck on the same step. Attempting extra scroll and fix.")
                        await self._fix_validation_errors(user_profile, job_description)
                        await self._click_element(next_button) # Try one more time
                    last_page_content = current_content
                else:
                    if await self._check_success():
                        return {'success': True, 'message': 'Application submitted!'}
                    
                    done_button = await self.page.query_selector('button:has-text("Done"), button:has-text("Dismiss")')
                    if done_button:
                        await self._click_element(done_button)
                        return {'success': True, 'message': 'Application finished (Done button clicked)'}
                    
                    break
            
            # Final check before giving up
            if await self._check_success():
                return {'success': True, 'message': 'Application submitted!'}

            return {
                'success': False,
                'message': 'Application process incomplete - manual intervention may be required'
            }
            
        except Exception as e:
            logger.error(f"Application completion error: {str(e)}")
            return {
                'success': False,
                'message': f'Error completing application: {str(e)}'
            }

    async def _check_success(self):
        """Check if the application was successfully submitted"""
        success_indicators = [
            'text=Application sent',
            'text=Success!',
            '.artdeco-inline-feedback--success',
            'h3:has-text("Application sent")',
            'h1:has-text("Application sent")',
            '.jp-post-apply-success-message'
        ]
        for indicator in success_indicators:
            if await self.page.query_selector(indicator):
                logger.info(f"Success indicator found: {indicator}")
                return True
        return False
    
    async def _fill_form_fields(self, user_profile, job_description=None):
        """Fill form fields with user data - covers text, number, selects, and radios"""
        try:
            # 1. Handle Text, Tel, Email, Number inputs and Textareas
            selectors = [
                'input[type="text"]', 'input[type="tel"]', 'input[type="email"]', 
                'input[type="number"]', 'textarea', 'input:not([type])'
            ]
            for selector in selectors:
                elements = await self.page.query_selector_all(selector)
                for el in elements:
                    if not await el.is_visible() or await el.input_value():
                        continue
                        
                    # Find label for context
                    field_id = await el.get_attribute('id')
                    label_text = ""
                    if field_id:
                        label_el = await self.page.query_selector(f'label[for="{field_id}"]')
                        if label_el:
                            label_text = await label_el.inner_text()
                    
                    if not label_text:
                        label_text = await el.get_attribute('aria-label') or await el.get_attribute('placeholder') or "question"

                    # Specific fix for LinkedIn mandatory fields that think they are optional
                    if 'last working day' in label_text.lower():
                        await el.fill('N/A')
                        continue

                    answer = await self._ask_ai_to_fill_field(label_text, user_profile, job_description)
                    if answer:
                        await self._type_human(el, str(answer))
            
            # 2. Handle Dropdowns (Selects)
            selects = await self.page.query_selector_all('select')
            for select in selects:
                if not await select.is_visible():
                    continue
                
                label_text = "question"
                field_id = await select.get_attribute('id')
                if field_id:
                    label_el = await self.page.query_selector(f'label[for="{field_id}"]')
                    if label_el:
                        label_text = await label_el.inner_text()

                options = await select.query_selector_all('option')
                option_texts = [await opt.inner_text() for opt in options if await opt.get_attribute('value')]
                
                if option_texts:
                    # Clean question context for AI but keep label as the key
                    ai_context = f"Choose from choices: {', '.join(option_texts)}"
                    ai_choice = await self._ask_ai_to_fill_field(label_text, user_profile, job_description, context=ai_context)
                    
                    # Diversity/General categories matching
                    matched = False
                    for opt in options:
                        opt_text = await opt.inner_text()
                        if ai_choice and (ai_choice.lower() in opt_text.lower() or opt_text.lower() in ai_choice.lower()):
                            val = await opt.get_attribute('value')
                            await select.select_option(val)
                            matched = True
                            break
                    
                    # Fallback for mandatory diversity questions if AI failed to pick accurately
                    if not matched and any(x in label_text.lower() for x in ['gender', 'ethnic', 'orientation', 'race']):
                         # Pick first non-empty option if mandatory
                         for val in [opt for opt in options if await opt.get_attribute('value')]:
                             await select.select_option(await val.get_attribute('value'))
                             break
            
            # 3. Handle Radio Buttons (Yes/No or multi-choice)
            fieldsets = await self.page.query_selector_all('fieldset')
            for fieldset in fieldsets:
                if not await fieldset.is_visible():
                    continue
                
                legend = await fieldset.query_selector('legend')
                question = await legend.inner_text() if legend else "question"
                
                # Check if already answered
                checked = await fieldset.query_selector('input[checked], input:checked')
                if checked:
                    continue

                labels = await fieldset.query_selector_all('label')
                label_texts = [await l.inner_text() for l in labels]
                
                if label_texts:
                    ai_context = f"Choose from choices: {', '.join(label_texts)}"
                    ai_choice = await self._ask_ai_to_fill_field(question, user_profile, job_description, context=ai_context)
                    for label in labels:
                        l_text = await label.inner_text()
                        if ai_choice and (ai_choice.lower() in l_text.lower() or l_text.lower() in ai_choice.lower()):
                            await label.click()
                            break
                    else:
                        # Fallback for Yes/No if AI response was ambiguous
                        if 'yes' in ai_choice.lower():
                            yes_label = await fieldset.query_selector('label:has-text("Yes")')
                            if yes_label: await yes_label.click()
                        elif 'no' in ai_choice.lower():
                            no_label = await fieldset.query_selector('label:has-text("No")')
                            if no_label: await no_label.click()
                            
            # 4. Handle Checkboxes
            checkboxes = await self.page.query_selector_all('input[type="checkbox"]')
            for cb in checkboxes:
                if await cb.is_visible() and not await cb.is_checked():
                    await cb.check()

            logger.info("Form fields filling cycle completed")
        except Exception as e:
            logger.error(f"Error filling form: {str(e)}")

    async def _fix_validation_errors(self, user_profile, job_description=None):
        """Force fill fields that have error messages highlighted"""
        try:
            error_containers = await self.page.query_selector_all('.artdeco-inline-feedback--error')
            for container in error_containers:
                # Find input/select related to this error
                parent = await container.query_selector('xpath=..')
                field = await parent.query_selector('input, select, textarea')
                if field:
                    logger.info("Fixing validation error for field")
                    label = await parent.query_selector('label')
                    label_text = await label.inner_text() if label else "required field"
                    
                    if 'last working day' in label_text.lower():
                        await field.fill('N/A')
                    else:
                        answer = await self._ask_ai_to_fill_field(label_text, user_profile, job_description)
                        
                        # SMART FALLBACK: If initial answer resulted in an error, try variation
                        # e.g. "Three years" -> "3"
                        if 'input' in await field.evaluate('node => node.tagName.toLowerCase()'):
                            await self._type_human(field, str(answer or ""))
                            await self._jitter(0.5, 1.0)
                            
                            # Check if error persists
                            still_has_error = await parent.query_selector('.artdeco-inline-feedback--error')
                            if still_has_error:
                                logger.info("Validation persists, trying numeric fallback")
                                prompt = f"The answer '{answer}' for '{label_text}' failed validation. Provide ONLY the numeric value if applicable, or a 1-word alternative."
                                fallback_answer = await self._ask_ai_to_fill_field(prompt, user_profile, job_description)
                                if fallback_answer:
                                    await self._type_human(field, str(fallback_answer))
                                    
                        elif 'select' in await field.evaluate('node => node.tagName.toLowerCase()'):
                             await field.select_option(index=1) # Pick first valid option as fallback
        except:
            pass
    
    async def _upload_resume(self, resume_path):
        """Upload resume if file input is present"""
        try:
            file_input = await self.page.query_selector('input[type="file"]')
            if file_input:
                await file_input.set_input_files(resume_path)
                logger.info(f"Resume uploaded: {resume_path}")
                await asyncio.sleep(2)  # Wait for upload
        except Exception as e:
            logger.error(f"Resume upload error: {str(e)}")

    async def _ask_ai_to_fill_field(self, field_label, user_profile, job_description=None, context=None):
        """Use the unified metered AI service to answer job application questions"""
        try:
            from app.models import AnswerCache
            
            user_id = self.user_id
            
            # 1. Check Cache first (normalized question)
            normalized_q = field_label.strip().lower()
            if user_id:
                def get_cached():
                    cached = AnswerCache.query.filter_by(user_id=user_id, question_text=normalized_q).first()
                    if cached:
                        # Update last_used_at
                        cached.last_used_at = datetime.utcnow()
                        db.session.commit()
                    return cached
                cached = await asyncio.to_thread(get_cached)
                if cached:
                    logger.info(f"Using cached answer for: {normalized_q}")
                    return cached.answer_text

            # Handle empty or None profile
            skills = getattr(user_profile, 'skills', 'Software Engineering') if user_profile else 'Software Engineering'
            experience = getattr(user_profile, 'experience', '2') if user_profile else '2'
            roles = getattr(user_profile, 'preferred_roles', 'Software Developer') if user_profile else 'Software Developer'
            
            job_context = f"\nJob Description Context:\n{job_description[:1000]}" if job_description else ""
            additional_context = f"\nAdditional Field Context:\n{context}" if context else ""
            
            prompt = f"""
Answer this job application question for a user with the following profile:
Skills: {skills}
Experience: {experience} years
Preferred Roles: {roles}
{job_context}
{additional_context}

Question: "{field_label}"

If it's a numeric question (e.g. years of experience), return only the number.
If it's a yes/no question, return "Yes" or "No".
If it's a choice question, return the best matching option from the list provided.
If it's a short text question, keep the answer concise (under 20 words).
Return only the answer text.
"""
            metered_resp = await AIMeteringService.ask_ai_metered(
                user_id=user_id,
                feature_type='auto_apply',
                prompt=prompt,
                system_prompt="You are a job application assistant. Provide concise, accurate answers based on the user's profile and the job context.",
                max_tokens=50,
                temperature=0
            )
            
            if not metered_resp.get('success'):
                logger.error(f"Metered AI Field Fill failed: {metered_resp.get('message')}")
                return ""

            answer = metered_resp.get('text', '')
            
            logger.info(f"AI Answer for '{field_label}': {answer}")
            
            # Save or handle empty answer
            final_answer = answer if answer else "[USER_INPUT_REQUIRED]"
            
            if user_id:
                try:
                    def save_cache():
                        # Check if already exists (might have failed mid-way before)
                        existing = AnswerCache.query.filter_by(user_id=user_id, question_text=normalized_q).first()
                        if not existing:
                            new_cache = AnswerCache(user_id=user_id, question_text=normalized_q, answer_text=str(final_answer))
                            db.session.add(new_cache)
                            db.session.commit()
                        elif not answer and existing.answer_text != "[USER_INPUT_REQUIRED]":
                            # Don't overwrite a good answer with a failure unless it's genuinely empty
                            pass
                    await asyncio.to_thread(save_cache)
                except Exception as cache_err:
                    logger.warning(f"Failed to cache answer: {str(cache_err)}")
                    db.session.rollback()

            return answer if answer else "" # Return empty so browser validation might catch it or we can retry
        except Exception as e:
            logger.error(f"AI Field Fill Error: {str(e)}")
            # Even on error, try to save the question so user knows it exists
            if user_id:
                try:
                    def save_error_cache():
                        existing = AnswerCache.query.filter_by(user_id=user_id, question_text=normalized_q).first()
                        if not existing:
                            new_cache = AnswerCache(user_id=user_id, question_text=normalized_q, answer_text="[USER_INPUT_REQUIRED]")
                            db.session.add(new_cache)
                            db.session.commit()
                    asyncio.create_task(asyncio.to_thread(save_error_cache))
                except: pass
            return ""


async def apply_to_linkedin_job(user_id, job_id, application_id=None, resume_path=None):
    """
    Apply to a LinkedIn job for a user
    
    Args:
        user_id (int): User ID
        job_id (int): Job ID (from JobPost table)
        application_id (int, optional): Application ID for tracking status
        resume_path (str, optional): Explicit path to resume to use
        
    Returns:
        dict: Application result
    """
    try:
        # Get user credentials
        credentials = LinkedInCredentials.query.filter_by(
            user_id=user_id,
            is_active=True
        ).first()
        
        if not credentials:
            return {
                'success': False,
                'message': 'LinkedIn credentials not found'
            }
        
        # Get job details
        job = db.session.get(JobPost, job_id)
        if not job:
            return {
                'success': False,
                'message': 'Job not found'
            }
        
        # Get user profile
        from app.models import UserProfile, Resume
        user_profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        if resume_path:
            logger.info(f"Using explicitly provided resume: {resume_path}")
        else:
            # SMART MULTI-RESUME SELECTION (Prioritizes Recency)
            resumes = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).all()
            if not resumes:
                resume_path = None
            elif len(resumes) == 1:
                resume_path = resumes[0].file_path
            else:
                # Let AI pick the best resume
                resume_choices = "\n".join([
                    f"ID {r.id}: {r.file_path.split('/')[-1].split('\\')[-1]} (Uploaded: {r.uploaded_at.strftime('%Y-%m-%d')})" 
                    for r in resumes
                ])
                
                pick_prompt = f"""
    A user has multiple resumes. Pick the best one for this specific job.
    PRIORITY: If a resume was recently uploaded (today/yesterday) and matches the skills, prefer it as it likely contains the latest updates.
    
    Job Description Snippet:
    {job.description[:1000]}
    
    User Resume Options (Sorted newest to oldest):
    {resume_choices}
    
    Which resume ID is the best match for this specific job? Return ONLY the ID number.
    If multipe are equally good, return the record with ID {resumes[0].id} as it is the most recent.
    """
                try:
                    metered_resp = await AIMeteringService.ask_ai_metered(
                        user_id=user_id,
                        feature_type='auto_apply',
                        prompt=pick_prompt,
                        system_prompt="You are a recruitment assistant selecting the most relevant and updated resume.",
                        temperature=0
                    )
                    
                    if not metered_resp.get('success'):
                        raise ValueError(metered_resp.get('message'))

                    best_id_str = metered_resp.get('text', '')
                    # Extract digits to handle cases where AI returns "ID: 5" or similar
                    best_id = int(''.join(filter(str.isdigit, str(best_id_str))))
                    chosen_resume = next((r for r in resumes if r.id == best_id), resumes[0])
                    resume_path = chosen_resume.file_path
                    logger.info(f"AI selected resume (ID {best_id}): {resume_path}")
                except Exception as e:
                    logger.warning(f"AI resume selection failed: {e}. Falling back to newest.")
                    # Fallback to the latest primary or simply the newest one
                    primary = next((r for r in resumes if r.is_primary), resumes[0])
                    resume_path = primary.file_path
        
        # Initialize bot and apply
        async with LinkedInEasyApplyBot(user_id=user_id, headless=True, application_id=application_id) as bot:
            # Load cookies if available
            import json
            if credentials.session_cookies:
                try:
                    cookies = json.loads(credentials.session_cookies)
                    await bot.set_cookies(cookies)
                except Exception as e:
                    logger.error(f"Error loading cookies: {str(e)}")
            
            # Login
            email = credentials.email
            password = credentials.get_password()
            
            login_success = await bot.login(email, password)
            if not login_success:
                return {
                    'success': False,
                    'message': 'LinkedIn login failed'
                }
            
            # Save cookies after successful login
            try:
                new_cookies = await bot.get_cookies()
                credentials.session_cookies = json.dumps(new_cookies)
                credentials.last_login = datetime.utcnow()
                db.session.commit()
            except Exception as e:
                logger.error(f"Error saving cookies: {str(e)}")
                db.session.rollback()
            
            # Apply to job
            result = await bot.apply_to_job(job.job_url, user_profile, resume_path, job.description)
            
            # Record application in database
            def finalize_application():
                if application_id:
                    app_record = db.session.get(Application, application_id)
                else:
                    # Check if somehow another record was created while we were processing
                    app_record = Application.query.filter_by(user_id=user_id, job_id=job_id).first()
                    if not app_record:
                        app_record = Application(user_id=user_id, job_id=job_id)
                        db.session.add(app_record)

                if app_record:
                    if result['success']:
                        app_record.status = 'Applied'
                        app_record.applied_at = datetime.utcnow()
                        app_record.status_message = 'Submitted successfully!'
                        app_record.error_message = None
                    else:
                        app_record.status = 'Failed'
                        app_record.error_message = result['message']
                        # status_message might already contain the last step reached
                    db.session.commit()
            
            await asyncio.to_thread(finalize_application)
            return result
            
    except Exception as e:
        logger.error(f"Apply to job error: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

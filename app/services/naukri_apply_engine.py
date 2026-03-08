import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from app.services.selenium_driver import get_chrome_driver
from app.utils.human_behavior import random_delay, human_scroll, safe_click, type_like_human
from app.models import NaukriCredentials, JobPost, Application
from app.extensions import db

logger = logging.getLogger(__name__)

class JobApplyEngine(ABC):
    """
    Abstract Base Class for Job Application Engines.
    Each platform (Naukri, LinkedIn, Indeed) should implement this.
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.driver = None
        self.wait = None

    def start_driver(self):
        """Initializes the Selenium Driver"""
        logger.info(f"Starting driver for User {self.user_id}")
        self.driver = get_chrome_driver(self.user_id)
        self.wait = WebDriverWait(self.driver, 15)

    def stop_driver(self):
        """Quits the Selenium Driver safely"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"Driver stopped for User {self.user_id}")
            except Exception as e:
                logger.error(f"Error stopping driver: {e}")
            finally:
                self.driver = None

    @abstractmethod
    def login(self) -> bool:
        pass

    @abstractmethod
    def ensure_logged_in(self) -> bool:
        pass

    @abstractmethod
    def search_jobs(self, query: str, location: str) -> List[Dict]:
        pass

    @abstractmethod
    def apply_to_job(self, job_data: Dict) -> bool:
        pass


class SeleniumNaukriApplyEngine(JobApplyEngine):
    """
    Concrete implementation for Naukri.com using Selenium.
    Optimized for 'Easy Apply' flows and robust error handling.
    """

    LOGIN_URL = "https://www.naukri.com/nlogin/login"
    HOME_URL = "https://www.naukri.com/"
    
    def login(self) -> bool:
        """
        Logs into Naukri using stored credentials.
        """
        try:
            creds = NaukriCredentials.query.filter_by(user_id=self.user_id, is_active=True).first()
            if not creds:
                logger.error(f"No active Naukri credentials for User {self.user_id}")
                return False

            logger.info("Navigating to Naukri login page...")
            self.driver.get(self.LOGIN_URL)
            random_delay()

            # Check if redirection happened (already logged in)
            if "login" not in self.driver.current_url:
                logger.info("Already logged in (redirected)")
                return True

            # Enter Username
            try:
                username_field = self.wait.until(EC.visibility_of_element_located((By.ID, "usernameField")))
                type_like_human(username_field, creds.email)
            except TimeoutException:
                 logger.info("Username field not found, checking if already logged in via UI")
                 if self.ensure_logged_in():
                     return True
                 raise

            # Enter Password
            password_field = self.driver.find_element(By.ID, "passwordField")
            type_like_human(password_field, creds.get_password())
            random_delay(1, 2)

            # Click Login
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button.blue-btn")
            safe_click(self.driver, submit_btn)
            
            # Wait for Navigation
            random_delay(3, 5)
            
            if self.ensure_logged_in():
                logger.info("Successfully logged into Naukri")
                return True
            else:
                # Check for errors
                try:
                    err = self.driver.find_element(By.CSS_SELECTOR, ".server-err").text
                    logger.error(f"Login failed: {err}")
                except:
                    logger.error("Login failed (Unknown reason)")
                return False

        except Exception as e:
            logger.error(f"Login Exception: {e}")
            return False

    def ensure_logged_in(self) -> bool:
        """
        Verifies login state by checking for profile elements.
        """
        try:
            # Common indicators of a logged-in session on Naukri
            indicators = [
                (By.CLASS_NAME, "nI-gNb-header__logo"), # Header logo often present for all
                (By.CLASS_NAME, "nI-gNb-drawer__icon"), # Mobile/Drawer menu
                (By.CSS_SELECTOR, "div.nI-gNb-drawer"),
                (By.XPATH, "//div[contains(@class, 'nI-gNb-mb-icon')]")
            ]
            
            for by, val in indicators:
                try:
                    if self.driver.find_elements(by, val):
                        # Use a more specific check: The 'View Profile' or User Image usually confirms AUTH vs just PAGE LOAD
                        if self.driver.find_elements(By.CSS_SELECTOR, "img.nI-gNb-user-img") or \
                           self.driver.find_elements(By.XPATH, "//a[contains(@href, '/mnj/user/profile')]"):
                            return True
                except:
                    continue
            
            return False
        except Exception:
            return False

    def search_jobs(self, query: str, location: str = "") -> List[Dict]:
        """
        Performs a job search on Naukri.
        """
        logger.info(f"Searching for '{query}' in '{location}'")
        try:
            self.driver.get(self.HOME_URL)
            random_delay(2, 4)

            # Handle Search Inputs
            try:
                # Search Bar
                search_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.suggestor-input")))
                safe_click(self.driver, search_input)
                type_like_human(search_input, query)
                random_delay(1, 2)
                
                # Location Bar (if applicable - Naukri UI changes often, sometimes it's separate)
                if location:
                    # Try finding the second input or specific location input
                    inputs = self.driver.find_elements(By.CSS_SELECTOR, "input.suggestor-input")
                    if len(inputs) > 1:
                        loc_input = inputs[1]
                        safe_click(self.driver, loc_input)
                        type_like_human(loc_input, location)
                        random_delay(1, 2)

                # Click Search
                search_btn = self.driver.find_element(By.CSS_SELECTOR, "div.qsbSubmit")
                safe_click(self.driver, search_btn)
                
            except TimeoutException:
                logger.warning("Standard search bar not found, trying fallback URL construction")
                q = query.replace(" ", "-")
                l = location.replace(" ", "-")
                url = f"https://www.naukri.com/{q}-jobs-in-{l}" if location else f"https://www.naukri.com/{q}-jobs"
                self.driver.get(url)

            # Wait for Results
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".srp-jobtuple-wrapper")))
            random_delay(2, 4)
            human_scroll(self.driver)

            # Extract Basic Data
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, ".srp-jobtuple-wrapper")
            results = []
            
            for card in job_cards[:15]: # Limit parsing to top 15
                try:
                    title_elem = card.find_element(By.CSS_SELECTOR, "a.title")
                    title = title_elem.text
                    url = title_elem.get_attribute("href")
                    
                    # Filter for things that look like "Easy Apply" if possible, 
                    # but Naukri doesn't always tag them clearly until clicked.
                    # We'll return everything and filter in the apply step.
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "element": card # We prefer fresh find, but keeping reference can be risky in Selenium if DOM updates
                    })
                except:
                    continue
            
            logger.info(f"Found {len(results)} jobs via Selenium search")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def apply_to_job(self, job_url: str) -> bool:
        """
        Navigates to a job and attempts to apply.
        Handles window switching and simple apply flows.
        """
        logger.info(f"Processing Job: {job_url}")
        original_window = self.driver.current_window_handle
        
        try:
            # Open new tab for the job
            self.driver.switch_to.new_window('tab')
            self.driver.get(job_url)
            random_delay(2, 4)
            
            # Check for "Apply" button
            try:
                # Naukri has multiple classes for Apply buttons: "apply-button", "create-job-alert" (no), "premium-apply"
                apply_btn = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Apply') or contains(@class, 'apply-button')]")
                ))
                
                # Verify it's not "Already Applied"
                if "Applied" in apply_btn.text:
                    logger.info("Already applied to this job.")
                    return False
                
                logger.info("Clicking Apply button...")
                safe_click(self.driver, apply_btn)
                random_delay(2, 3)
                
                # Case 1: Chatbot / Modal Apply
                # Naukri often opens a chatbot-style modal or a simple form modal
                modal_selectors = ["div.chatbot-layer", "div.apply-message", "div.success-modal"]
                
                # Look for success or further questions. 
                # For this MVP, we assume if we clicked Apply and didn't get a redirect to external site, 
                # we might need to handle a "Submit" in a modal.
                
                # Check for "Update Profile and Apply" or immediate success
                # This is highly dynamic. We will look for a Success indicator.
                
                # If redirection to company site happened
                if len(self.driver.window_handles) > 2:
                    logger.info("Redirected to external company site - Skipping (Not Easy Apply)")
                    return False

                # Heuristic: Check for success message in DOM
                success = False
                try:
                    self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'successfully applied') or contains(text(), 'Application sent')]")))
                    logger.info("Application successful!")
                    success = True
                except TimeoutException:
                    # Maybe it's a form we need to submit?
                    # Try finding a "Submit" button in a modal
                    try:
                        submit_modal = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'Send')]")
                        safe_click(self.driver, submit_modal)
                        random_delay(2)
                        success = True
                    except:
                        logger.warning("Could not find final submit or success confirmation. Marking as possible failure.")

                return success

            except TimeoutException:
                logger.warning("Apply button not found or not clickable.")
                return False
                
        except Exception as e:
            logger.error(f"Apply failed logic: {e}")
            return False
            
        finally:
            # Cleanup - Close tab and return to main
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(original_window)
            except Exception as e:
                logger.error(f"Window switching error: {e}")

    def apply_easy_apply_jobs(self, limit: int = 5):
        """
        Main orchestration method to search and apply.
        """
        # Hardcoded default search for now, can be parameterized
        # In a real scenario, we'd fetch user preferences
        jobs = self.search_jobs("Python Developer", "Remote")
        
        applied_count = 0
        for job in jobs:
            if applied_count >= limit:
                break
                
            success = self.apply_to_job(job['url'])
            if success:
                applied_count += 1
                # Anti-bot delay between applications
                random_delay(10, 20) 
        
        logger.info(f"Session finished. Applied to {applied_count} jobs.")

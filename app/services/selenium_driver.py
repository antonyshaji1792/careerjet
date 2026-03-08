import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from app.models import SystemConfig

logger = logging.getLogger(__name__)

def get_chrome_driver(user_id):
    """
    Factory to create a Selenium Chrome Driver with a persistent profile for the user.
    Optimized for anti-detection and efficiency.
    """
    try:
        chrome_options = Options()
        
        # --- 1. Persistent Session ---
        # Base directory for sessions
        base_session_dir = os.path.join(os.getcwd(), 'selenium_sessions', 'naukri')
        user_session_dir = os.path.join(base_session_dir, str(user_id))
        
        if not os.path.exists(user_session_dir):
            os.makedirs(user_session_dir)
            
        chrome_options.add_argument(f"user-data-dir={user_session_dir}")
        logger.info(f"Using Chrome profile: {user_session_dir}")

        # --- 2. Anti-Bot / Anti-Detection ---
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Spoof User Agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # --- 3. Performance & Stability ---
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        if os.environ.get('HEADLESS_MODE', 'False').lower() == 'true':
            chrome_options.add_argument("--headless=new")

        # --- 4. Driver Initialization ---
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Remove `navigator.webdriver` property for extra stealth
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info(f"Chrome Driver started successfully for User {user_id}")
        return driver

    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        raise

def get_pdf_print_driver():
    """
    Factory specifically for headless PDF generation.
    Stateless (incognito-like), headless, and optimized for printing.
    """
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new") # Mandatory for PDF gen
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Hide scrollbars to avoid printing them
        chrome_options.add_argument("--hide-scrollbars")
        
        # Robustness for local resources and mixed content
        chrome_options.add_argument("--allow-file-access-from-files")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-web-security")
        
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize PDF Print driver: {e}")
        raise

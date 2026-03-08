import random
import time
import logging
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, MoveTargetOutOfBoundsException

logger = logging.getLogger(__name__)

def random_delay(min_seconds=2.0, max_seconds=6.0):
    """
    Sleep for a random amount of time to simulate human behavior.
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Sleeping for {delay:.2f} seconds...")
    time.sleep(delay)

def human_scroll(driver, speed_min=200, speed_max=500):
    """
    Scroll the page like a human, with random pauses and variable speeds.
    """
    try:
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        current_position = driver.execute_script("return window.scrollY")
        
        target_position = min(current_position + random.randint(400, 800), total_height - viewport_height)
        
        while current_position < target_position:
            scroll_by = random.randint(50, 150)
            driver.execute_script(f"window.scrollBy(0, {scroll_by});")
            current_position += scroll_by
            time.sleep(random.uniform(0.1, 0.4))
            
    except Exception as e:
        logger.warning(f"Human scroll failed: {e}")

def safe_click(driver, element, timeout=10):
    """
    Move to element, wait gently, then click.
    Uses JavaScript click as fallback if intercepted.
    """
    try:
        # Scroll logic
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(random.uniform(0.5, 1.5))
        
        # Move mouse
        actions = ActionChains(driver)
        actions.move_to_element(element).perform()
        time.sleep(random.uniform(0.2, 0.8))
        
        # Click
        element.click()
        logger.debug("Clicked element successfully")
    except (TimeoutException, MoveTargetOutOfBoundsException) as e:
        logger.warning(f"Standard click failed, trying JS click: {e}")
        try:
            driver.execute_script("arguments[0].click();", element)
        except Exception as js_e:
            logger.error(f"JS click also failed: {js_e}")
            raise js_e
    except Exception as e:
        logger.error(f"Safe click failed: {e}")
        raise

def type_like_human(element, text, min_delay=0.05, max_delay=0.2):
    """
    Type text into an element one character at a time with random delays.
    """
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))

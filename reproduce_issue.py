
import requests
from bs4 import BeautifulSoup
import sys

BASE_URL = "http://localhost:5000"
LOGIN_URL = f"{BASE_URL}/auth/login"
TARGET_URL = f"{BASE_URL}/resumes/download-wysiwyg"

EMAIL = "antonyshaji17@gmail.com"
PASSWORD = "Antony1304!"

def reproduce():
    s = requests.Session()
    
    # 1. Get Login Page for CSRF Token
    print(f"Fetching {LOGIN_URL}...")
    try:
        r = s.get(LOGIN_URL)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    soup = BeautifulSoup(r.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})
    if not csrf_token:
        print("Could not find CSRF token on login page.")
        # Some apps might not use csrf_token in the form if disabled, but let's assume it's there
        # Check meta tag
        meta_csrf = soup.find('meta', {'name': 'csrf-token'})
        if meta_csrf:
            csrf_token_val = meta_csrf['content']
        else:
            print("No CSRF token found anywhere.")
            csrf_token_val = None
    else:
        csrf_token_val = csrf_token['value']
        
    print(f"CSRF Token: {csrf_token_val}")
    
    # 2. Login
    payload = {
        'email': EMAIL,
        'password': PASSWORD,
        'csrf_token': csrf_token_val
    }
    
    print("Logging in...")
    r = s.post(LOGIN_URL, data=payload)
    print(f"Login Response: {r.status_code}")
    
    if r.url == LOGIN_URL or 'Login Unsuccessful' in r.text:
        print("Login failed.")
        return

    # 3. Simulate Download
    print("Sending PDF generation request...")
    
    # Needs valid CSRF token in header. Usually the one from login/meta works.
    # Let's refresh the token just in case by hitting the dashboard or builder
    r = s.get(f"{BASE_URL}/resumes/builder")
    soup = BeautifulSoup(r.content, 'html.parser')
    meta_csrf = soup.find('meta', {'name': 'csrf-token'})
    if meta_csrf:
        headers_csrf = meta_csrf['content']
    else:
        headers_csrf = csrf_token_val

    # Simple HTML payload
    html_payload = {
        "html_content": """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body><h1>Hello Server</h1></body>
        </html>
        """
    }
    
    headers = {
        'X-CSRFToken': headers_csrf,
        'Content-Type': 'application/json',
        'Referer': f"{BASE_URL}/resumes/builder"
    }
    
    r = s.post(TARGET_URL, json=html_payload, headers=headers)
    print(f"Download Response: {r.status_code}")
    print(f"Download Content Start: {r.content[:100]}")
    
    if r.status_code == 200:
        print("SUCCESS: PDF generated.")
    else:
        print("FAILURE: PDF not generated.")
        print(r.text)

if __name__ == "__main__":
    reproduce()

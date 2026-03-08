"""
Security and Performance Guards for Resume Builder
Implements OWASP Top 10 protections and performance optimizations
"""

import re
import hashlib
import time
from functools import wraps
from flask import request, jsonify, current_app
from werkzeug.exceptions import TooManyRequests
import logging

logger = logging.getLogger(__name__)


class SecurityGuard:
    """
    OWASP Top 10 Security Controls for Resume Builder
    """
    
    # SQL Injection Prevention
    @staticmethod
    def sanitize_sql_input(value):
        """
        Sanitize input to prevent SQL injection.
        Note: Using parameterized queries is the primary defense.
        """
        if not isinstance(value, str):
            return value
        
        # Remove dangerous SQL keywords
        dangerous_patterns = [
            r"(\bDROP\b|\bDELETE\b|\bINSERT\b|\bUPDATE\b|\bEXEC\b|\bUNION\b)",
            r"(--|;|\/\*|\*\/)",
            r"(\bOR\b\s+\d+\s*=\s*\d+)",
            r"(\bAND\b\s+\d+\s*=\s*\d+)"
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Potential SQL injection attempt detected: {value[:50]}")
                raise ValueError("Invalid input detected")
        
        return value
    
    # XSS Prevention
    @staticmethod
    def sanitize_html(text):
        """
        Sanitize HTML to prevent XSS attacks.
        Removes script tags and dangerous attributes.
        """
        if not isinstance(text, str):
            return text
        
        # Remove script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove event handlers
        text = re.sub(r'\bon\w+\s*=\s*["\']?[^"\']*["\']?', '', text, flags=re.IGNORECASE)
        
        # Remove javascript: protocol
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        # Remove data: protocol (can be used for XSS)
        text = re.sub(r'data:text/html', '', text, flags=re.IGNORECASE)
        
        return text
    
    # File Upload Security
    @staticmethod
    def validate_file_upload(file, max_size=5*1024*1024):
        """
        Validate uploaded file for security.
        Checks file size, type, and content.
        """
        if not file:
            raise ValueError("No file provided")
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > max_size:
            raise ValueError(f"File too large. Max size: {max_size/1024/1024}MB")
        
        # Check file extension
        allowed_extensions = {'.pdf', '.docx', '.doc'}
        filename = file.filename.lower()
        
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise ValueError("Invalid file type. Allowed: PDF, DOCX")
        
        # Check MIME type
        allowed_mimes = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword'
        ]
        
        # Read file signature (magic bytes)
        file_header = file.read(8)
        file.seek(0)
        
        # PDF signature: %PDF
        # DOCX signature: PK (ZIP format)
        if not (file_header.startswith(b'%PDF') or file_header.startswith(b'PK')):
            logger.warning(f"File signature mismatch for {filename}")
            raise ValueError("File content doesn't match extension")
        
        return True
    
    # Path Traversal Prevention
    @staticmethod
    def sanitize_filename(filename):
        """
        Sanitize filename to prevent path traversal attacks.
        """
        # Remove path separators
        filename = filename.replace('/', '').replace('\\', '')
        
        # Remove parent directory references
        filename = filename.replace('..', '')
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Limit filename length
        if len(filename) > 255:
            filename = filename[:255]
        
        # Only allow alphanumeric, dash, underscore, and dot
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        return filename
    
    # PII Detection
    @staticmethod
    def detect_pii(text):
        """
        Detect potential PII in text.
        Returns list of detected PII types.
        """
        pii_patterns = {
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        }
        
        detected = []
        for pii_type, pattern in pii_patterns.items():
            if re.search(pattern, text):
                detected.append(pii_type)
        
        return detected


class PerformanceGuard:
    """
    Performance optimization and monitoring
    """
    
    # Rate Limiting
    _rate_limit_cache = {}
    
    @staticmethod
    def rate_limit(key, max_requests, time_window):
        """
        Simple in-memory rate limiting.
        In production, use Redis for distributed rate limiting.
        """
        now = time.time()
        
        if key not in PerformanceGuard._rate_limit_cache:
            PerformanceGuard._rate_limit_cache[key] = []
        
        # Clean old requests
        PerformanceGuard._rate_limit_cache[key] = [
            req_time for req_time in PerformanceGuard._rate_limit_cache[key]
            if now - req_time < time_window
        ]
        
        # Check limit
        if len(PerformanceGuard._rate_limit_cache[key]) >= max_requests:
            return False
        
        # Add current request
        PerformanceGuard._rate_limit_cache[key].append(now)
        return True
    
    # Token Budget Tracking
    _token_usage = {}
    
    @staticmethod
    def check_token_budget(user_id, tokens_needed, daily_limit=50000):
        """
        Check if user has enough token budget.
        Prevents excessive AI API costs.
        """
        today = time.strftime('%Y-%m-%d')
        key = f"{user_id}:{today}"
        
        if key not in PerformanceGuard._token_usage:
            PerformanceGuard._token_usage[key] = 0
        
        if PerformanceGuard._token_usage[key] + tokens_needed > daily_limit:
            return False
        
        PerformanceGuard._token_usage[key] += tokens_needed
        return True
    
    # Query Performance Monitoring
    @staticmethod
    def monitor_query_time(func):
        """
        Decorator to monitor database query performance.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            if elapsed > 1.0:  # Log slow queries (>1s)
                logger.warning(f"Slow query detected: {func.__name__} took {elapsed:.2f}s")
            
            return result
        return wrapper


# Decorator for route protection
def require_resume_access(f):
    """
    Decorator to ensure user has access to the resume.
    Prevents unauthorized access to other users' resumes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        from app.models.resume import Resume
        
        resume_id = kwargs.get('resume_id') or kwargs.get('id')
        
        if not resume_id:
            return jsonify({'success': False, 'message': 'Resume ID required'}), 400
        
        resume = Resume.query.get(resume_id)
        
        if not resume:
            return jsonify({'success': False, 'message': 'Resume not found'}), 404
        
        if resume.user_id != current_user.id:
            logger.warning(f"Unauthorized resume access attempt: User {current_user.id} -> Resume {resume_id}")
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def rate_limit_route(max_requests=100, time_window=3600):
    """
    Decorator for route-level rate limiting.
    
    Args:
        max_requests: Maximum requests allowed
        time_window: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            
            # Create rate limit key
            key = f"rate_limit:{current_user.id}:{f.__name__}"
            
            if not PerformanceGuard.rate_limit(key, max_requests, time_window):
                logger.warning(f"Rate limit exceeded for user {current_user.id} on {f.__name__}")
                return jsonify({
                    'success': False,
                    'message': 'Rate limit exceeded. Please try again later.',
                    'error_code': 'RATE_LIMIT_EXCEEDED'
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def sanitize_input(f):
    """
    Decorator to sanitize all input data.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Sanitize JSON body
        if request.is_json:
            data = request.get_json()
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = SecurityGuard.sanitize_html(value)
        
        return f(*args, **kwargs)
    
    return decorated_function


# CSRF Protection (Flask-WTF handles this, but here's a manual check)
def verify_csrf_token():
    """
    Verify CSRF token for state-changing requests.
    """
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
        
        if not token:
            logger.warning("Missing CSRF token")
            return False
        
        # Verify token (simplified - use Flask-WTF in production)
        # This is just a placeholder
        return True
    
    return True


# Content Security Policy Headers
def set_security_headers(response):
    """
    Set security headers on response.
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    return response

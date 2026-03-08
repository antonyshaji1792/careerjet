"""
Website Preference Helper Functions

This module provides utility functions to check user's website preferences
for job applications.
"""

from app.models import WebsitePreference
from app import db


def get_enabled_platforms(user_id):
    """
    Get list of enabled platform names for a user.
    
    Args:
        user_id (int): The user's ID
        
    Returns:
        list: List of enabled platform names (e.g., ['LinkedIn', 'Indeed'])
    """
    preferences = WebsitePreference.query.filter_by(
        user_id=user_id,
        is_enabled=True
    ).all()
    
    return [pref.platform_name for pref in preferences]


def is_platform_enabled(user_id, platform_name):
    """
    Check if a specific platform is enabled for a user.
    
    Args:
        user_id (int): The user's ID
        platform_name (str): Name of the platform (e.g., 'LinkedIn')
        
    Returns:
        bool: True if platform is enabled, False otherwise
              Returns True by default if no preference exists
    """
    preference = WebsitePreference.query.filter_by(
        user_id=user_id,
        platform_name=platform_name
    ).first()
    
    # If no preference exists, default to enabled
    if not preference:
        return True
    
    return preference.is_enabled


def get_platform_preferences(user_id):
    """
    Get all platform preferences for a user as a dictionary.
    
    Args:
        user_id (int): The user's ID
        
    Returns:
        dict: Dictionary mapping platform names to enabled status
              e.g., {'LinkedIn': True, 'Indeed': False, ...}
    """
    preferences = WebsitePreference.query.filter_by(user_id=user_id).all()
    
    return {pref.platform_name: pref.is_enabled for pref in preferences}


def set_platform_preference(user_id, platform_name, is_enabled):
    """
    Set or update a platform preference for a user.
    
    Args:
        user_id (int): The user's ID
        platform_name (str): Name of the platform
        is_enabled (bool): Whether the platform should be enabled
        
    Returns:
        WebsitePreference: The created or updated preference object
    """
    preference = WebsitePreference.query.filter_by(
        user_id=user_id,
        platform_name=platform_name
    ).first()
    
    if preference:
        preference.is_enabled = is_enabled
    else:
        preference = WebsitePreference(
            user_id=user_id,
            platform_name=platform_name,
            is_enabled=is_enabled
        )
        db.session.add(preference)
    
    db.session.commit()
    return preference


def initialize_default_preferences(user_id):
    """
    Initialize default preferences for a new user (all platforms enabled).
    
    Args:
        user_id (int): The user's ID
        
    Returns:
        list: List of created preference objects
    """
    default_platforms = [
        'LinkedIn', 'Indeed', 'Naukri', 'Monster', 'Glassdoor',
        'AngelList', 'Dice', 'CareerBuilder', 'ZipRecruiter', 'SimplyHired'
    ]
    
    preferences = []
    for platform in default_platforms:
        # Only create if doesn't exist
        existing = WebsitePreference.query.filter_by(
            user_id=user_id,
            platform_name=platform
        ).first()
        
        if not existing:
            pref = WebsitePreference(
                user_id=user_id,
                platform_name=platform,
                is_enabled=True
            )
            db.session.add(pref)
            preferences.append(pref)
    
    db.session.commit()
    return preferences


def get_enabled_platform_count(user_id):
    """
    Get count of enabled platforms for a user.
    
    Args:
        user_id (int): The user's ID
        
    Returns:
        int: Number of enabled platforms
    """
    return WebsitePreference.query.filter_by(
        user_id=user_id,
        is_enabled=True
    ).count()


# Example usage in job application service:
"""
from app.services.website_preferences import is_platform_enabled, get_enabled_platforms

def apply_to_jobs(user_id, jobs):
    '''Apply to jobs based on user's platform preferences'''
    enabled_platforms = get_enabled_platforms(user_id)
    
    for job in jobs:
        # Check if user wants to apply to this platform
        if job.platform in enabled_platforms:
            # Apply to the job
            submit_application(job)
        else:
            # Skip this job
            print(f"Skipping {job.title} on {job.platform} - platform disabled")

def should_scrape_platform(user_id, platform_name):
    '''Check if we should scrape jobs from this platform for the user'''
    return is_platform_enabled(user_id, platform_name)
"""

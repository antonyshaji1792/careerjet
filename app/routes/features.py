"""
Features Routes

Displays all CareerJet features in a beautiful showcase page.
"""

from flask import Blueprint, render_template
from flask_login import current_user

bp = Blueprint('features', __name__, url_prefix='/features')


@bp.route('/', methods=['GET'])
def index():
    """Features listing page"""
    
    # Organize features by category
    features = {
        'core': [
            {
                'icon': '🔍',
                'name': 'Smart Job Ingestion',
                'description': 'Automatically scrapes and aggregates job postings from multiple platforms including LinkedIn, Indeed, Naukri, and more.',
                'benefits': ['Save hours of manual searching', 'Never miss an opportunity', 'Centralized job database'],
                'status': 'active'
            },
            {
                'icon': '💼',
                'name': 'LinkedIn Integration',
                'description': 'Automated LinkedIn job scraping and Easy Apply automation with encrypted credential storage.',
                'benefits': ['Access millions of LinkedIn jobs', 'One-click Easy Apply', 'Secure credential management'],
                'status': 'active'
            },
            {
                'icon': '🎯',
                'name': 'AI Matching Engine',
                'description': 'Automatically scores and ranks jobs based on your skills, experience, and career preferences.',
                'benefits': ['Find best-fit opportunities', 'Save time on filtering', 'Personalized recommendations'],
                'status': 'active'
            },
            {
                'icon': '🤖',
                'name': 'Automated Applications',
                'description': 'Schedules and submits job applications on your behalf using intelligent browser automation.',
                'benefits': ['Apply to more jobs faster', 'Consistent application quality', 'Schedule applications'],
                'status': 'active'
            },
            {
                'icon': '📊',
                'name': 'Dashboard Tracking',
                'description': 'Comprehensive view of your entire job search progress with real-time statistics and insights.',
                'benefits': ['Track all applications', 'Monitor progress', 'Data-driven decisions'],
                'status': 'active'
            }
        ],
        'quick_wins': [
            {
                'icon': '✍️',
                'name': 'AI Cover Letter Generator',
                'description': 'Generate professional, personalized cover letters using GPT-4 AI technology in seconds.',
                'benefits': ['Save hours writing', 'Multiple tones available', '4 professional templates'],
                'status': 'active'
            },
            {
                'icon': '🔔',
                'name': 'Job Alerts',
                'description': 'Get instant email notifications when new jobs match your custom search criteria.',
                'benefits': ['Never miss opportunities', 'Custom filters', 'Daily digest option'],
                'status': 'active'
            },
            {
                'icon': '🏢',
                'name': 'Company Research Hub',
                'description': 'Comprehensive company insights including news, employee reviews, salary data, and funding information.',
                'benefits': ['Make informed decisions', 'Prepare for interviews', 'Salary negotiation data'],
                'status': 'active'
            },
            {
                'icon': '⚙️',
                'name': 'Website Preferences',
                'description': 'Select which job platforms you want to apply to with an interactive checkbox interface.',
                'benefits': ['Control your applications', '10 supported platforms', 'Easy management'],
                'status': 'active'
            }
        ],
        'advanced': [
            {
                'icon': '📄',
                'name': 'Resume Builder & Optimizer',
                'description': 'AI-powered resume creation with ATS optimization, keyword matching, and professional templates.',
                'benefits': ['ATS-optimized resumes', 'Keyword suggestions', '4 professional templates'],
                'status': 'beta'
            },
            {
                'icon': '📋',
                'name': 'Application Tracking System',
                'description': 'Kanban-style board with 7 stages, analytics dashboard, success metrics, and timeline view.',
                'benefits': ['Visual progress tracking', 'Success metrics', 'Performance insights'],
                'status': 'beta'
            },
            {
                'icon': '🎤',
                'name': 'AI Interview Preparation',
                'description': 'Mock interviews, answer evaluation, STAR response builder, and personalized coaching.',
                'benefits': ['Practice interviews', 'AI feedback', 'Confidence building'],
                'status': 'beta'
            }
        ]
    }
    
    # Feature statistics
    stats = {
        'total_features': 12,
        'ai_powered': 6,
        'integrations': 10,
        'time_saved': '20+ Hours'
    }

    
    return render_template('features/index.html', features=features, stats=stats)

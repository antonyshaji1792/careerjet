"""
Salary Negotiation Coach Routes

Handles salary analysis, negotiation strategies, and offer evaluation.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.salary_coach import SalaryNegotiationCoach
from app.models import UserProfile
from app.utils.credit_middleware import credit_required
from app.utils.rate_limiter import rate_limit
import logging


logger = logging.getLogger(__name__)

bp = Blueprint('salary', __name__, url_prefix='/salary')


@bp.route('/', methods=['GET'])
@login_required
def index():
    """Salary coach homepage"""
    coach = SalaryNegotiationCoach()
    tips = coach.get_negotiation_tips()
    
    return render_template('salary/index.html', tips=tips)


@bp.route('/market-data', methods=['GET', 'POST'])
@login_required
def market_data():
    """Get market salary data"""
    
    if request.method == 'POST':
        try:
            job_title = request.form.get('job_title')
            location = request.form.get('location', 'United States')
            experience_years = int(request.form.get('experience_years', 5))
            
            if not job_title:
                flash('Job title is required', 'danger')
                return redirect(url_for('salary.market_data'))
            
            coach = SalaryNegotiationCoach()
            data = coach.get_market_data(job_title, location, experience_years)
            
            return render_template('salary/market_data.html', 
                                 data=data,
                                 job_title=job_title,
                                 location=location,
                                 experience_years=experience_years)
            
        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('salary.market_data'))
    
    return render_template('salary/market_data.html')


@bp.route('/analyze-offer', methods=['GET', 'POST'])
@login_required
@rate_limit(limit=5, period=60)
@credit_required('salary_coach')
def analyze_offer():

    """Analyze job offer"""
    
    if request.method == 'POST':
        try:
            # Get offer details
            job_title = request.form.get('job_title')
            company_name = request.form.get('company_name')
            location = request.form.get('location', 'United States')
            base_salary = int(request.form.get('base_salary', 0))
            bonus = int(request.form.get('bonus', 0))
            equity = int(request.form.get('equity', 0))
            benefits_value = int(request.form.get('benefits_value', 0))
            experience_years = int(request.form.get('experience_years', 5))
            
            if not job_title or base_salary == 0:
                flash('Job title and base salary are required', 'danger')
                return redirect(url_for('salary.analyze_offer'))
            
            # Build offer details
            current_offer = {
                'base_salary': base_salary,
                'bonus': bonus,
                'equity': equity,
                'benefits_value': benefits_value,
                'total': base_salary + bonus + equity + benefits_value
            }
            
            # Get user profile
            profile = UserProfile.query.filter_by(user_id=current_user.id).first()
            user_profile = {
                'experience': f'{experience_years} years',
                'skills': profile.skills if profile else 'Not specified'
            }
            
            coach = SalaryNegotiationCoach()
            
            # Get market data
            market_data = coach.get_market_data(job_title, location, experience_years)
            
            # Generate strategy
            strategy = coach.generate_negotiation_strategy(current_offer, market_data, user_profile)
            
            # Analyze package
            package_analysis = coach.analyze_offer_package(current_offer)
            
            return render_template('salary/analyze_offer.html',
                                 offer=current_offer,
                                 job_title=job_title,
                                 company_name=company_name,
                                 market_data=market_data,
                                 strategy=strategy,
                                 package_analysis=package_analysis,
                                 show_results=True)
            
        except Exception as e:
            logger.error(f"Error analyzing offer: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('salary.analyze_offer'))
    
    return render_template('salary/analyze_offer.html', show_results=False)


@bp.route('/negotiate', methods=['GET', 'POST'])
@login_required
@rate_limit(limit=5, period=60)
@credit_required('salary_coach')
def negotiate():

    """Generate negotiation email"""
    
    if request.method == 'POST':
        try:
            target_salary = int(request.form.get('target_salary', 0))
            company_name = request.form.get('company_name', 'the company')
            talking_points = request.form.get('talking_points', '').split('\n')
            talking_points = [p.strip() for p in talking_points if p.strip()]
            
            if target_salary == 0:
                flash('Target salary is required', 'danger')
                return redirect(url_for('salary.negotiate'))
            
            coach = SalaryNegotiationCoach()
            email = coach.generate_counter_offer_email(target_salary, talking_points, company_name)
            
            return render_template('salary/negotiate.html',
                                 email=email,
                                 target_salary=target_salary,
                                 company_name=company_name,
                                 show_email=True)
            
        except Exception as e:
            logger.error(f"Error generating email: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('salary.negotiate'))
    
    return render_template('salary/negotiate.html', show_email=False)


@bp.route('/tips', methods=['GET'])
@login_required
def tips():
    """Negotiation tips and best practices"""
    coach = SalaryNegotiationCoach()
    all_tips = coach.get_negotiation_tips()
    
    return render_template('salary/tips.html', tips=all_tips)

"""
Salary Negotiation Coach

AI-powered salary negotiation assistance with market data and coaching.
"""

import openai
import os
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class SalaryNegotiationCoach:
    """AI-powered salary negotiation coaching"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
    
    def get_market_data(self, job_title, location='United States', experience_years=5):
        """
        Get salary market data for a role
        
        Args:
            job_title (str): Job title
            location (str): Location
            experience_years (int): Years of experience
            
        Returns:
            dict: Market data
        """
        # In production, this would integrate with APIs like Glassdoor, Levels.fyi, etc.
        # For now, using AI to generate realistic estimates
        
        try:
            prompt = f"""
Provide realistic salary data for a {job_title} position in {location} with {experience_years} years of experience.

Include:
1. Salary range (min, median, max)
2. Total compensation range (including bonuses, equity)
3. Percentile breakdown (25th, 50th, 75th, 90th)
4. Industry variations
5. Company size impact

Format as JSON with keys: base_salary, total_comp, percentiles, industry_variations, company_size_impact
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a compensation expert with access to current market data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            result = response.choices[0].message.content.strip()
            
            try:
                market_data = json.loads(result)
            except:
                # Fallback data
                market_data = self._get_fallback_market_data(job_title, experience_years)
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            return self._get_fallback_market_data(job_title, experience_years)
    
    def generate_negotiation_strategy(self, current_offer, market_data, user_profile):
        """
        Generate personalized negotiation strategy
        
        Args:
            current_offer (dict): Current offer details
            market_data (dict): Market salary data
            user_profile (dict): User's profile and experience
            
        Returns:
            dict: Negotiation strategy
        """
        try:
            prompt = f"""
Create a salary negotiation strategy:

**Current Offer:**
- Base Salary: ${current_offer.get('base_salary', 0):,}
- Bonus: ${current_offer.get('bonus', 0):,}
- Equity: ${current_offer.get('equity', 0):,}
- Total: ${current_offer.get('total', 0):,}

**Market Data:**
- Market Median: ${market_data.get('base_salary', {}).get('median', 0):,}
- 75th Percentile: ${market_data.get('base_salary', {}).get('p75', 0):,}

**Your Profile:**
- Experience: {user_profile.get('experience', 'Not specified')}
- Skills: {user_profile.get('skills', 'Not specified')}

Provide:
1. Assessment (is offer fair/low/high?)
2. Target salary to request
3. Negotiation talking points
4. Email template
5. Alternative benefits to negotiate
6. Red flags to watch for

Format as JSON with keys: assessment, target_salary, talking_points, email_template, alternative_benefits, red_flags
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert salary negotiation coach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            result = response.choices[0].message.content.strip()
            
            try:
                strategy = json.loads(result)
            except:
                strategy = {
                    'assessment': result,
                    'target_salary': current_offer.get('base_salary', 0) * 1.15,
                    'talking_points': [result],
                    'email_template': result,
                    'alternative_benefits': ['More vacation days', 'Remote work', 'Professional development budget'],
                    'red_flags': ['Vague job description', 'High turnover']
                }
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error generating strategy: {str(e)}")
            return {
                'assessment': 'Unable to assess at this time',
                'target_salary': current_offer.get('base_salary', 0),
                'talking_points': [],
                'email_template': '',
                'alternative_benefits': [],
                'red_flags': []
            }
    
    def generate_counter_offer_email(self, target_salary, talking_points, company_name):
        """
        Generate professional counter-offer email
        
        Args:
            target_salary (int): Target salary
            talking_points (list): Key points to mention
            company_name (str): Company name
            
        Returns:
            str: Email template
        """
        try:
            prompt = f"""
Write a professional, polite counter-offer email for a job offer.

**Details:**
- Target Salary: ${target_salary:,}
- Company: {company_name}
- Key Points: {', '.join(talking_points[:3])}

The email should:
1. Express enthusiasm for the role
2. Thank them for the offer
3. Professionally request higher compensation
4. Highlight value you bring
5. Remain collaborative and positive

Keep it concise (3-4 paragraphs).
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional communication expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=600
            )
            
            email = response.choices[0].message.content.strip()
            return email
            
        except Exception as e:
            logger.error(f"Error generating email: {str(e)}")
            return self._get_fallback_email_template(target_salary, company_name)
    
    def analyze_offer_package(self, offer_details):
        """
        Analyze complete offer package
        
        Args:
            offer_details (dict): Complete offer details
            
        Returns:
            dict: Analysis
        """
        base = offer_details.get('base_salary', 0)
        bonus = offer_details.get('bonus', 0)
        equity = offer_details.get('equity', 0)
        benefits_value = offer_details.get('benefits_value', 0)
        
        total_comp = base + bonus + equity + benefits_value
        
        # Calculate percentages
        base_pct = (base / total_comp * 100) if total_comp > 0 else 0
        bonus_pct = (bonus / total_comp * 100) if total_comp > 0 else 0
        equity_pct = (equity / total_comp * 100) if total_comp > 0 else 0
        
        analysis = {
            'total_compensation': total_comp,
            'breakdown': {
                'base_salary': {'amount': base, 'percentage': round(base_pct, 1)},
                'bonus': {'amount': bonus, 'percentage': round(bonus_pct, 1)},
                'equity': {'amount': equity, 'percentage': round(equity_pct, 1)},
                'benefits': {'amount': benefits_value, 'percentage': round((benefits_value/total_comp*100) if total_comp > 0 else 0, 1)}
            },
            'recommendations': []
        }
        
        # Add recommendations
        if base_pct < 70:
            analysis['recommendations'].append('Base salary is low relative to total comp - consider negotiating higher base')
        
        if equity_pct > 30:
            analysis['recommendations'].append('High equity percentage - ensure you understand vesting schedule and company valuation')
        
        if bonus_pct > 20:
            analysis['recommendations'].append('Significant bonus component - clarify performance metrics and payout history')
        
        return analysis
    
    def get_negotiation_tips(self):
        """Get general negotiation tips"""
        
        return {
            'before': [
                'Research market rates thoroughly',
                'Know your minimum acceptable salary',
                'Prepare your value proposition',
                'Practice your pitch',
                'Get everything in writing'
            ],
            'during': [
                'Let them make the first offer',
                'Don\'t immediately accept',
                'Ask for time to consider',
                'Negotiate total package, not just salary',
                'Stay professional and positive'
            ],
            'after': [
                'Get final offer in writing',
                'Review all details carefully',
                'Clarify any ambiguities',
                'Set a decision deadline',
                'Trust your gut'
            ],
            'dos': [
                'Do your research',
                'Do be confident',
                'Do highlight your value',
                'Do consider the full package',
                'Do maintain relationships'
            ],
            'donts': [
                'Don\'t lie about other offers',
                'Don\'t be aggressive',
                'Don\'t focus only on money',
                'Don\'t burn bridges',
                'Don\'t rush the decision'
            ]
        }
    
    def _get_fallback_market_data(self, job_title, experience_years):
        """Fallback market data"""
        
        # Simple estimation based on experience
        base_estimate = 50000 + (experience_years * 10000)
        
        return {
            'base_salary': {
                'min': int(base_estimate * 0.7),
                'median': base_estimate,
                'max': int(base_estimate * 1.5),
                'p25': int(base_estimate * 0.85),
                'p50': base_estimate,
                'p75': int(base_estimate * 1.2),
                'p90': int(base_estimate * 1.4)
            },
            'total_comp': {
                'min': int(base_estimate * 0.8),
                'median': int(base_estimate * 1.2),
                'max': int(base_estimate * 1.8)
            }
        }
    
    def _get_fallback_email_template(self, target_salary, company_name):
        """Fallback email template"""
        
        return f"""Dear Hiring Manager,

Thank you so much for extending the offer to join {company_name}. I'm very excited about the opportunity and the potential to contribute to the team.

After careful consideration of the offer and research into market rates for this role, I was hoping we could discuss the compensation package. Based on my experience and the value I can bring to {company_name}, I was hoping for a base salary closer to ${target_salary:,}.

I'm confident that I can make significant contributions to the team, and I'm very enthusiastic about this opportunity. I'm hopeful we can find a compensation package that reflects the value I'll bring.

I look forward to discussing this further.

Best regards,
[Your Name]"""


# Helper function
def get_negotiation_advice(current_offer, job_title, location, user_profile):
    """
    Get complete negotiation package
    
    Args:
        current_offer (dict): Current offer
        job_title (str): Job title
        location (str): Location
        user_profile (dict): User profile
        
    Returns:
        dict: Complete negotiation package
    """
    coach = SalaryNegotiationCoach()
    
    market_data = coach.get_market_data(job_title, location, user_profile.get('experience_years', 5))
    strategy = coach.generate_negotiation_strategy(current_offer, market_data, user_profile)
    
    return {
        'market_data': market_data,
        'strategy': strategy,
        'tips': coach.get_negotiation_tips()
    }

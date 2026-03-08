import re
from app.models import JobPost, UserProfile, JobMatch
from app import db

class MatchingEngine:
    def __init__(self, user_profile):
        self.profile = user_profile
        self.skills = [s.strip().lower() for s in (user_profile.skills or "").split(',') if s.strip()]
        self.roles = [r.strip().lower() for r in (user_profile.preferred_roles or "").split(',') if r.strip()]
        self.locations = [l.strip().lower() for l in (user_profile.preferred_locations or "").split(',') if l.strip()]

        # Incorporate Job Alert keywords into roles for better matching
        try:
            from app.models import JobAlert
            alerts = JobAlert.query.filter_by(user_id=user_profile.user_id, is_active=True).all()
            for alert in alerts:
                if alert.keywords:
                    # Treat alert keywords as preferred roles
                    alert_keywords = [k.strip().lower() for k in alert.keywords.split(',') if k.strip()]
                    for k in alert_keywords:
                        if k not in self.roles:
                            self.roles.append(k)
        except Exception:
            pass # Fail gracefully if DB access fails


    def calculate_score(self, job):
        score = 0
        total_weight = 0
        
        # Skill Match (40%)
        job_desc = (job.description or "").lower()
        if self.skills:
            matched_skills = [s for s in self.skills if s in job_desc]
            skill_score = (len(matched_skills) / len(self.skills)) * 40
            score += skill_score
            total_weight += 40
            
        # Title/Role Match (30%)
        job_title = job.title.lower()
        if self.roles:
            role_match = any(role in job_title for role in self.roles)
            if role_match:
                score += 30
            total_weight += 30
            
        # Location Match (20%)
        job_location = (job.location or "").lower()
        if self.locations:
            loc_match = any(loc in job_location for loc in self.locations)
            if loc_match:
                score += 20
            total_weight += 20
            
        # Experience Match (10%)
        # Basic regex to find years of experience in job description
        exp_match = re.search(r'(\d+)\+?\s*years?', job_desc)
        if exp_match:
            required_exp = int(exp_match.group(1))
            if self.profile.experience >= required_exp:
                score += 10
            elif self.profile.experience >= required_exp - 1:
                score += 5
        else:
            score += 10 # Assume match if not specified
        total_weight += 10

        return min(100, score)

def update_matches_for_user(user_id):
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return
        
    engine = MatchingEngine(profile)
    jobs = JobPost.query.all()
    
    for job in jobs:
        score = engine.calculate_score(job)
        if score > 50: # Only store meaningful matches
            existing_match = JobMatch.query.filter_by(user_id=user_id, job_id=job.id).first()
            if existing_match:
                existing_match.match_score = score
            else:
                match = JobMatch(user_id=user_id, job_id=job.id, match_score=score)
                db.session.add(match)
    
    db.session.commit()

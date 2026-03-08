import sys
# Force stdout to utf-8
sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from app.models import User, UserProfile, JobMatch, JobAlert, JobPost

def check_profile():
    app = create_app()
    with app.app_context():
        user = User.query.first()
        if not user:
            print("No users found.")
            return

        print(f"User: {user.email} (ID: {user.id})")
        
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        if profile:
            print(f"Preferred Roles: '{profile.preferred_roles}'")
            print(f"Skills: '{profile.skills}'")
            print(f"Preferred Locations: '{profile.preferred_locations}'")
        else:
            print("No profile found.")

        alerts = JobAlert.query.filter_by(user_id=user.id).all()
        print(f"Job Alerts ({len(alerts)}):")
        for a in alerts:
            print(f"- Name: {a.name}, Keywords: {a.keywords}")

        matches = JobMatch.query.filter_by(user_id=user.id).order_by(JobMatch.match_score.desc()).limit(5).all()
        print(f"Top 5 Matches:")
        for m in matches:
            job = db.session.get(JobPost, m.job_id)
            title = job.title if job else "Unknown"
            print(f"- Job ID: {m.job_id} | Score: {m.match_score} | Title: {title}")

if __name__ == "__main__":
    check_profile()

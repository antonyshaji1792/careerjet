from flask import Flask
import os
from dotenv import load_dotenv
from app.extensions import db, login_manager, migrate, csrf

load_dotenv()

def create_app():
    flask_app = Flask(__name__)
    flask_app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-12345')
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///careerjet.db')
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.url_map.strict_slashes = False

    db.init_app(flask_app)
    login_manager.init_app(flask_app)
    migrate.init_app(flask_app, db)
    csrf.init_app(flask_app)

    # Initialize Redis for rate limiting
    import redis
    from app import extensions
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    try:
        extensions.redis_client = redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        print(f"Warning: Failed to connect to Redis: {e}")
        extensions.redis_client = None

    from app.routes.subscription import bp as subscription_bp
    csrf.exempt(subscription_bp.name + '.webhook')

    # Import models early so they register with DB
    import app.models

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from app.routes import main, auth, dashboard, profile, jobs, subscription, linkedin, naukri, cover_letters, alerts, features, salary, admin, resumes, skill_gap_api, skill_gap_ui_api, profile_api, credits, contact
    from app.blueprints.resume import bp as resume_bp
    
    flask_app.register_blueprint(main.bp)
    flask_app.register_blueprint(auth.bp)
    flask_app.register_blueprint(dashboard.bp)
    flask_app.register_blueprint(profile.bp)
    flask_app.register_blueprint(jobs.bp)
    flask_app.register_blueprint(subscription.bp)
    flask_app.register_blueprint(linkedin.bp)
    flask_app.register_blueprint(naukri.bp)
    flask_app.register_blueprint(cover_letters.bp)
    flask_app.register_blueprint(alerts.bp)
    flask_app.register_blueprint(features.bp)
    flask_app.register_blueprint(salary.bp)
    flask_app.register_blueprint(admin.bp)
    flask_app.register_blueprint(resumes.bp)
    flask_app.register_blueprint(resume_bp)
    flask_app.register_blueprint(skill_gap_api.skill_gap_bp)
    flask_app.register_blueprint(skill_gap_ui_api.bp)
    flask_app.register_blueprint(profile_api.bp)
    flask_app.register_blueprint(credits.bp)
    flask_app.register_blueprint(contact.bp)

    from app.billing.routes.subscriptions import bp as billing_subscriptions_bp
    from app.billing.routes.webhooks import bp as billing_webhooks_bp
    from app.billing.routes.topups import bp as billing_topups_bp
    from app.billing.routes.overview import bp as billing_overview_bp
    from app.billing.routes.admin import bp as billing_admin_bp
    flask_app.register_blueprint(billing_subscriptions_bp)
    flask_app.register_blueprint(billing_webhooks_bp)
    flask_app.register_blueprint(billing_topups_bp)
    flask_app.register_blueprint(billing_overview_bp)
    flask_app.register_blueprint(billing_admin_bp)

    csrf.exempt(billing_webhooks_bp.name + '.razorpay_webhook')




    from app.routes import interview, video_interview
    flask_app.register_blueprint(interview.bp)
    flask_app.register_blueprint(video_interview.bp)


    @flask_app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        from flask import send_from_directory
        return send_from_directory(os.path.join(flask_app.root_path, '..', 'uploads'), filename)

    from app.commands import register_commands
    register_commands(flask_app)

    return flask_app



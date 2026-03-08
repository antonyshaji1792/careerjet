from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import (
    UserProfile, Resume, CoverLetter, Schedule, WebsitePreference,
    LinkedInCredentials, NaukriCredentials, AnswerCache,
    ProfileHeadline, KeySkill, ProfileSummary, PersonalDetails, CareerProfile, Employment
)
from app.forms import UserProfileForm, ScheduleForm
from app import db
import os
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('profile', __name__, url_prefix='/profile')

@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()
    form = UserProfileForm(obj=profile)
    if form.validate_on_submit():
        if not profile:
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)
        form.populate_obj(profile)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.index'))
    # Compute a simple completion percentage based on key sections
    try:
        checks = []
        keys = []
        # resume uploaded
        checks.append(1 if resume else 0); keys.append('resume')
        # headline
        checks.append(1 if ProfileHeadline.query.filter_by(user_id=current_user.id).first() else 0); keys.append('headline')
        # any skills
        checks.append(1 if KeySkill.query.filter_by(user_id=current_user.id).count() > 0 else 0); keys.append('skills')
        # personal details (name or phone)
        pd = PersonalDetails.query.filter_by(user_id=current_user.id).first()
        checks.append(1 if (pd and (pd.full_name or pd.phone)) else 0); keys.append('personal_details')
        # any employment
        checks.append(1 if Employment.query.filter_by(user_id=current_user.id).count() > 0 else 0); keys.append('employment')
        # summary
        checks.append(1 if ProfileSummary.query.filter_by(user_id=current_user.id).first() else 0); keys.append('summary')
        # career profile (salary / notice)
        checks.append(1 if CareerProfile.query.filter_by(user_id=current_user.id).first() else 0); keys.append('career_profile')

        total = len(checks)
        filled = sum(checks)
        completion = int(round((filled / total) * 100)) if total > 0 else 0
        missing_count = total - filled
        # find first missing key
        first_missing = None
        for k, v in zip(keys, checks):
            if v == 0:
                first_missing = k
                break
    except Exception:
        completion = 0
        missing_count = 0
        first_missing = None

    return render_template('profile/index.html', form=form, profile=profile, resume=resume, completion=completion, missing_count=missing_count, first_missing=first_missing)

@bp.route('/test-modals')
def test_modals():
    """Test page for CRUD modals - no login required"""
    return render_template('test_modals.html')


@bp.route('/resume', methods=['POST'])
@login_required
def upload_resume():
    if 'resume' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('profile.index'))
    file = request.files['resume']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('profile.index'))
    if file:
        filename = f"resume_{current_user.id}_{file.filename}"
        file_path = os.path.join('uploads', filename)
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        file.save(file_path)
        
        # Mark other resumes as not primary
        Resume.query.filter_by(user_id=current_user.id).update({Resume.is_primary: False})
        
        resume = Resume(user_id=current_user.id, file_path=file_path, is_primary=True)
        db.session.add(resume)
        db.session.commit()
        flash('Resume uploaded successfully and set as primary!', 'success')
        return redirect(url_for('profile.index'))

@bp.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    schedule = Schedule.query.filter_by(user_id=current_user.id).first()
    form = ScheduleForm()
    
    if request.method == 'GET' and schedule:
        form.daily_limit.data = schedule.daily_limit
        form.daily_search_limit.data = schedule.daily_search_limit
        form.is_autopilot_enabled.data = schedule.is_autopilot_enabled
        if schedule.preferred_days:
            form.preferred_days.data = [d.strip() for d in schedule.preferred_days.split(',')]
        if schedule.preferred_time and '-' in schedule.preferred_time:
            start, end = schedule.preferred_time.split('-')
            form.start_time.data = start
            form.end_time.data = end
            form.match_threshold.data = schedule.match_threshold
            
    if form.validate_on_submit():
        if not schedule:
            schedule = Schedule(user_id=current_user.id)
            db.session.add(schedule)
        
        schedule.daily_limit = form.daily_limit.data
        schedule.daily_search_limit = form.daily_search_limit.data
        schedule.is_autopilot_enabled = form.is_autopilot_enabled.data
        schedule.preferred_days = ','.join(form.preferred_days.data)
        schedule.preferred_time = f"{form.start_time.data}-{form.end_time.data}"
        schedule.match_threshold = form.match_threshold.data
        
        db.session.commit()
        flash('Schedule updated successfully!', 'success')
        return redirect(url_for('profile.schedule'))
    return render_template('profile/schedule.html', form=form, schedule=schedule)


@bp.route('/autofill', methods=['POST'])
@login_required
def autofill():
    """Autofill profile from the primary resume"""
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()
    if not resume:
        return jsonify({'success': False, 'message': 'No resume uploaded yet.'})

    try:
        from app.services.resume_parser import autofill_profile_from_resume
        import asyncio
        
        # In a real async app we wouldn't use asyncio.run here, 
        # but since Flask is sync, we bridge it for now.
        result = asyncio.run(autofill_profile_from_resume(resume.id))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Autofill error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error during autofill: {str(e)}'})

@bp.route('/debug-resume-parse', methods=['GET'])
@login_required
def debug_resume_parse():
    """Debug endpoint to see what's being extracted from resume"""
    from app.services.resume_parser import ResumeParserService
    import json
    
    # Get user's latest resume
    resume = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.uploaded_at.desc()).first()
    
    if not resume:
        return jsonify({'error': 'No resume found'}), 404
    
    # Parse the resume
    result = ResumeParserService.parse_resume_file(resume.file_path)
    
    if not result['success']:
        return jsonify({'error': result['message']}), 400
    
    # Return extracted data
    return jsonify({
        'success': True,
        'file_path': resume.file_path,
        'extracted_data': result['data'],
        'raw_text_preview': result['raw_text'][:500] + '...' if len(result['raw_text']) > 500 else result['raw_text']
    })



@bp.route('/websites', methods=['GET', 'POST'])
@login_required
def websites():
    # Define available job platforms
    available_platforms = [
        {'name': 'LinkedIn', 'icon': '💼'},
        {'name': 'Indeed', 'icon': '🔍'},
        {'name': 'Naukri', 'icon': '🇮🇳'},
        {'name': 'Monster', 'icon': '👹'},
        {'name': 'Glassdoor', 'icon': '🚪'},
        {'name': 'AngelList', 'icon': '👼'},
        {'name': 'Dice', 'icon': '🎲'},
        {'name': 'CareerBuilder', 'icon': '🏗️'},
        {'name': 'ZipRecruiter', 'icon': '📮'},
        {'name': 'SimplyHired', 'icon': '✅'},
    ]
    
    if request.method == 'POST':
        # Get selected platforms from form
        selected_platforms = request.form.getlist('platforms')
        
        # Delete all existing preferences for this user
        WebsitePreference.query.filter_by(user_id=current_user.id).delete()
        
        # Add new preferences
        for platform in available_platforms:
            is_enabled = platform['name'] in selected_platforms
            preference = WebsitePreference(
                user_id=current_user.id,
                platform_name=platform['name'],
                is_enabled=is_enabled
            )
            db.session.add(preference)
        
        db.session.commit()
        flash('Website preferences updated successfully!', 'success')
        return redirect(url_for('profile.websites'))
    
    # Get current preferences
    current_preferences = WebsitePreference.query.filter_by(user_id=current_user.id).all()
    enabled_platforms = {pref.platform_name for pref in current_preferences if pref.is_enabled}
    
    # If no preferences exist, enable all by default
    if not current_preferences:
        enabled_platforms = {platform['name'] for platform in available_platforms}
    
    return render_template('profile/websites.html', 
                         platforms=available_platforms, 
                         enabled_platforms=enabled_platforms)

@bp.route('/test-connection/<portal>', methods=['POST'])
@login_required
def test_connection(portal):
    """Test connection for a specific job portal"""
    portal = portal.lower()
    
    # Check for specific portal logic or generic one
    if portal == 'linkedin':
        from app.routes.linkedin import test_connection as linkedin_test
        return linkedin_test()
    elif portal == 'naukri':
        from app.routes.naukri import test_connection as naukri_test
        return naukri_test()
    
    # Generic placeholder for others
    # In a real implementation, we would call the specific scraper's login method
    try:
        from app.models import PlatformCredential
        creds = PlatformCredential.query.filter_by(user_id=current_user.id, platform=portal).first()
        if not creds:
            return jsonify({'success': False, 'message': f'No credentials found for {portal.capitalize()}'})
        
        # Simulating a successful login for now as we haven't built all scrapers yet
        # But we'll at least verify the credentials exist
        creds.last_login = db.func.now()
        db.session.commit()
        return jsonify({'success': True, 'message': f'Simulated connection to {portal.capitalize()} successful!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Test failed: {str(e)}'})

@bp.route('/test-ai-connection/<provider>', methods=['POST'])
@login_required
def test_ai_connection(provider):
    """Test connection for a specific AI provider"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required.'}), 403
        
    data = request.json
    api_key = data.get('api_key')
    model = data.get('model')
    
    # Handle '********' placeholder (if user didn't change it, fetch from DB)
    if api_key == '********':
        from app.models import SystemConfig
        key_name = f'{provider.upper()}_API_KEY'
        api_key = SystemConfig.get_config_value(key_name)
        if provider == 'ollama':
             api_key = SystemConfig.get_config_value('OLLAMA_BASE_URL')

    try:
        from app.services.llm_service import ask_ai
        import asyncio
        
        # Test prompt
        test_prompt = "Say 'Connection Successful' in exactly 2 words."
        
        # Run the AI call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(ask_ai(
            prompt=test_prompt,
            provider_override=provider,
            credentials_override={'api_key': api_key, 'model': model}
        ))
        
        if result and len(result) > 0:
            return jsonify({
                'success': True, 
                'message': f'Connection verified! Response: "{result}"'
            })
        else:
            return jsonify({'success': False, 'message': 'Received empty response from provider.'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Connection failed: {str(e)}'})

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    from app.models import PlatformCredential, SystemConfig
    
    available_platforms = [
        {'id': 'linkedin', 'name': 'LinkedIn', 'icon': 'fab fa-linkedin', 'color': '#0284c7', 'bg': '#e0f2fe'},
        {'id': 'naukri', 'name': 'Naukri.com', 'icon': 'fas fa-briefcase', 'color': '#ea580c', 'bg': '#fff7ed'},
        {'id': 'indeed', 'name': 'Indeed', 'icon': 'fas fa-search', 'color': '#2557a7', 'bg': '#e8f0fe'},
    ]
    
    # Fetch job portal credentials
    creds_dict = {}
    creds_dict['linkedin'] = LinkedInCredentials.query.filter_by(user_id=current_user.id).first()
    creds_dict['naukri'] = NaukriCredentials.query.filter_by(user_id=current_user.id).first()
    
    universal_creds = PlatformCredential.query.filter_by(user_id=current_user.id).all()
    for c in universal_creds:
        creds_dict[c.platform.lower()] = c

    # Fetch LLM configs for admins
    llm_configs = {}
    if current_user.is_admin:
        providers = ['OPENAI', 'ANTHROPIC', 'GEMINI', 'OLLAMA', 'OPENROUTER', 'GROQ', 'MISTRAL']
        llm_configs['PRIMARY_LLM_PROVIDER'] = SystemConfig.get_config_value('PRIMARY_LLM_PROVIDER', 'openai')
        for p in providers:
            llm_configs[f'{p}_IS_ACTIVE'] = SystemConfig.get_config_value(f'{p}_IS_ACTIVE', 'true') == 'true'
            key_name = f'{p}_API_KEY'
            
            # Fetch Models
            llm_configs[f'{p}_MODEL'] = SystemConfig.get_config_value(f'{p}_MODEL', 
                'gpt-4o' if p == 'OPENAI' else 
                'claude-3-5-sonnet-20240620' if p == 'ANTHROPIC' else 
                'gemini-1.5-flash' if p == 'GEMINI' else 
                'anthropic/claude-3.5-sonnet' if p == 'OPENROUTER' else
                'llama3-70b-8192' if p == 'GROQ' else
                'mistral-large-latest' if p == 'MISTRAL' else 'llama3')
            
            if p == 'OLLAMA':
                llm_configs['OLLAMA_BASE_URL'] = SystemConfig.get_config_value('OLLAMA_BASE_URL', 'http://localhost:11434')
            elif p == 'OPENROUTER':
                llm_configs['OPENROUTER_REFERER'] = SystemConfig.get_config_value('OPENROUTER_REFERER', 'https://careerjet.ai')
                llm_configs['OPENROUTER_TITLE'] = SystemConfig.get_config_value('OPENROUTER_TITLE', 'CareerJet AI')
                raw_val = SystemConfig.get_config_value(key_name)
                llm_configs[key_name] = '********' if raw_val else ''
            else:
                raw_val = SystemConfig.get_config_value(key_name)
                llm_configs[key_name] = '********' if raw_val else ''

    from app.models import PlatformCredential
    
    # Fetch all credentials
    creds_dict = {}
    
    # Specific ones
    creds_dict['linkedin'] = LinkedInCredentials.query.filter_by(user_id=current_user.id).first()
    creds_dict['naukri'] = NaukriCredentials.query.filter_by(user_id=current_user.id).first()
    
    # Universal ones
    universal_creds = PlatformCredential.query.filter_by(user_id=current_user.id).all()
    for c in universal_creds:
        creds_dict[c.platform.lower()] = c

    if request.method == 'POST':
        portal = request.form.get('portal').lower()
        email = request.form.get('email')
        password = request.form.get('password')
        
        if portal == 'linkedin':
            creds = LinkedInCredentials.query.filter_by(user_id=current_user.id).first()
            if not creds:
                creds = LinkedInCredentials(user_id=current_user.id, email=email)
                db.session.add(creds)
            else:
                creds.email = email
            creds.set_password(password)
            creds.is_active = True
        elif portal == 'naukri':
            creds = NaukriCredentials.query.filter_by(user_id=current_user.id).first()
            if not creds:
                creds = NaukriCredentials(user_id=current_user.id, email=email)
                db.session.add(creds)
            else:
                creds.email = email
            creds.set_password(password)
            creds.is_active = True
        else:
            # Universal platforms
            creds = PlatformCredential.query.filter_by(user_id=current_user.id, platform=portal).first()
            if not creds:
                creds = PlatformCredential(user_id=current_user.id, platform=portal, email=email)
                db.session.add(creds)
            else:
                creds.email = email
            creds.set_password(password)
            creds.is_active = True
            
        db.session.commit()
        flash(f'{portal.capitalize()} credentials updated!', 'success')
        return redirect(url_for('profile.settings'))
        
    return render_template('profile/settings.html', 
                         platforms=available_platforms,
                         creds=creds_dict,
                         llm_configs=llm_configs)

@bp.route('/settings/llm', methods=['POST'])
@login_required
def save_llm_settings():
    if not current_user.is_admin:
        flash('Admin access required for AI settings.', 'danger')
        return redirect(url_for('profile.settings'))
        
    from app.models import SystemConfig
    
    # Save primary provider
    primary = request.form.get('PRIMARY_LLM_PROVIDER')
    if primary:
        SystemConfig.set_config_value('PRIMARY_LLM_PROVIDER', primary)
        
    # Save providers info
    providers = ['OPENAI', 'ANTHROPIC', 'GEMINI', 'OLLAMA', 'OPENROUTER', 'GROQ', 'MISTRAL']
    for p in providers:
        # Active toggle
        is_active = request.form.get(f'{p}_IS_ACTIVE') == 'on'
        SystemConfig.set_config_value(f'{p}_IS_ACTIVE', 'true' if is_active else 'false')
        
        # Model Name
        model_val = request.form.get(f'{p}_MODEL')
        if model_val:
            SystemConfig.set_config_value(f'{p}_MODEL', model_val)
            
        # Keys
        key_name = f'{p}_API_KEY'
        val = request.form.get(key_name)
        if val is not None and val != '********':
             SystemConfig.set_config_value(key_name, val, is_encrypted=True)
             
        # Provider specifics
        if p == 'OLLAMA':
            SystemConfig.set_config_value('OLLAMA_BASE_URL', request.form.get('OLLAMA_BASE_URL', 'http://localhost:11434'))
        elif p == 'OPENROUTER':
            SystemConfig.set_config_value('OPENROUTER_REFERER', request.form.get('OPENROUTER_REFERER', 'https://careerjet.ai'))
            SystemConfig.set_config_value('OPENROUTER_TITLE', request.form.get('OPENROUTER_TITLE', 'CareerJet AI'))
            
    flash('AI configuration updated globally.', 'success')
    return redirect(url_for('profile.settings') + '#ai')

@bp.route('/answers', methods=['GET', 'POST'])
@login_required
def answers():
    if request.method == 'POST':
        question_id = request.form.get('id')
        new_answer = request.form.get('answer')
        
        if question_id and new_answer:
            answer_obj = AnswerCache.query.filter_by(id=question_id, user_id=current_user.id).first()
            if answer_obj:
                answer_obj.answer_text = new_answer
                db.session.commit()
                flash('Answer updated!', 'success')
            else:
                flash('Answer not found.', 'danger')
        return redirect(url_for('profile.answers'))

    all_answers = AnswerCache.query.filter_by(user_id=current_user.id).order_by(AnswerCache.last_used_at.desc(), AnswerCache.created_at.desc()).all()
    return render_template('profile/answers.html', answers=all_answers)

@bp.route('/answers/delete/<int:answer_id>', methods=['POST'])
@login_required
def delete_answer(answer_id):
    answer_obj = AnswerCache.query.filter_by(id=answer_id, user_id=current_user.id).first()
    if answer_obj:
        db.session.delete(answer_obj)
        db.session.commit()
        flash('Answer removed.', 'success')
    else:
        flash('Answer not found.', 'danger')
    return redirect(url_for('profile.answers'))

@bp.route('/answers/clear', methods=['POST'])
@login_required
def clear_answers():
    AnswerCache.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All saved answers cleared.', 'success')
    return redirect(url_for('profile.answers'))

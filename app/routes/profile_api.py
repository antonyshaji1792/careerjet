"""
Profile API routes for CRUD operations on all profile sections
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import (
    ProfileHeadline, KeySkill, Employment, Education, ITSkill,
    Project, ProfileSummary, Accomplishment, PersonalDetails,
    Language, DiversityInfo, CareerProfile, UserProfile
)
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from pathlib import Path

bp = Blueprint('profile_api', __name__, url_prefix='/api/profile')

# ============ PROFILE HEADLINE ============
@bp.route('/headline', methods=['GET'])
@login_required
def get_headline():
    headline = ProfileHeadline.query.filter_by(user_id=current_user.id).first()
    if headline:
        return jsonify({'success': True, 'data': {'id': headline.id, 'headline': headline.headline}})
    return jsonify({'success': True, 'data': None})

@bp.route('/headline', methods=['POST', 'PUT'])
@login_required
def save_headline():
    data = request.json
    headline = ProfileHeadline.query.filter_by(user_id=current_user.id).first()
    
    if headline:
        headline.headline = data.get('headline')
        headline.updated_at = datetime.utcnow()
    else:
        headline = ProfileHeadline(user_id=current_user.id, headline=data.get('headline'))
        db.session.add(headline)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Headline updated successfully', 'data': {'id': headline.id}})

# ============ KEY SKILLS ============
@bp.route('/skills', methods=['GET'])
@login_required
def get_skills():
    skills = KeySkill.query.filter_by(user_id=current_user.id).all()
    return jsonify({'success': True, 'data': [{'id': s.id, 'skill_name': s.skill_name} for s in skills]})

@bp.route('/skills', methods=['POST'])
@login_required
def add_skill():
    data = request.json
    skill = KeySkill(user_id=current_user.id, skill_name=data.get('skill_name'))
    db.session.add(skill)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Skill added successfully', 'data': {'id': skill.id}})

@bp.route('/skills/<int:skill_id>', methods=['DELETE'])
@login_required
def delete_skill(skill_id):
    skill = KeySkill.query.filter_by(id=skill_id, user_id=current_user.id).first()
    if skill:
        db.session.delete(skill)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Skill deleted successfully'})
    return jsonify({'success': False, 'message': 'Skill not found'}), 404

# ============ EMPLOYMENT ============
@bp.route('/employment', methods=['GET'])
@login_required
def get_employments():
    employments = Employment.query.filter_by(user_id=current_user.id).order_by(Employment.start_date.desc()).all()
    data = []
    for emp in employments:
        data.append({
            'id': emp.id,
            'job_title': emp.job_title,
            'company_name': emp.company_name,
            'employment_type': emp.employment_type,
            'start_date': emp.start_date.isoformat() if emp.start_date else None,
            'end_date': emp.end_date.isoformat() if emp.end_date else None,
            'is_current': emp.is_current,
            'is_serving_notice': emp.is_serving_notice,
            'notice_period_days': emp.notice_period_days,
            'description': emp.description,
            'key_skills': emp.key_skills
        })
    return jsonify({'success': True, 'data': data})

@bp.route('/employment', methods=['POST'])
@login_required
def add_employment():
    data = request.json
    emp = Employment(
        user_id=current_user.id,
        job_title=data.get('job_title'),
        company_name=data.get('company_name'),
        employment_type=data.get('employment_type'),
        start_date=datetime.fromisoformat(data.get('start_date')) if data.get('start_date') else None,
        end_date=datetime.fromisoformat(data.get('end_date')) if data.get('end_date') else None,
        is_current=data.get('is_current', False),
        is_serving_notice=data.get('is_serving_notice', False),
        notice_period_days=data.get('notice_period_days'),
        description=data.get('description'),
        key_skills=data.get('key_skills')
    )
    db.session.add(emp)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Employment added successfully', 'data': {'id': emp.id}})

@bp.route('/employment/<int:emp_id>', methods=['PUT'])
@login_required
def update_employment(emp_id):
    emp = Employment.query.filter_by(id=emp_id, user_id=current_user.id).first()
    if not emp:
        return jsonify({'success': False, 'message': 'Employment not found'}), 404
    
    data = request.json
    emp.job_title = data.get('job_title', emp.job_title)
    emp.company_name = data.get('company_name', emp.company_name)
    emp.employment_type = data.get('employment_type', emp.employment_type)
    emp.start_date = datetime.fromisoformat(data.get('start_date')) if data.get('start_date') else emp.start_date
    emp.end_date = datetime.fromisoformat(data.get('end_date')) if data.get('end_date') else emp.end_date
    emp.is_current = data.get('is_current', emp.is_current)
    emp.is_serving_notice = data.get('is_serving_notice', emp.is_serving_notice)
    emp.notice_period_days = data.get('notice_period_days', emp.notice_period_days)
    emp.description = data.get('description', emp.description)
    emp.key_skills = data.get('key_skills', emp.key_skills)
    emp.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Employment updated successfully'})

@bp.route('/employment/<int:emp_id>', methods=['DELETE'])
@login_required
def delete_employment(emp_id):
    emp = Employment.query.filter_by(id=emp_id, user_id=current_user.id).first()
    if emp:
        db.session.delete(emp)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Employment deleted successfully'})
    return jsonify({'success': False, 'message': 'Employment not found'}), 404

# ============ EDUCATION ============
@bp.route('/education', methods=['GET'])
@login_required
def get_educations():
    educations = Education.query.filter_by(user_id=current_user.id).order_by(Education.end_year.desc()).all()
    data = []
    for edu in educations:
        data.append({
            'id': edu.id,
            'degree': edu.degree,
            'institution': edu.institution,
            'field_of_study': edu.field_of_study,
            'start_year': edu.start_year,
            'end_year': edu.end_year,
            'grade': edu.grade,
            'education_type': edu.education_type
        })
    return jsonify({'success': True, 'data': data})

@bp.route('/education', methods=['POST'])
@login_required
def add_education():
    data = request.json
    edu = Education(
        user_id=current_user.id,
        degree=data.get('degree'),
        institution=data.get('institution'),
        field_of_study=data.get('field_of_study'),
        start_year=data.get('start_year'),
        end_year=data.get('end_year'),
        grade=data.get('grade'),
        education_type=data.get('education_type')
    )
    db.session.add(edu)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Education added successfully', 'data': {'id': edu.id}})

@bp.route('/education/<int:edu_id>', methods=['PUT'])
@login_required
def update_education(edu_id):
    edu = Education.query.filter_by(id=edu_id, user_id=current_user.id).first()
    if not edu:
        return jsonify({'success': False, 'message': 'Education not found'}), 404
    
    data = request.json
    edu.degree = data.get('degree', edu.degree)
    edu.institution = data.get('institution', edu.institution)
    edu.field_of_study = data.get('field_of_study', edu.field_of_study)
    edu.start_year = data.get('start_year', edu.start_year)
    edu.end_year = data.get('end_year', edu.end_year)
    edu.grade = data.get('grade', edu.grade)
    edu.education_type = data.get('education_type', edu.education_type)
    edu.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Education updated successfully'})

@bp.route('/education/<int:edu_id>', methods=['DELETE'])
@login_required
def delete_education(edu_id):
    edu = Education.query.filter_by(id=edu_id, user_id=current_user.id).first()
    if edu:
        db.session.delete(edu)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Education deleted successfully'})
    return jsonify({'success': False, 'message': 'Education not found'}), 404

# ============ IT SKILLS ============
@bp.route('/it-skills', methods=['GET'])
@login_required
def get_it_skills():
    skills = ITSkill.query.filter_by(user_id=current_user.id).all()
    data = []
    for skill in skills:
        data.append({
            'id': skill.id,
            'skill_name': skill.skill_name,
            'version': skill.version,
            'last_used_year': skill.last_used_year,
            'experience_years': skill.experience_years,
            'experience_months': skill.experience_months
        })
    return jsonify({'success': True, 'data': data})

@bp.route('/it-skills', methods=['POST'])
@login_required
def add_it_skill():
    data = request.json
    skill = ITSkill(
        user_id=current_user.id,
        skill_name=data.get('skill_name'),
        version=data.get('version'),
        last_used_year=data.get('last_used_year'),
        experience_years=data.get('experience_years'),
        experience_months=data.get('experience_months')
    )
    db.session.add(skill)
    db.session.commit()
    return jsonify({'success': True, 'message': 'IT Skill added successfully', 'data': {'id': skill.id}})

@bp.route('/it-skills/<int:skill_id>', methods=['PUT'])
@login_required
def update_it_skill(skill_id):
    skill = ITSkill.query.filter_by(id=skill_id, user_id=current_user.id).first()
    if not skill:
        return jsonify({'success': False, 'message': 'IT Skill not found'}), 404
    
    data = request.json
    skill.skill_name = data.get('skill_name', skill.skill_name)
    skill.version = data.get('version', skill.version)
    skill.last_used_year = data.get('last_used_year', skill.last_used_year)
    skill.experience_years = data.get('experience_years', skill.experience_years)
    skill.experience_months = data.get('experience_months', skill.experience_months)
    skill.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'IT Skill updated successfully'})

@bp.route('/it-skills/<int:skill_id>', methods=['DELETE'])
@login_required
def delete_it_skill(skill_id):
    skill = ITSkill.query.filter_by(id=skill_id, user_id=current_user.id).first()
    if skill:
        db.session.delete(skill)
        db.session.commit()
        return jsonify({'success': True, 'message': 'IT Skill deleted successfully'})
    return jsonify({'success': False, 'message': 'IT Skill not found'}), 404

# ============ PROJECTS ============
@bp.route('/projects', methods=['GET'])
@login_required
def get_projects():
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.start_date.desc()).all()
    data = []
    for proj in projects:
        data.append({
            'id': proj.id,
            'title': proj.title,
            'client': proj.client,
            'project_status': proj.project_status,
            'start_date': proj.start_date.isoformat() if proj.start_date else None,
            'end_date': proj.end_date.isoformat() if proj.end_date else None,
            'description': proj.description,
            'role': proj.role,
            'team_size': proj.team_size,
            'skills_used': proj.skills_used,
            'project_url': proj.project_url
        })
    return jsonify({'success': True, 'data': data})

@bp.route('/projects', methods=['POST'])
@login_required
def add_project():
    data = request.json
    proj = Project(
        user_id=current_user.id,
        title=data.get('title'),
        client=data.get('client'),
        project_status=data.get('project_status'),
        start_date=datetime.fromisoformat(data.get('start_date')) if data.get('start_date') else None,
        end_date=datetime.fromisoformat(data.get('end_date')) if data.get('end_date') else None,
        description=data.get('description'),
        role=data.get('role'),
        team_size=data.get('team_size'),
        skills_used=data.get('skills_used'),
        project_url=data.get('project_url')
    )
    db.session.add(proj)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Project added successfully', 'data': {'id': proj.id}})

@bp.route('/projects/<int:proj_id>', methods=['PUT'])
@login_required
def update_project(proj_id):
    proj = Project.query.filter_by(id=proj_id, user_id=current_user.id).first()
    if not proj:
        return jsonify({'success': False, 'message': 'Project not found'}), 404
    
    data = request.json
    proj.title = data.get('title', proj.title)
    proj.client = data.get('client', proj.client)
    proj.project_status = data.get('project_status', proj.project_status)
    proj.start_date = datetime.fromisoformat(data.get('start_date')) if data.get('start_date') else proj.start_date
    proj.end_date = datetime.fromisoformat(data.get('end_date')) if data.get('end_date') else proj.end_date
    proj.description = data.get('description', proj.description)
    proj.role = data.get('role', proj.role)
    proj.team_size = data.get('team_size', proj.team_size)
    proj.skills_used = data.get('skills_used', proj.skills_used)
    proj.project_url = data.get('project_url', proj.project_url)
    proj.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Project updated successfully'})

@bp.route('/projects/<int:proj_id>', methods=['DELETE'])
@login_required
def delete_project(proj_id):
    proj = Project.query.filter_by(id=proj_id, user_id=current_user.id).first()
    if proj:
        db.session.delete(proj)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Project deleted successfully'})
    return jsonify({'success': False, 'message': 'Project not found'}), 404

# ============ PROFILE SUMMARY ============
@bp.route('/summary', methods=['GET'])
@login_required
def get_summary():
    summary = ProfileSummary.query.filter_by(user_id=current_user.id).first()
    if summary:
        return jsonify({'success': True, 'data': {'id': summary.id, 'summary': summary.summary}})
    return jsonify({'success': True, 'data': None})

@bp.route('/summary', methods=['POST', 'PUT'])
@login_required
def save_summary():
    data = request.json
    summary = ProfileSummary.query.filter_by(user_id=current_user.id).first()
    
    if summary:
        summary.summary = data.get('summary')
        summary.updated_at = datetime.utcnow()
    else:
        summary = ProfileSummary(user_id=current_user.id, summary=data.get('summary'))
        db.session.add(summary)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Summary updated successfully', 'data': {'id': summary.id}})

# ============ ACCOMPLISHMENTS ============
@bp.route('/accomplishments', methods=['GET'])
@login_required
def get_accomplishments():
    accomplishments = Accomplishment.query.filter_by(user_id=current_user.id).all()
    data = []
    for acc in accomplishments:
        data.append({
            'id': acc.id,
            'type': acc.type,
            'title': acc.title,
            'url': acc.url,
            'description': acc.description,
            'issued_by': acc.issued_by,
            'issued_date': acc.issued_date.isoformat() if acc.issued_date else None
        })
    return jsonify({'success': True, 'data': data})

@bp.route('/accomplishments', methods=['POST'])
@login_required
def add_accomplishment():
    data = request.json
    acc = Accomplishment(
        user_id=current_user.id,
        type=data.get('type'),
        title=data.get('title'),
        url=data.get('url'),
        description=data.get('description'),
        issued_by=data.get('issued_by'),
        issued_date=datetime.fromisoformat(data.get('issued_date')) if data.get('issued_date') else None
    )
    db.session.add(acc)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Accomplishment added successfully', 'data': {'id': acc.id}})

@bp.route('/accomplishments/<int:acc_id>', methods=['PUT'])
@login_required
def update_accomplishment(acc_id):
    acc = Accomplishment.query.filter_by(id=acc_id, user_id=current_user.id).first()
    if not acc:
        return jsonify({'success': False, 'message': 'Accomplishment not found'}), 404
    
    data = request.json
    acc.type = data.get('type', acc.type)
    acc.title = data.get('title', acc.title)
    acc.url = data.get('url', acc.url)
    acc.description = data.get('description', acc.description)
    acc.issued_by = data.get('issued_by', acc.issued_by)
    acc.issued_date = datetime.fromisoformat(data.get('issued_date')) if data.get('issued_date') else acc.issued_date
    acc.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Accomplishment updated successfully'})

@bp.route('/accomplishments/<int:acc_id>', methods=['DELETE'])
@login_required
def delete_accomplishment(acc_id):
    acc = Accomplishment.query.filter_by(id=acc_id, user_id=current_user.id).first()
    if acc:
        db.session.delete(acc)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Accomplishment deleted successfully'})
    return jsonify({'success': False, 'message': 'Accomplishment not found'}), 404

# ============ PERSONAL DETAILS ============
@bp.route('/personal-details', methods=['GET'])
@login_required
def get_personal_details():
    details = PersonalDetails.query.filter_by(user_id=current_user.id).first()
    if details:
        return jsonify({'success': True, 'data': {
            'id': details.id,
            'full_name': details.full_name,
            'gender': details.gender,
            'marital_status': details.marital_status,
            'date_of_birth': details.date_of_birth.isoformat() if details.date_of_birth else None,
            'category': details.category,
            'work_permit_country': details.work_permit_country,
            'address': details.address,
            'city': details.city,
            'state': details.state,
            'country': details.country,
            'pincode': details.pincode,
            'phone': details.phone,
            'alternate_phone': details.alternate_phone
        }})
    return jsonify({'success': True, 'data': None})

@bp.route('/personal-details', methods=['POST', 'PUT'])
@login_required
def save_personal_details():
    data = request.json
    details = PersonalDetails.query.filter_by(user_id=current_user.id).first()
    
    if details:
        details.full_name = data.get('full_name', details.full_name)
        details.gender = data.get('gender', details.gender)
        details.marital_status = data.get('marital_status', details.marital_status)
        details.date_of_birth = datetime.fromisoformat(data.get('date_of_birth')) if data.get('date_of_birth') else details.date_of_birth
        details.category = data.get('category', details.category)
        details.work_permit_country = data.get('work_permit_country', details.work_permit_country)
        details.address = data.get('address', details.address)
        details.city = data.get('city', details.city)
        details.state = data.get('state', details.state)
        details.country = data.get('country', details.country)
        details.pincode = data.get('pincode', details.pincode)
        details.phone = data.get('phone', details.phone)
        details.alternate_phone = data.get('alternate_phone', details.alternate_phone)
        details.updated_at = datetime.utcnow()
    else:
        details = PersonalDetails(
            user_id=current_user.id,
            full_name=data.get('full_name'),
            gender=data.get('gender'),
            marital_status=data.get('marital_status'),
            date_of_birth=datetime.fromisoformat(data.get('date_of_birth')) if data.get('date_of_birth') else None,
            category=data.get('category'),
            work_permit_country=data.get('work_permit_country'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            country=data.get('country'),
            pincode=data.get('pincode'),
            phone=data.get('phone'),
            alternate_phone=data.get('alternate_phone')
        )
        db.session.add(details)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Personal details updated successfully', 'data': {'id': details.id}})

# ============ LANGUAGES ============
@bp.route('/languages', methods=['GET'])
@login_required
def get_languages():
    languages = Language.query.filter_by(user_id=current_user.id).all()
    data = []
    for lang in languages:
        data.append({
            'id': lang.id,
            'language_name': lang.language_name,
            'proficiency': lang.proficiency,
            'can_read': lang.can_read,
            'can_write': lang.can_write,
            'can_speak': lang.can_speak
        })
    return jsonify({'success': True, 'data': data})

@bp.route('/languages', methods=['POST'])
@login_required
def add_language():
    data = request.json
    lang = Language(
        user_id=current_user.id,
        language_name=data.get('language_name'),
        proficiency=data.get('proficiency'),
        can_read=data.get('can_read', False),
        can_write=data.get('can_write', False),
        can_speak=data.get('can_speak', False)
    )
    db.session.add(lang)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Language added successfully', 'data': {'id': lang.id}})

@bp.route('/languages/<int:lang_id>', methods=['PUT'])
@login_required
def update_language(lang_id):
    lang = Language.query.filter_by(id=lang_id, user_id=current_user.id).first()
    if not lang:
        return jsonify({'success': False, 'message': 'Language not found'}), 404
    
    data = request.json
    lang.language_name = data.get('language_name', lang.language_name)
    lang.proficiency = data.get('proficiency', lang.proficiency)
    lang.can_read = data.get('can_read', lang.can_read)
    lang.can_write = data.get('can_write', lang.can_write)
    lang.can_speak = data.get('can_speak', lang.can_speak)
    lang.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Language updated successfully'})

@bp.route('/languages/<int:lang_id>', methods=['DELETE'])
@login_required
def delete_language(lang_id):
    lang = Language.query.filter_by(id=lang_id, user_id=current_user.id).first()
    if lang:
        db.session.delete(lang)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Language deleted successfully'})
    return jsonify({'success': False, 'message': 'Language not found'}), 404

# ============ DIVERSITY INFO ============
@bp.route('/diversity', methods=['GET'])
@login_required
def get_diversity():
    diversity = DiversityInfo.query.filter_by(user_id=current_user.id).first()
    if diversity:
        return jsonify({'success': True, 'data': {
            'id': diversity.id,
            'has_disability': diversity.has_disability,
            'disability_type': diversity.disability_type,
            'has_military_experience': diversity.has_military_experience,
            'military_branch': diversity.military_branch,
            'military_start_date': diversity.military_start_date.isoformat() if diversity.military_start_date else None,
            'military_end_date': diversity.military_end_date.isoformat() if diversity.military_end_date else None,
            'has_career_break': diversity.has_career_break,
            'career_break_reason': diversity.career_break_reason,
            'career_break_start_date': diversity.career_break_start_date.isoformat() if diversity.career_break_start_date else None,
            'career_break_end_date': diversity.career_break_end_date.isoformat() if diversity.career_break_end_date else None
        }})
    return jsonify({'success': True, 'data': None})

@bp.route('/diversity', methods=['POST', 'PUT'])
@login_required
def save_diversity():
    data = request.json
    diversity = DiversityInfo.query.filter_by(user_id=current_user.id).first()
    
    if diversity:
        diversity.has_disability = data.get('has_disability', diversity.has_disability)
        diversity.disability_type = data.get('disability_type', diversity.disability_type)
        diversity.has_military_experience = data.get('has_military_experience', diversity.has_military_experience)
        diversity.military_branch = data.get('military_branch', diversity.military_branch)
        diversity.military_start_date = datetime.fromisoformat(data.get('military_start_date')) if data.get('military_start_date') else diversity.military_start_date
        diversity.military_end_date = datetime.fromisoformat(data.get('military_end_date')) if data.get('military_end_date') else diversity.military_end_date
        diversity.has_career_break = data.get('has_career_break', diversity.has_career_break)
        diversity.career_break_reason = data.get('career_break_reason', diversity.career_break_reason)
        diversity.career_break_start_date = datetime.fromisoformat(data.get('career_break_start_date')) if data.get('career_break_start_date') else diversity.career_break_start_date
        diversity.career_break_end_date = datetime.fromisoformat(data.get('career_break_end_date')) if data.get('career_break_end_date') else diversity.career_break_end_date
        diversity.updated_at = datetime.utcnow()
    else:
        diversity = DiversityInfo(
            user_id=current_user.id,
            has_disability=data.get('has_disability', False),
            disability_type=data.get('disability_type'),
            has_military_experience=data.get('has_military_experience', False),
            military_branch=data.get('military_branch'),
            military_start_date=datetime.fromisoformat(data.get('military_start_date')) if data.get('military_start_date') else None,
            military_end_date=datetime.fromisoformat(data.get('military_end_date')) if data.get('military_end_date') else None,
            has_career_break=data.get('has_career_break', False),
            career_break_reason=data.get('career_break_reason'),
            career_break_start_date=datetime.fromisoformat(data.get('career_break_start_date')) if data.get('career_break_start_date') else None,
            career_break_end_date=datetime.fromisoformat(data.get('career_break_end_date')) if data.get('career_break_end_date') else None
        )
        db.session.add(diversity)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Diversity information updated successfully', 'data': {'id': diversity.id}})

# ============ CAREER PROFILE ============
@bp.route('/career-profile', methods=['GET'])
@login_required
def get_career_profile():
    career = CareerProfile.query.filter_by(user_id=current_user.id).first()
    if career:
        return jsonify({'success': True, 'data': {
            'id': career.id,
            'current_industry': career.current_industry,
            'preferred_industries': career.preferred_industries,
            'current_salary': career.current_salary,
            'expected_salary': career.expected_salary,
            'preferred_shift': career.preferred_shift,
            'preferred_employment_type': career.preferred_employment_type,
            'willing_to_relocate': career.willing_to_relocate,
            'preferred_work_location': career.preferred_work_location,
            'notice_period_days': career.notice_period_days
        }})
    return jsonify({'success': True, 'data': None})

@bp.route('/career-profile', methods=['POST', 'PUT'])
@login_required
def save_career_profile():
    data = request.json
    career = CareerProfile.query.filter_by(user_id=current_user.id).first()
    
    if career:
        career.current_industry = data.get('current_industry', career.current_industry)
        career.preferred_industries = data.get('preferred_industries', career.preferred_industries)
        career.current_salary = data.get('current_salary', career.current_salary)
        career.expected_salary = data.get('expected_salary', career.expected_salary)
        career.preferred_shift = data.get('preferred_shift', career.preferred_shift)
        career.preferred_employment_type = data.get('preferred_employment_type', career.preferred_employment_type)
        career.willing_to_relocate = data.get('willing_to_relocate', career.willing_to_relocate)
        career.preferred_work_location = data.get('preferred_work_location', career.preferred_work_location)
        career.notice_period_days = data.get('notice_period_days', career.notice_period_days)
        career.updated_at = datetime.utcnow()
    else:
        career = CareerProfile(
            user_id=current_user.id,
            current_industry=data.get('current_industry'),
            preferred_industries=data.get('preferred_industries'),
            current_salary=data.get('current_salary'),
            expected_salary=data.get('expected_salary'),
            preferred_shift=data.get('preferred_shift'),
            preferred_employment_type=data.get('preferred_employment_type'),
            willing_to_relocate=data.get('willing_to_relocate', False),
            preferred_work_location=data.get('preferred_work_location'),
            notice_period_days=data.get('notice_period_days')
        )
        db.session.add(career)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Career profile updated successfully', 'data': {'id': career.id}})

# ============ BASIC INFO (HEADER) ============
@bp.route('/basic-info', methods=['GET'])
@login_required
def get_basic_info():
    # Fetch all necessary records
    pd = PersonalDetails.query.filter_by(user_id=current_user.id).first()
    curr_emp = Employment.query.filter_by(user_id=current_user.id, is_current=True).first()
    profile = current_user.profile
    cp = CareerProfile.query.filter_by(user_id=current_user.id).first()
    
    # helper for safe int conversion
    def safe_int(val):
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    data = {
        'full_name': pd.full_name if pd else current_user.email.split('@')[0],
        'job_title': curr_emp.job_title if curr_emp else '',
        'company_name': curr_emp.company_name if curr_emp else '',
        'city': pd.city if pd else '',
        'country': pd.country if pd else '',
        'phone': pd.phone if pd else '',
        'total_experience': profile.experience if profile else 0,
        'current_salary': cp.current_salary if cp else '',
        'notice_period': cp.notice_period_days if cp else (curr_emp.notice_period_days if curr_emp and curr_emp.is_serving_notice else '')
    }
    return jsonify({'success': True, 'data': data})

@bp.route('/basic-info', methods=['POST'])
@login_required
def save_basic_info():
    data = request.json
    
    # 1. Update Personal Details
    pd = PersonalDetails.query.filter_by(user_id=current_user.id).first()
    if not pd:
        pd = PersonalDetails(user_id=current_user.id)
        db.session.add(pd)
    
    pd.full_name = data.get('full_name')
    pd.city = data.get('city')
    pd.country = data.get('country')
    pd.phone = data.get('phone')
    pd.updated_at = datetime.utcnow()
    
    # 2. Update Current Employment
    curr_emp = Employment.query.filter_by(user_id=current_user.id, is_current=True).first()
    if data.get('job_title') or data.get('company_name'):
        if not curr_emp:
            curr_emp = Employment(user_id=current_user.id, is_current=True, start_date=datetime.utcnow(), job_title='Unknown', company_name='Unknown')
            db.session.add(curr_emp)
        curr_emp.job_title = data.get('job_title') or curr_emp.job_title
        curr_emp.company_name = data.get('company_name') or curr_emp.company_name
        curr_emp.updated_at = datetime.utcnow()
    
    # 3. Update User Profile (Experience)
    profile = current_user.profile
    if not profile:
        from app.models import UserProfile
        profile = UserProfile(user_id=current_user.id)
        db.session.add(profile)
    
    try:
        # accept decimal years (e.g., 3.5) and store as float
        profile.experience = float(data.get('total_experience', 0) or 0)
    except (ValueError, TypeError):
        pass
        
    # 4. Update Career Profile (Salary & Notice Period)
    cp = CareerProfile.query.filter_by(user_id=current_user.id).first()
    if not cp:
        cp = CareerProfile(user_id=current_user.id)
        db.session.add(cp)
    
    try:
        cp.current_salary = int(str(data.get('current_salary', '0')).replace(',', ''))
    except (ValueError, TypeError):
        pass
        
    try: 
        cp.notice_period_days = int(data.get('notice_period', 0))
    except (ValueError, TypeError):
        pass
        
    cp.updated_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Basic info updated successfully'})

# ============ PROFILE PICTURE ============
@bp.route('/upload-picture', methods=['POST'])
@login_required
def upload_picture():
    """Upload a profile picture for the user."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    # Validate file extension
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({'success': False, 'message': 'Invalid file type. Allowed: jpg, jpeg, png, gif, webp'}), 400
    
    try:
        # Create profile pictures directory if it doesn't exist
        upload_dir = Path('app/static/uploads/profile-pictures')
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate secure filename with user ID
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f'user_{current_user.id}_profile.{ext}'
        file_path = upload_dir / filename
        
        # Save file
        file.save(str(file_path))
        
        # Update user profile in database
        profile = current_user.profile
        if not profile:
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)
        
        profile.profile_picture_path = f'uploads/profile-pictures/{filename}'
        profile.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Profile picture uploaded successfully',
            'picture_url': f"/static/{profile.profile_picture_path}"
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500
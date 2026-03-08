import logging
import jinja2
from app.models.prompt_version import PromptVersion
from app.extensions import db

logger = logging.getLogger(__name__)

class PromptRegistryService:
    """
    Central registry for AI prompts. 
    Handles versioning, formatting, and determinism.
    """
    
    @staticmethod
    def get_prompt(name, version=None):
        """
        Retrieves a prompt by name and optional version.
        If version is omitted, returns the latest active version.
        """
        query = PromptVersion.query.filter_by(name=name, is_active=True)
        if version:
            query = query.filter_by(version=version)
        else:
            query = query.order_by(PromptVersion.created_at.desc())
            
        prompt = query.first()
        if not prompt:
            logger.warning(f"Prompt '{name}' version '{version}' not found. Seeding defaults...")
            prompt = PromptRegistryService._seed_default_prompt(name)
            
        return prompt

    @staticmethod
    def format_prompt(prompt_obj, **kwargs):
        """Formats the prompt template with provided variables."""
        template = jinja2.Template(prompt_obj.user_prompt_template)
        return template.render(**kwargs)

    @staticmethod
    def _seed_default_prompt(name):
        """Seeds stable production-ready prompts if they don't exist."""
        defaults = {
            'resume_generation': {
                'version': '1.0.0',
                'system_prompt': "You are a senior career consultant and ATS optimization expert. Respond ONLY with valid JSON.",
                'user_prompt_template': """
Create a high-impact, ATS-optimized resume in JSON format for the following candidate:

Profile Data:
- Skills: {{ skills }}
- Bio: {{ bio }}

Target Role: {{ target_role }}
Tone: {{ tone }}
Career Intent: 
- Strategy: {{ intent.career_stage }}
- Environment: {{ intent.environment }}
- Work Mode: {{ intent.work_mode }}
- Risk Profile: {{ intent.risk_profile }}

Incorporate these strategy-based adjustments:
1. If 'promotion', emphasize leadership, mentoring, and strategic business impact.
2. If 'startup', highlight versatility, speed, and ownership.
3. If 'enterprise', highlight scale, process, and cross-functional collaboration.
4. If 'remote', emphasize communication skills and autonomy.
5. If Risk Profile is 'bold', use high-impact power verbs and specific metrics.

JSON Structure Requirements:
{
    "header": {
        "full_name": "...",
        "title": "Professional title matching target role"
    },
    "summary": "Impactful 3-4 sentence professional summary",
    "skills": ["skill1", "skill2", ...],
    "experience": [
        {
            "company": "...",
            "role": "...",
            "duration": "...",
            "achievements": ["Action-verb led bullet point with metrics", ...]
        }
    ],
    "education": [
        {
            "institution": "...",
            "degree": "...",
            "year": "..."
        }
    ]
}
""",
                'model': 'gpt-4o',
                'temperature': 0.0,
                'max_tokens': 2500,
                'description': 'Initial production release for resume generation'
            },
            'resume_optimization': {
                'version': '1.0.0',
                'system_prompt': "You are an ATS (Applicant Tracking System) expert. Analyze and optimize the resume.",
                'user_prompt_template': """
Analyze the following resume against the provided job description.

Resume:
{{ resume_json }}

Job Description:
{{ job_description }}

Optimization Intent:
- Strategy: {{ intent.career_stage }}
- Environment: {{ intent.environment }}
- Work Mode: {{ intent.work_mode }}

Optimize the resume content to maximize ATS compatibility while aligning with the stated Intent.
1. If they are seeking a 'promotion', ensure the achievements sound higher-level.
2. If they are 'switching' to a 'startup', condense process descriptions and emphasize 'zero-to-one' contributions.

Respond ONLY with a JSON object:
{
    "ats_score": (integer 0-100),
    "missing_keywords": ["keyword1", ...],
    "tailored_summary": "...",
    "experience_updates": [
        {
            "original_achievements": ["..."],
            "optimized_achievements": ["..."]
        }
    ],
     "suggestions": ["improvement1", ...]
}
""",
                'model': 'gpt-4o',
                'temperature': 0.0,
                'max_tokens': 2000,
                'description': 'Initial production release for resume optimization'
            },
            'resume_improvement': {
                'version': '1.0.0',
                'system_prompt': "You are a professional resume writer and career coach.",
                'user_prompt_template': "Improve the following {{ context }} to be more impactful and professional for a resume. Keep the same general length and facts. Return ONLY the improved text, no preamble or extra text:\n\n{{ text }}",
                'model': 'gpt-4o',
                'temperature': 0.0,
                'max_tokens': 500,
                'description': 'Initial production release for text improvement'
            }
        }
        
        if name in defaults:
            data = defaults[name]
            prompt = PromptVersion(
                name=name,
                version=data['version'],
                system_prompt=data['system_prompt'],
                user_prompt_template=data['user_prompt_template'],
                model=data['model'],
                temperature=data['temperature'],
                max_tokens=data['max_tokens'],
                description=data['description'],
                is_active=True
            )
            db.session.add(prompt)
            db.session.commit()
            return prompt
            
        raise ValueError(f"Unknown prompt name: {name} and no default available.")

    @staticmethod
    def list_prompts():
        """Returns all versions of all prompts."""
        return PromptVersion.query.order_by(PromptVersion.name, PromptVersion.created_at.desc()).all()

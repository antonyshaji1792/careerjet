"""
AI Cover Letter Generator Service

This module generates personalized cover letters using OpenAI GPT-4.
It can create cover letters tailored to specific job descriptions and companies.
"""

from datetime import datetime
from app.services.ai_metering_service import AIMeteringService
import logging

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """Generate AI-powered cover letters"""
    
    def __init__(self):
        pass
    
    async def generate(self, user_id, job_title, company_name, job_description, user_profile, tone='professional'):
        """
        Generate a personalized cover letter
        
        Args:
            user_id (int): User ID for metering
            job_title (str): Job title
            company_name (str): Company name
            job_description (str): Job description text
            user_profile (dict): User profile data (skills, experience, etc.)
            tone (str): Tone of the letter ('professional', 'enthusiastic', 'conservative')
            
        Returns:
            str: Generated cover letter
        """
        try:
            # Build the prompt
            prompt = self._build_prompt(
                job_title=job_title,
                company_name=company_name,
                job_description=job_description,
                user_profile=user_profile,
                tone=tone
            )
            
            # Call metered AI API
            metered_resp = await AIMeteringService.ask_ai_metered(
                user_id=user_id,
                feature_type='cover_letter',
                prompt=prompt,
                system_prompt="You are an expert career coach and professional writer specializing in creating compelling cover letters that get interviews.",
                max_tokens=800
            )
            
            if not metered_resp.get('success'):
                logger.error(f"Metered Cover Letter generation failed: {metered_resp.get('message')}")
                return self._get_fallback_template(job_title, company_name, user_profile)

            cover_letter = metered_resp.get('text', '').strip()
            logger.info(f"Generated cover letter for {job_title} at {company_name}")
            
            return cover_letter
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            return self._get_fallback_template(job_title, company_name, user_profile)
    
    def _build_prompt(self, job_title, company_name, job_description, user_profile, tone):
        """Build the prompt for OpenAI"""
        
        # Extract user info
        skills = user_profile.get('skills', 'Not specified')
        experience = user_profile.get('experience', 'Not specified')
        preferred_roles = user_profile.get('preferred_roles', 'Not specified')
        
        # Tone descriptions
        tone_guide = {
            'professional': 'professional and polished',
            'enthusiastic': 'enthusiastic and passionate',
            'conservative': 'conservative and formal'
        }
        
        tone_description = tone_guide.get(tone, 'professional and polished')
        
        prompt = f"""
Write a compelling cover letter for the following job application:

**Job Title**: {job_title}
**Company**: {company_name}

**Job Description**:
{job_description[:1000]}  # Limit to avoid token limits

**Candidate Profile**:
- Skills: {skills}
- Years of Experience: {experience}
- Career Goals: {preferred_roles}

**Requirements**:
1. Write in a {tone_description} tone
2. Highlight relevant skills and experience that match the job description
3. Show genuine interest in the company and role
4. Keep it concise (3-4 paragraphs)
5. Include a strong opening and closing
6. Make it personalized and specific to this role
7. Use [Your Name] as a placeholder for the candidate's name
8. Use [Your Contact] as a placeholder for contact information

**Format**:
- Start with a professional greeting
- Include 3-4 well-structured paragraphs
- End with a professional closing
- Do NOT include address blocks or date (we'll add those separately)

Generate the cover letter now:
"""
        
        return prompt
    
    def _get_fallback_template(self, job_title, company_name, user_profile):
        """Fallback template if AI generation fails"""
        
        skills = user_profile.get('skills', 'relevant skills')
        experience = user_profile.get('experience', 'several years')
        
        template = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company_name}. With {experience} years of experience and expertise in {skills}, I am confident that I would be a valuable addition to your team.

Throughout my career, I have developed a strong foundation in the skills and technologies that are essential for this role. My experience has taught me the importance of continuous learning, collaboration, and delivering high-quality results. I am particularly drawn to {company_name} because of your reputation for innovation and excellence in the industry.

I am excited about the opportunity to contribute to your team and help {company_name} achieve its goals. My background in {skills} aligns well with the requirements of this position, and I am eager to bring my expertise to your organization.

Thank you for considering my application. I look forward to the opportunity to discuss how my skills and experience can benefit {company_name}.

Sincerely,
[Your Name]
[Your Contact]"""
        
        return template
    
    def customize_template(self, template, replacements):
        """
        Customize a cover letter template with user-specific information
        
        Args:
            template (str): Cover letter template
            replacements (dict): Dictionary of placeholder -> value mappings
            
        Returns:
            str: Customized cover letter
        """
        customized = template
        
        for placeholder, value in replacements.items():
            customized = customized.replace(f"[{placeholder}]", str(value))
        
        return customized
    
    def get_templates(self):
        """Get predefined cover letter templates"""
        
        templates = {
            'professional': {
                'name': 'Professional',
                'description': 'A polished, professional cover letter suitable for most roles',
                'content': """Dear Hiring Manager,

I am writing to apply for the [Job Title] position at [Company Name]. With [Years] years of experience in [Field], I am excited about the opportunity to contribute to your team.

My background in [Skills] has prepared me well for this role. At [Previous Company], I successfully [Achievement], which resulted in [Impact]. I am particularly drawn to [Company Name] because of [Reason].

I am confident that my skills in [Key Skills] and my passion for [Industry] make me an ideal candidate for this position. I would welcome the opportunity to discuss how I can contribute to [Company Name]'s continued success.

Thank you for your consideration.

Sincerely,
[Your Name]
[Your Contact]"""
            },
            'enthusiastic': {
                'name': 'Enthusiastic',
                'description': 'An energetic cover letter showing passion and excitement',
                'content': """Dear Hiring Team,

I am thrilled to apply for the [Job Title] position at [Company Name]! As someone who has been following [Company Name]'s work in [Industry], I am incredibly excited about the possibility of joining your team.

Throughout my [Years] years in [Field], I have developed a deep passion for [Area of Interest]. My experience with [Skills] has not only honed my technical abilities but also reinforced my enthusiasm for creating [Impact]. I am particularly excited about [Company Name]'s recent [Project/Initiative] and would love to contribute to similar innovative work.

I believe my combination of technical expertise and genuine passion for [Industry] would make me a valuable addition to your team. I am eager to bring my energy and skills to [Company Name] and help drive [Goal].

I would be delighted to discuss this opportunity further!

Best regards,
[Your Name]
[Your Contact]"""
            },
            'conservative': {
                'name': 'Conservative',
                'description': 'A formal, traditional cover letter for conservative industries',
                'content': """Dear Sir/Madam,

I am writing to formally apply for the [Job Title] position at [Company Name], as advertised. I believe my [Years] years of professional experience in [Field] make me a strong candidate for this role.

My professional background includes extensive experience in [Skills], with a proven track record of [Achievement]. I have consistently demonstrated my ability to [Key Competency] while maintaining the highest standards of professionalism and quality.

I am confident that my qualifications align well with the requirements of this position. I would appreciate the opportunity to discuss my candidacy in greater detail at your convenience.

Thank you for your time and consideration.

Respectfully,
[Your Name]
[Your Contact]"""
            },
            'career_change': {
                'name': 'Career Change',
                'description': 'For candidates transitioning to a new field or industry',
                'content': """Dear Hiring Manager,

I am writing to express my interest in the [Job Title] position at [Company Name]. While my background is in [Previous Field], I am excited to transition into [New Field] and believe my transferable skills make me a strong candidate.

During my [Years] years in [Previous Field], I developed valuable skills in [Transferable Skills] that are directly applicable to this role. My experience with [Relevant Experience] has given me a unique perspective that I am eager to bring to [Company Name].

I am committed to this career transition and have been actively [Learning/Preparation Activities]. I am confident that my combination of diverse experience and fresh perspective would be an asset to your team.

I would welcome the opportunity to discuss how my background can benefit [Company Name].

Sincerely,
[Your Name]
[Your Contact]"""
            }
        }
        
        return templates


# Helper function for easy use
async def generate_cover_letter(user_id, job_title, company_name, job_description, user_profile, tone='professional'):
    """
    Quick function to generate a cover letter
    """
    generator = CoverLetterGenerator()
    return await generator.generate(user_id, job_title, company_name, job_description, user_profile, tone)

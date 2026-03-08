"""
Resume Parser Service - Extract structured data from uploaded resumes
"""
import logging
import json
import re
from typing import Dict, Optional, List
from datetime import datetime
import PyPDF2
import docx

logger = logging.getLogger(__name__)

class ResumeParserService:
    """
    Parse uploaded resumes and extract structured information for profile auto-fill.
    """
    
    @staticmethod
    def parse_resume_file(file_path: str) -> Dict:
        """
        Parse resume file and extract structured data.
        Supports PDF and DOCX formats.
        """
        try:
            # Determine file type
            if file_path.lower().endswith('.pdf'):
                text = ResumeParserService._extract_text_from_pdf(file_path)
            elif file_path.lower().endswith('.docx'):
                text = ResumeParserService._extract_text_from_docx(file_path)
            elif file_path.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                return {'success': False, 'message': 'Unsupported file format'}
            
            # Extract structured data from text
            parsed_data = ResumeParserService._extract_structured_data(text)
            
            return {
                'success': True,
                'data': parsed_data,
                'raw_text': text
            }
            
        except Exception as e:
            logger.error(f"Resume parsing error: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def _extract_text_from_pdf(file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            raise
        return text
    
    @staticmethod
    def _extract_text_from_docx(file_path: str) -> str:
        """Extract text from DOCX file."""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX extraction error: {str(e)}")
            raise
        return text
    
    @staticmethod
    def _extract_structured_data(text: str) -> Dict:
        """
        Extract structured data from resume text using pattern matching.
        """
        data = {
            'full_name': None,
            'email': None,
            'phone': None,
            'location': None,
            'linkedin': None,
            'github': None,
            'skills': [],
            'experience': [],
            'education': [],
            'summary': None
        }
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            data['email'] = emails[0]
        
        # Extract phone
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            data['phone'] = ''.join(phones[0]) if isinstance(phones[0], tuple) else phones[0]
        
        # Extract LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin_matches = re.findall(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_matches:
            data['linkedin'] = f"https://{linkedin_matches[0]}"
        
        # Extract GitHub
        github_pattern = r'github\.com/[\w-]+'
        github_matches = re.findall(github_pattern, text, re.IGNORECASE)
        if github_matches:
            data['github'] = f"https://{github_matches[0]}"
        
        # Extract name (usually first line or after "Name:")
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            # Try to find name in first few lines
            for line in lines[:5]:
                # Skip lines that look like section headers or contact info
                if not any(keyword in line.lower() for keyword in ['email', 'phone', 'address', 'summary', 'experience', 'education', 'skills']):
                    if len(line.split()) <= 4 and len(line) < 50:  # Likely a name
                        data['full_name'] = line
                        break
        
        # Extract skills (look for skills section)
        skills_section = ResumeParserService._extract_section(text, 'skills|technical skills|core competencies')
        if skills_section:
            # Split by common delimiters
            skills_text = re.sub(r'[•\-\*]', ',', skills_section)
            skills = [s.strip() for s in re.split(r'[,|\n]', skills_text) if s.strip()]
            # Filter out section headers and long text
            data['skills'] = [s for s in skills if len(s) < 50 and not s.lower().startswith('skill')][:20]
        
        # Extract summary/objective
        summary_keywords = 'summary|objective|profile|about|professional summary|executive summary|overview|synopsis|core competencies|career profile|professional profile|career summary'
        summary_section = ResumeParserService._extract_section(text, summary_keywords)
        if summary_section:
            # Take section content
            data['summary'] = summary_section[:1500].strip()
        
        # Fallback: if no summary section found, try to take the first substantial paragraph
        if not data['summary']:
            # Look at first half of the resume
            top_half = lines[:len(lines)//2]
            for line in top_half:
                # If a line is long and doesn't look like contact info or a header
                if len(line) > 100 and not any(keyword in line.lower() for keyword in ['education', 'experience', 'skill', 'work', 'university', 'college']):
                    data['summary'] = line[:1500]
                    break
        
        # Extract location/address (look for city, state patterns)
        # Strategy 1: Look for "Address:" or "Location:" prefix
        address_match = re.search(r'(?i)(?:Address|Location|Lives in)[:\s]+(.+)', text)
        if address_match:
            data['location'] = address_match.group(1).split('\n')[0].strip()
        
        # Strategy 2: Look in first 10 lines for City, State pattern
        if not data['location']:
            first_lines = '\n'.join(lines[:10])
            # Refined pattern: City (at least 3 chars), State (2 uppercase letters)
            # Avoid matching common skills like JS, CS, IT
            location_pattern = r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\b'
            locations = re.findall(location_pattern, first_lines)
            if locations:
                for city, state in locations:
                    # Skip common false positives
                    if city.lower() not in ['skill', 'experience', 'education', 'summary', 'profile', 'css', 'html', 'js', 'xml', 'api']:
                        data['location'] = f"{city}, {state}"
                        break
        
        # Extract full address if possible
        data['address'] = None
        if data['location'] and len(data['location']) > 20: 
            data['address'] = data['location']
        
        # Extract employment history
        data['experience'] = ResumeParserService._extract_employment(text)
        
        # Extract education
        data['education'] = ResumeParserService._extract_education(text)
        
        # Extract languages
        data['languages'] = ResumeParserService._extract_languages(text)
        
        return data
    
    @staticmethod
    def _extract_employment(text: str) -> List[Dict]:
        """Extract employment/work experience from resume with multiple fallback strategies."""
        employment_list = []
        
        # Strategy 1: Try to find dedicated experience section
        exp_section = ResumeParserService._extract_section(text, 'experience|employment|work history|professional experience|work experience')
        
        logger.info(f"Experience section found: {bool(exp_section)}")
        if exp_section:
            logger.info(f"Experience section length: {len(exp_section)} chars")
            logger.info(f"Experience section preview: {exp_section[:200]}...")
        
        if not exp_section:
            # Strategy 2: Look for experience keywords in full text
            logger.info("No experience section found, trying full text search")
            exp_section = text
        
        # Multiple patterns to catch different resume formats
        patterns = [
            # Pattern 1: "Job Title at Company" or "Job Title @ Company"
            r'([A-Z][A-Za-z\s&,]+?)\s+(?:at|@)\s+([A-Z][A-Za-z\s&,\.]+?)(?:\n|$|\||•)',
            # Pattern 2: "Company Name - Job Title"
            r'([A-Z][A-Za-z\s&,\.]+?)\s+-\s+([A-Z][A-Za-z\s&,]+?)(?:\n|$)',
            # Pattern 3: Job title on one line, company on next
            r'([A-Z][A-Za-z\s]+?)\n([A-Z][A-Za-z\s&,\.]+(?:Inc|LLC|Ltd|Corp|Company|Technologies|Solutions))',
            # Pattern 4: Bullet points with job info
            r'[•\-\*]\s*([A-Z][A-Za-z\s]+?)\\s+(?:at|@|-)\s+([A-Z][A-Za-z\s&,\.]+)',
        ]
        
        jobs_found = []
        
        for pattern_idx, pattern in enumerate(patterns):
            matches = re.findall(pattern, exp_section)
            logger.info(f"Pattern {pattern_idx + 1} found {len(matches)} matches")
            
            for match in matches:
                if len(match) == 2:
                    # Determine which is job title and which is company
                    if pattern_idx == 1:  # Company - Job Title pattern
                        company_name = match[0].strip()
                        job_title = match[1].strip()
                    else:  # Job Title at/@ Company pattern
                        job_title = match[0].strip()
                        company_name = match[1].strip()
                    
                    # Filter out obvious non-jobs
                    if len(job_title) > 3 and len(company_name) > 2:
                        jobs_found.append({
                            'job_title': job_title,
                            'company_name': company_name
                        })
        
        logger.info(f"Total jobs found across all patterns: {len(jobs_found)}")
        
        # Strategy 3: If no jobs found, try simple line-by-line extraction
        if not jobs_found:
            logger.info("No jobs found with patterns, trying simple line extraction")
            lines = [line.strip() for line in exp_section.split('\n') if line.strip()]
            
            # Look for common job titles
            job_keywords = ['engineer', 'developer', 'manager', 'analyst', 'designer', 'consultant', 
                          'specialist', 'coordinator', 'director', 'lead', 'architect', 'administrator']
            
            for i, line in enumerate(lines):
                # Check if line contains job keywords
                if any(keyword in line.lower() for keyword in job_keywords):
                    job_title = line
                    company_name = "Company"  # Default
                    
                    # Try to find company name in next few lines
                    for j in range(i+1, min(i+3, len(lines))):
                        next_line = lines[j]
                        # Skip date lines
                        if not re.search(r'\d{4}', next_line):
                            # Check if it looks like a company name (capitalized, not too long)
                            if next_line[0].isupper() and len(next_line) < 100:
                                company_name = next_line
                                break
                    
                    jobs_found.append({
                        'job_title': job_title,
                        'company_name': company_name
                    })
            
            logger.info(f"Simple extraction found {len(jobs_found)} jobs")
        
        # Remove duplicates
        seen = set()
        unique_jobs = []
        for job in jobs_found:
            key = (job['job_title'].lower(), job['company_name'].lower())
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)
        
        logger.info(f"Unique jobs after deduplication: {len(unique_jobs)}")
        
        # Extract dates for each job
        date_patterns = [
            r'(\d{4})\s*[-–]\s*(\d{4})',  # 2020 - 2023
            r'(\d{4})\s*[-–]\s*(Present|Current|Now)',  # 2020 - Present
            r'(\w+\s+\d{4})\s*[-–]\s*(\w+\s+\d{4})',  # Jan 2020 - Dec 2023
            r'(\w+\s+\d{4})\s*[-–]\s*(Present|Current|Now)',  # Jan 2020 - Present
        ]
        
        all_dates = []
        for date_pattern in date_patterns:
            dates = re.findall(date_pattern, exp_section, re.IGNORECASE)
            all_dates.extend(dates)
        
        logger.info(f"Total date ranges found: {len(all_dates)}")
        
        # Combine jobs with dates
        for idx, job in enumerate(unique_jobs[:5]):  # Limit to 5 most recent
            start_year = None
            end_year = None
            is_current = False
            
            # Try to match dates
            if idx < len(all_dates):
                date_match = all_dates[idx]
                
                # Extract start year
                start_str = date_match[0]
                if start_str.isdigit():
                    start_year = int(start_str)
                else:
                    year_match = re.search(r'\d{4}', start_str)
                    if year_match:
                        start_year = int(year_match.group())
                
                # Extract end year
                end_str = date_match[1]
                if end_str.lower() in ['present', 'current', 'now']:
                    is_current = True
                    end_year = datetime.now().year
                elif end_str.isdigit():
                    end_year = int(end_str)
                else:
                    year_match = re.search(r'\d{4}', end_str)
                    if year_match:
                        end_year = int(year_match.group())
            
            employment_list.append({
                'job_title': job['job_title'][:200],
                'company_name': job['company_name'][:200],
                'start_year': start_year,
                'end_year': end_year,
                'is_current': is_current
            })
        
        logger.info(f"Final employment list: {len(employment_list)} entries")
        for idx, emp in enumerate(employment_list):
            logger.info(f"Job {idx + 1}: {emp['job_title']} at {emp['company_name']} ({emp.get('start_year')} - {emp.get('end_year')})")
        
        return employment_list
    
    @staticmethod
    def _extract_education(text: str) -> List[Dict]:
        """Extract education history from resume."""
        education_list = []
        
        # Extract education section
        edu_section = ResumeParserService._extract_section(text, 'education|academic|qualifications')
        if not edu_section:
            return education_list
        
        # Common degree patterns
        degree_patterns = [
            r'(Bachelor|Master|PhD|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|B\.?Tech|M\.?Tech|MBA|BBA)[\w\s]*',
            r'(Diploma|Certificate)[\w\s]*'
        ]
        
        # Extract degrees
        degrees = []
        for pattern in degree_patterns:
            matches = re.findall(pattern, edu_section, re.IGNORECASE)
            degrees.extend(matches)
        
        # Extract institutions (usually capitalized words)
        institution_pattern = r'([A-Z][A-Za-z\s&,\.]+(?:University|College|Institute|School|Academy))'
        institutions = re.findall(institution_pattern, edu_section)
        
        # Extract years
        year_pattern = r'\b(19\d{2}|20\d{2})\b'
        years = re.findall(year_pattern, edu_section)
        
        # Combine extracted information
        max_entries = max(len(degrees), len(institutions))
        for i in range(min(max_entries, 3)):  # Limit to 3 education entries
            degree = degrees[i] if i < len(degrees) else 'Degree'
            institution = institutions[i].strip() if i < len(institutions) else 'Institution'
            
            # Try to find graduation year
            end_year = None
            if i * 2 + 1 < len(years):
                end_year = int(years[i * 2 + 1])
            elif i < len(years):
                end_year = int(years[i])
            
            education_list.append({
                'degree': degree[:200],
                'institution': institution[:200],
                'end_year': end_year
            })
        
        return education_list
    
    @staticmethod
    def _extract_languages(text: str) -> List[Dict]:
        """Extract languages from resume."""
        languages_list = []
        
        # Common languages to look for
        common_languages = [
            'English', 'Spanish', 'French', 'German', 'Chinese', 'Japanese', 
            'Hindi', 'Arabic', 'Portuguese', 'Russian', 'Bengali', 'Punjabi',
            'Telugu', 'Marathi', 'Tamil', 'Urdu', 'Gujarati', 'Kannada', 'Malayalam'
        ]
        
        # Strategy 1: Look for dedicated languages section
        lang_section = ResumeParserService._extract_section(text, 'languages|linguistic skills|languages known')
        search_text = lang_section if lang_section else text
        
        # Strategy 2: Search for language names and proficiency
        proficiencies = ['Native', 'Fluent', 'Bilingual', 'Professional', 'Elementary', 'Intermediate', 'Expert', 'Full Professional']
        
        for lang in common_languages:
            if re.search(rf'\b{lang}\b', search_text, re.IGNORECASE):
                # Try to find proficiency near the language name
                proficiency = 'Intermediate' # Default
                
                # Check for proficiency keywords in the lines around where the language was found
                lang_match = re.search(rf'\b{lang}\b', search_text, re.IGNORECASE)
                if lang_match:
                    start = max(0, lang_match.start() - 50)
                    end = min(len(search_text), lang_match.end() + 50)
                    context = search_text[start:end]
                    
                    for p in proficiencies:
                        if re.search(rf'\b{p}\b', context, re.IGNORECASE):
                            proficiency = p
                            break
                
                languages_list.append({
                    'language_name': lang,
                    'proficiency': proficiency
                })
        
        return languages_list
    
    @staticmethod
    def _extract_section(text: str, section_name: str) -> Optional[str]:
        """
        Extract a specific section from resume text with high flexibility.
        """
        # Improved pattern handles:
        # 1. Headers in Title Case or ALL CAPS
        # 2. Text starting on the same line or next line
        # 3. Lookahead stops at any potential header (Title Case or ALL CAPS)
        
        # Stop at any line that looks like a new section header
        # (e.g., "EXPERIENCE", "Work History", "PROJECTS:")
        stop_lookahead = r'(?=\n(?:[A-Z\s]{4,}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[:\s]*\n|\Z)'
        
        # Match header followed by optional colon/whitespace and then capture content
        pattern = rf'(?i)(?:^|\n)({section_name})[:\s]*(?:\n|\s)(.*?){stop_lookahead}'
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        
        if match:
            return match.group(2).strip()
        return None


async def autofill_profile_from_resume(resume_id: int) -> Dict:
    """
    Auto-fill user profile from uploaded resume including employment and education.
    """
    from app.models import Resume
    from app.models.profile import PersonalDetails, ProfileSummary, KeySkill, Accomplishment, Employment, Education
    from app.extensions import db
    from datetime import date
    
    try:
        # Get resume
        resume = Resume.query.get(resume_id)
        if not resume:
            return {'success': False, 'message': 'Resume not found'}
        
        # Parse resume file
        parse_result = ResumeParserService.parse_resume_file(resume.file_path)
        
        if not parse_result['success']:
            return parse_result
        
        extracted_data = parse_result['data']
        
        # Track fields updated
        fields_updated = []
        
        # 1. Update PersonalDetails
        personal_details = PersonalDetails.query.filter_by(user_id=resume.user_id).first()
        if not personal_details:
            personal_details = PersonalDetails(user_id=resume.user_id)
            db.session.add(personal_details)
        
        if extracted_data.get('full_name') and not personal_details.full_name:
            personal_details.full_name = extracted_data['full_name']
            fields_updated.append('full_name')
        
        if extracted_data.get('phone') and not personal_details.phone:
            personal_details.phone = extracted_data['phone']
            fields_updated.append('phone')
        
        if extracted_data.get('location'):
            # Only update if city is empty
            if not personal_details.city:
                location_parts = extracted_data['location'].split(',')
                if len(location_parts) >= 1:
                    city = location_parts[0].strip()
                    # Final safety check: skip if it looks like a skill
                    if len(city) > 2 and city.lower() not in ['css', 'html', 'js', 'php']:
                        personal_details.city = city
                        fields_updated.append('city')
                if len(location_parts) >= 2:
                    personal_details.state = location_parts[1].strip()
                    fields_updated.append('state')
        
        if extracted_data.get('address') and not personal_details.address:
            # Final safety check for address
            if len(extracted_data['address']) > 5:
                personal_details.address = extracted_data['address']
                fields_updated.append('address')
        
        # 2. Update ProfileSummary
        if extracted_data.get('summary'):
            profile_summary = ProfileSummary.query.filter_by(user_id=resume.user_id).first()
            if not profile_summary:
                profile_summary = ProfileSummary(
                    user_id=resume.user_id,
                    summary=extracted_data['summary']
                )
                db.session.add(profile_summary)
                fields_updated.append('summary')
            elif not profile_summary.summary or not profile_summary.summary.strip():
                profile_summary.summary = extracted_data['summary']
                fields_updated.append('summary')
        
        # 3. Add KeySkills
        if extracted_data.get('skills'):
            existing_skills = {skill.skill_name.lower() for skill in KeySkill.query.filter_by(user_id=resume.user_id).all()}
            new_skills_added = 0
            
            for skill_name in extracted_data['skills'][:10]:  # Top 10 skills
                if skill_name.lower() not in existing_skills:
                    new_skill = KeySkill(
                        user_id=resume.user_id,
                        skill_name=skill_name
                    )
                    db.session.add(new_skill)
                    new_skills_added += 1
            
            if new_skills_added > 0:
                fields_updated.append(f'skills ({new_skills_added} added)')
        
        # 3b. Add IT Skills (Technical Skills)
        if extracted_data.get('skills'):
            from app.models.profile import ITSkill
            
            # Common technical skills that should go into IT Skills
            tech_keywords = [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin',
                'react', 'angular', 'vue', 'node', 'django', 'flask', 'spring', 'express',
                'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git',
                'html', 'css', 'sass', 'bootstrap', 'tailwind',
                'tensorflow', 'pytorch', 'scikit', 'pandas', 'numpy',
                'rest', 'api', 'graphql', 'microservices'
            ]
            
            existing_it_skills = {skill.skill_name.lower() for skill in ITSkill.query.filter_by(user_id=resume.user_id).all()}
            it_skills_added = 0
            
            for skill_name in extracted_data['skills']:
                skill_lower = skill_name.lower()
                
                # Check if it's a technical skill
                is_tech_skill = any(keyword in skill_lower for keyword in tech_keywords)
                
                if is_tech_skill and skill_lower not in existing_it_skills:
                    it_skill = ITSkill(
                        user_id=resume.user_id,
                        skill_name=skill_name,
                        experience_years=2  # Default to 2 years
                    )
                    db.session.add(it_skill)
                    it_skills_added += 1
            
            if it_skills_added > 0:
                fields_updated.append(f'IT skills ({it_skills_added} added)')
                logger.info(f"Added {it_skills_added} IT skills")
        
        # 4. Add Employment History
        if extracted_data.get('experience'):
            logger.info(f"Found {len(extracted_data['experience'])} jobs in extracted data")
            
            existing_jobs_count = Employment.query.filter_by(user_id=resume.user_id).count()
            logger.info(f"User already has {existing_jobs_count} employment records")
            
            # Get existing job titles to avoid duplicates
            existing_jobs = Employment.query.filter_by(user_id=resume.user_id).all()
            existing_titles = {(job.job_title.lower(), job.company_name.lower()) for job in existing_jobs}
            
            jobs_added = 0
            for job_data in extracted_data['experience']:
                job_key = (job_data['job_title'].lower(), job_data['company_name'].lower())
                
                # Only add if this exact job doesn't exist
                if job_key not in existing_titles:
                    try:
                        # Create start and end dates
                        start_date = date(job_data['start_year'], 1, 1) if job_data.get('start_year') else None
                        end_date = None if job_data.get('is_current') else (date(job_data['end_year'], 12, 31) if job_data.get('end_year') else None)
                        
                        employment = Employment(
                            user_id=resume.user_id,
                            job_title=job_data['job_title'],
                            company_name=job_data['company_name'],
                            start_date=start_date,
                            end_date=end_date,
                            is_current=job_data.get('is_current', False)
                        )
                        db.session.add(employment)
                        jobs_added += 1
                        logger.info(f"Added job: {job_data['job_title']} at {job_data['company_name']}")
                    except Exception as e:
                        logger.error(f"Error adding job: {str(e)}")
                else:
                    logger.info(f"Skipping duplicate job: {job_data['job_title']} at {job_data['company_name']}")
            
            if jobs_added > 0:
                fields_updated.append(f'employment ({jobs_added} jobs added)')
                logger.info(f"Total jobs added: {jobs_added}")
            else:
                logger.info("No new jobs added (all were duplicates or errors)")
        
        # 5. Add Education History
        if extracted_data.get('education'):
            existing_edu_count = Education.query.filter_by(user_id=resume.user_id).count()
            
            if existing_edu_count == 0:  # Only add if no education history exists
                edu_added = 0
                for edu_data in extracted_data['education']:
                    education = Education(
                        user_id=resume.user_id,
                        degree=edu_data['degree'],
                        institution=edu_data['institution'],
                        end_year=edu_data.get('end_year')
                    )
                    db.session.add(education)
                    edu_added += 1
                
                if edu_added > 0:
                    fields_updated.append(f'education ({edu_added} entries added)')
        
        # 6. Add Languages
        if extracted_data.get('languages'):
            from app.models.profile import Language
            
            existing_languages = {lang.language_name.lower() for lang in Language.query.filter_by(user_id=resume.user_id).all()}
            languages_added = 0
            
            for lang_data in extracted_data['languages']:
                if lang_data['language_name'].lower() not in existing_languages:
                    language = Language(
                        user_id=resume.user_id,
                        language_name=lang_data['language_name'],
                        proficiency=lang_data.get('proficiency', 'Intermediate'),
                        can_read=True,
                        can_write=True,
                        can_speak=True
                    )
                    db.session.add(language)
                    languages_added += 1
            
            if languages_added > 0:
                fields_updated.append(f'languages ({languages_added} added)')
                logger.info(f"Added {languages_added} languages")

        # 7. Add LinkedIn/GitHub as Accomplishments (online profiles)
        if extracted_data.get('linkedin'):
            # Check if LinkedIn already exists
            existing_linkedin = Accomplishment.query.filter_by(
                user_id=resume.user_id,
                type='online_profile',
                url=extracted_data['linkedin']
            ).first()
            
            if not existing_linkedin:
                linkedin_accomplishment = Accomplishment(
                    user_id=resume.user_id,
                    type='online_profile',
                    title='LinkedIn Profile',
                    url=extracted_data['linkedin']
                )
                db.session.add(linkedin_accomplishment)
                fields_updated.append('linkedin')
        
        if extracted_data.get('github'):
            # Check if GitHub already exists
            existing_github = Accomplishment.query.filter_by(
                user_id=resume.user_id,
                type='online_profile',
                url=extracted_data['github']
            ).first()
            
            if not existing_github:
                github_accomplishment = Accomplishment(
                    user_id=resume.user_id,
                    type='online_profile',
                    title='GitHub Profile',
                    url=extracted_data['github']
                )
                db.session.add(github_accomplishment)
                fields_updated.append('github')
        
        # Commit all changes
        db.session.commit()
        
        if fields_updated:
            return {
                'success': True,
                'message': f'Profile auto-filled successfully! Updated: {", ".join(fields_updated)}',
                'fields_updated': fields_updated,
                'extracted_data': extracted_data
            }
        else:
            return {
                'success': True,
                'message': 'Profile already contains all extractable information from your resume.',
                'fields_updated': [],
                'extracted_data': extracted_data
            }
        
    except Exception as e:
        logger.error(f"Auto-fill error: {str(e)}")
        db.session.rollback()
        return {'success': False, 'message': f'Error: {str(e)}'}

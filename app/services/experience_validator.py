import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class ExperienceValidatorService:
    """
    Analyzes resume experience for timeline coherence, gaps, and logical inconsistencies.
    Ensures the professional story is tight and error-free before finalization.
    """

    @staticmethod
    def validate_experience(experience_list):
        """
        Analyzes a list of experience items.
        Returns a list of structured warnings.
        """
        warnings = []
        if not experience_list:
            return warnings

        # Pre-process dates
        processed_exp = []
        for exp in experience_list:
            duration = exp.get('duration', '')
            parsed = ExperienceValidatorService._parse_duration(duration)
            processed_exp.append({
                **exp,
                'parsed_dates': parsed
            })

        # Sort by start date descending
        processed_exp.sort(key=lambda x: x['parsed_dates'][0] if x['parsed_dates'][0] else datetime.min, reverse=True)

        # 1. Detect Timeline Gaps & Overlaps
        for i in range(len(processed_exp) - 1):
            curr = processed_exp[i]
            prev = processed_exp[i+1] # Older role

            curr_start = curr['parsed_dates'][0]
            prev_end = prev['parsed_dates'][1]

            if curr_start and prev_end:
                delta = (curr_start - prev_end).days
                if delta > 90: # Gap > 3 months
                    warnings.append({
                        "type": "gap",
                        "severity": "medium",
                        "message": f"Significant gap (~{delta // 30} months) detected between {prev.get('company')} and {curr.get('company')}.",
                        "roles": [prev.get('role'), curr.get('role')]
                    })
                elif delta < -30: # Overlap > 1 month
                    warnings.append({
                        "type": "overlap",
                        "severity": "low",
                        "message": f"Timeline overlap detected between {prev.get('company')} and {curr.get('company')}. Ensure this is intentional (e.g., dual roles).",
                        "roles": [prev.get('role'), curr.get('role')]
                    })

        # 2. Tool & Tech Consistency
        # Example: Using "React" in 2010 (React was released in 2013)
        tech_history = {
            "React": 2013,
            "Vue": 2014,
            "Kubernetes": 2014,
            "Docker": 2013,
            "Flutter": 2017,
            "Swift": 2014,
            "Kotlin": 2011,
            "Go": 2009,
            "Rust": 2010
        }

        for exp in processed_exp:
            role_year = exp['parsed_dates'][0].year if exp['parsed_dates'][0] else None
            if not role_year: continue

            full_text = f"{exp.get('role', '')} {exp.get('company', '')} {' '.join(exp.get('achievements', []))}"
            for tech, year in tech_history.items():
                if tech.lower() in full_text.lower() and role_year < year:
                    warnings.append({
                        "type": "anachronism",
                        "severity": "high",
                        "message": f"Possible inconsistency: {tech} mentioned in a role starting in {role_year}, but it was released in {year}.",
                        "role": exp.get('role')
                    })

        return warnings

    @staticmethod
    def _parse_duration(duration_str):
        """
        Parses strings like 'Jan 2020 - Present' or '2018 - 2020'.
        Returns (start_date, end_date)
        """
        try:
            parts = duration_str.split('-')
            if len(parts) != 2:
                # Try to extract year at least
                years = re.findall(r'\d{4}', duration_str)
                if len(years) >= 1:
                    start = datetime(int(years[0]), 1, 1)
                    end = datetime(int(years[1]), 1, 1) if len(years) > 1 else datetime.now()
                    return start, end
                return None, None

            start_str = parts[0].strip()
            end_str = parts[1].strip()

            def parse_single(s):
                if 'present' in s.lower():
                    return datetime.now()
                # Try common formats
                for fmt in ('%b %Y', '%B %Y', '%Y'):
                    try:
                        return datetime.strptime(s, fmt)
                    except:
                        continue
                # Last resort regex for year
                yr = re.search(r'\d{4}', s)
                if yr:
                    return datetime(int(yr.group()), 1, 1)
                return None

            return parse_single(start_str), parse_single(end_str)
        except:
            return None, None

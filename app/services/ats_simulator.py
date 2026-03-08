import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

class ATSSimulatorService:
    """
    Simulates how real-world ATS (Applicant Tracking Systems) parse and weight resumes.
    Includes truncation, section extraction failures, and keyword frequency thresholds.
    """

    ATS_PROFILES = {
        "legacy": {
            "name": "Legacy Enterprise (Strict)",
            "truncation_limit": 1000, # words
            "keyword_weight": 0.5,
            "section_weights": {"experience": 0.6, "skills": 0.3, "education": 0.1},
            "frequency_bonus_limit": 3, # Max matches for a single skill
            "ignore_formatting": True
        },
        "modern": {
            "name": "Modern SaaS (NLP-focused)",
            "truncation_limit": 2500,
            "keyword_weight": 0.3,
            "section_weights": {"experience": 0.5, "skills": 0.4, "summary": 0.1},
            "frequency_bonus_limit": 5,
            "ignore_formatting": False
        }
    }

    @staticmethod
    def simulate_parse(resume_data, job_description, profile_key="legacy"):
        """
        Runs the simulation.
        Returns a dict with score, extracted content, and ignored blocks.
        """
        profile = ATSSimulatorService.ATS_PROFILES.get(profile_key, ATSSimulatorService.ATS_PROFILES["legacy"])
        
        # 1. Simulate Truncation
        raw_text = ATSSimulatorService._flatten_resume(resume_data)
        words = raw_text.split()
        full_word_count = len(words)
        
        truncated = False
        if full_word_count > profile["truncation_limit"]:
            truncated = True
            words = words[:profile["truncation_limit"]]
            processed_text = " ".join(words)
        else:
            processed_text = raw_text

        # 2. Keyword Extraction & Frequency
        jd_keywords = ATSSimulatorService._extract_keywords(job_description, as_set=True)
        detected_keywords = ATSSimulatorService._extract_keywords(processed_text, as_set=False)
        
        keyword_matches = Counter()
        for kw in detected_keywords:
            if kw in jd_keywords:
                keyword_matches[kw] += 1

        # 3. Scoring
        unique_matches = len(keyword_matches)
        total_possible = len(jd_keywords) if jd_keywords else 1
        
        # Frequency bonus (diminishing returns)
        bonus_score = sum([min(count, profile["frequency_bonus_limit"]) for count in keyword_matches.values()])
        
        match_percentage = (unique_matches / total_possible) * 100
        
        # 4. Explainability / Ignored Content
        ignored_content = []
        if truncated:
            ignored_content.append({
                "reason": "Truncation Limit Reached",
                "message": f"This ATS stops reading after {profile['truncation_limit']} words. Your resume has {full_word_count}. The end of your resume was ignored.",
                "severity": "high"
            })

        # Check for "Keyword Dusting" (too many repetitions)
        over_optimized = [kw for kw, count in keyword_matches.items() if count > profile["frequency_bonus_limit"]]
        if over_optimized:
             ignored_content.append({
                "reason": "Keyword Over-Optimization",
                "message": f"Keywords like '{', '.join(over_optimized[:3])}' appear too many times. Most systems cap frequency credit at {profile['frequency_bonus_limit']}.",
                "severity": "low"
            })

        return {
            "ats_name": profile["name"],
            "simulated_score": round(match_percentage),
            "word_count": full_word_count,
            "truncated": truncated,
            "matches": list(keyword_matches.keys()),
            "ignored": ignored_content,
            "parsed_highlights": words[:50] # Snippet of what the ATS "sees"
        }

    @staticmethod
    def _flatten_resume(data):
        """Converts structured JSON to a flat string as an ATS parser would see it."""
        parts = []
        if 'header' in data:
            parts.append(str(data['header']))
        if 'summary' in data:
            parts.append(data['summary'])
        if 'skills' in data:
            parts.append(" ".join(data['skills']) if isinstance(data['skills'], list) else data['skills'])
        if 'experience' in data:
            for exp in data['experience']:
                parts.append(f"{exp.get('role')} {exp.get('company')} {' '.join(exp.get('achievements', []))}")
        return " ".join(parts)

    @staticmethod
    def _extract_keywords(text, as_set=False):
        """Extracts significant words, removing common stopwords."""
        if not text: return [] if not as_set else set()
        words = re.findall(r'\b\w{3,}\b', text.lower())
        stopwords = {
            'with', 'that', 'this', 'from', 'they', 'have', 'been', 'were',
            'seeking', 'expert', 'looking', 'work', 'working', 'responsibly', 'using',
            'for', 'and', 'the', 'his', 'her', 'their', 'our', 'your'
        }
        filtered = [w for w in words if w not in stopwords]
        return set(filtered) if as_set else filtered

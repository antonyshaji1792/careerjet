import re
import logging
import datetime

logger = logging.getLogger(__name__)

class BiasDetectionService:
    """
    Analyzes resume content for potential bias traps and legal risks.
    Focuses on ageism, gender-coded language, and sensitive personal attributes.
    """

    # GENDERED LANGUAGE (Based on research from Gaucher, Friesen, and Kay, 2011)
    MASCULINE_CODED = {
        "active", "adventurous", "aggressive", "ambitious", "analytical", "assertive",
        "athletic", "autonomous", "battle", "boast", "challenge", "champion",
        "competitive", "confident", "courage", "decisive", "decision", "determined",
        "dominant", "driven", "fearless", "fight", "force", "greedy", "head-strong",
        "hierarchy", "hostile", "impulsive", "independent", "individual", "intellectual",
        "lead", "logical", "objective", "opinion", "outspoken", "persist", "principle",
        "reckless", "self-confident", "self-reliant", "self-sufficient", "stubborn",
        "superior", "unreasonable", "rockstar", "ninja"
    }

    FEMININE_CODED = {
        "agreeable", "affectionate", "child", "cheer", "collaborative", "commit",
        "communal", "compassionate", "connected", "considerate", "cooperate",
        "dependence", "emotional", "empathic", "feels", "flatterable", "gentle",
        "honest", "interpersonal", "interdependent", "interpersonal", "kind",
        "kinship", "loyal", "modesty", "nag", "nurturing", "pleasant", "polite",
        "quiet", "responsive", "sensational", "sensitive", "shrew", "soft",
        "supportive", "sympathetic", "tender", "together", "trust", "understand",
        "warm", "whiny", "yield"
    }

    @staticmethod
    def analyze_bias(resume_data):
        """
        Scans resume data for bias markers.
        Returns a list of warnings and suggested neutral alternatives.
        """
        warnings = []
        
        # 1. Age Detection (Graduation Years)
        current_year = datetime.datetime.now().year
        for edu in resume_data.get('education', []):
            try:
                year_match = re.search(r'\d{4}', str(edu.get('year', '')))
                if year_match:
                    grad_year = int(year_match.group())
                    if current_year - grad_year > 20:
                        warnings.append({
                            "type": "age",
                            "severity": "medium",
                            "label": "Potential Age Bias",
                            "message": f"Listing a graduation year from {grad_year} (>20 years ago) can inadvertently lead to age-based screening bias.",
                            "suggestion": "Consider removing the graduation year and focusing on your degree and institution."
                        })
            except:
                continue

        # 2. Gender-Coded Language Scan
        all_text = BiasDetectionService._flatten_for_analysis(resume_data)
        words = set(re.findall(r'\b\w+\b', all_text.lower()))
        
        masc_found = words.intersection(BiasDetectionService.MASCULINE_CODED)
        fem_found = words.intersection(BiasDetectionService.FEMININE_CODED)
        
        if masc_found:
            warnings.append({
                "type": "gender",
                "severity": "low",
                "label": "Masculine-Coded Language",
                "message": f"Detected heavy usage of masculine-coded words: {', '.join(list(masc_found)[:3])}.",
                "suggestion": "While not inherently 'wrong', balanced language attracts a more diverse range of recruiters and companies."
            })
            
        if fem_found:
            warnings.append({
                "type": "gender",
                "severity": "low",
                "label": "Feminine-Coded Language",
                "message": f"Detected heavy usage of feminine-coded words: {', '.join(list(fem_found)[:3])}.",
                "suggestion": "Consider blending in more 'agentic' or outcome-focused verbs to balance the tone."
            })

        # 3. Legally Sensitive Attributes
        sensitive_patterns = {
            "marital_status": (r'\bmarried\b|\bsingle\b|\bdivorced\b|\bwidowed\b', "Marital Status"),
            "religion": (r'\bchristian\b|\bmuslim\b|\bjewish\b|\bhindu\b|\bcatholic\b', "Religious Affiliation"),
            "nationality": (r'\bnationality\b|\bcitizenship\b', "Nationality/Citizenship")
        }
        
        for key, (pattern, label) in sensitive_patterns.items():
            if re.search(pattern, all_text, re.I):
                warnings.append({
                    "type": "legal",
                    "severity": "high",
                    "label": f"Sensitive Attribute: {label}",
                    "message": f"Inclusion of {label.lower()} is generally not recommended as it is an 'EEO Protected Attribute' and can create legal risks for employers.",
                    "suggestion": f"Remove references to {label.lower()} unless specifically required for visa or security clearance purposes."
                })

        return warnings

    @staticmethod
    def _flatten_for_analysis(data):
        parts = [
            data.get('summary', ''),
            " ".join(data.get('skills', [])),
        ]
        for exp in data.get('experience', []):
            parts.append(exp.get('role', ''))
            parts.append(" ".join(exp.get('achievements', [])))
        return " ".join(parts)

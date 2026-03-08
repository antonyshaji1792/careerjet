"""
Resume Compliance and Safety Service
PII detection, bias detection, GDPR compliance, and export safety
"""

from typing import Dict, List, Optional, Set, Tuple
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ComplianceService:
    """
    Service for ensuring resume compliance with privacy and safety standards.
    Handles PII detection, bias language detection, GDPR compliance, and export safety.
    """
    
    # PII Patterns
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'date_of_birth': r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b',
        'address': r'\b\d+\s+[A-Za-z0-9\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir)\b',
        'zip_code': r'\b\d{5}(?:-\d{4})?\b',
        'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        'passport': r'\b[A-Z]{1,2}\d{6,9}\b',
        'drivers_license': r'\b[A-Z]{1,2}\d{6,8}\b'
    }
    
    # Sensitive personal identifiers
    SENSITIVE_KEYWORDS = {
        'age', 'birthday', 'birth date', 'marital status', 'married', 'single',
        'divorced', 'religion', 'religious', 'race', 'ethnicity', 'nationality',
        'citizenship', 'visa status', 'gender', 'sex', 'sexual orientation',
        'disability', 'health', 'medical', 'pregnant', 'pregnancy',
        'children', 'family status', 'political', 'union', 'veteran status'
    }
    
    # Bias language patterns
    BIAS_PATTERNS = {
        'age_bias': {
            'patterns': [
                r'\b(?:young|youthful|energetic|digital native)\b',
                r'\b(?:mature|experienced|seasoned|senior)\b',
                r'\b(?:\d+\s*years?\s*old)\b'
            ],
            'severity': 'medium',
            'message': 'Age-related language detected'
        },
        'gender_bias': {
            'patterns': [
                r'\b(?:he|him|his|she|her|hers)\b',
                r'\b(?:man|woman|male|female|guy|girl)\b',
                r'\b(?:chairman|chairwoman|salesman|saleswoman)\b'
            ],
            'severity': 'high',
            'message': 'Gender-specific language detected'
        },
        'cultural_bias': {
            'patterns': [
                r'\b(?:native|non-native)\s+(?:speaker|english)\b',
                r'\b(?:foreign|immigrant|alien)\b'
            ],
            'severity': 'high',
            'message': 'Cultural bias language detected'
        },
        'ability_bias': {
            'patterns': [
                r'\b(?:crazy|insane|psycho|lame|dumb|stupid)\b',
                r'\b(?:handicapped|disabled|crippled)\b'
            ],
            'severity': 'high',
            'message': 'Ableist language detected'
        }
    }
    
    # GDPR-safe fields
    GDPR_SAFE_FIELDS = {
        'professional_summary', 'skills', 'experience', 'education',
        'certifications', 'projects', 'achievements'
    }
    
    # Fields to exclude for GDPR
    GDPR_EXCLUDE_FIELDS = {
        'photo', 'date_of_birth', 'nationality', 'marital_status',
        'religion', 'political_affiliation', 'health_information'
    }
    
    def __init__(self):
        self.logger = logger
    
    def scan_resume(
        self,
        resume_data: Dict,
        check_pii: bool = True,
        check_bias: bool = True,
        check_gdpr: bool = True
    ) -> Dict:
        """
        Comprehensive compliance scan of resume.
        
        Args:
            resume_data: Resume content
            check_pii: Check for PII
            check_bias: Check for bias language
            check_gdpr: Check GDPR compliance
        
        Returns:
            Compliance report
        """
        try:
            issues = []
            warnings = []
            
            # Convert resume to text
            resume_text = self._resume_to_text(resume_data)
            
            # PII Detection
            if check_pii:
                pii_results = self.detect_pii(resume_text)
                if pii_results['found']:
                    issues.extend(pii_results['issues'])
            
            # Bias Detection
            if check_bias:
                bias_results = self.detect_bias(resume_text)
                if bias_results['found']:
                    issues.extend(bias_results['issues'])
            
            # GDPR Compliance
            if check_gdpr:
                gdpr_results = self.check_gdpr_compliance(resume_data)
                if not gdpr_results['compliant']:
                    warnings.extend(gdpr_results['warnings'])
            
            # Overall compliance
            is_compliant = len(issues) == 0
            
            return {
                'compliant': is_compliant,
                'issues': issues,
                'warnings': warnings,
                'summary': {
                    'total_issues': len(issues),
                    'critical_issues': len([i for i in issues if i.get('severity') == 'critical']),
                    'high_issues': len([i for i in issues if i.get('severity') == 'high']),
                    'medium_issues': len([i for i in issues if i.get('severity') == 'medium'])
                },
                'scanned_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Compliance scan failed: {str(e)}")
            raise
    
    def detect_pii(self, text: str) -> Dict:
        """
        Detect personally identifiable information.
        
        Args:
            text: Text to scan
        
        Returns:
            PII detection results
        """
        try:
            found_pii = []
            
            for pii_type, pattern in self.PII_PATTERNS.items():
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    found_pii.append({
                        'type': pii_type,
                        'value': match.group(),
                        'position': match.start(),
                        'severity': self._get_pii_severity(pii_type),
                        'message': f'{pii_type.replace("_", " ").title()} detected',
                        'recommendation': f'Remove or mask {pii_type.replace("_", " ")}'
                    })
            
            # Check for sensitive keywords
            for keyword in self.SENSITIVE_KEYWORDS:
                if keyword in text.lower():
                    found_pii.append({
                        'type': 'sensitive_keyword',
                        'value': keyword,
                        'position': text.lower().find(keyword),
                        'severity': 'medium',
                        'message': f'Sensitive keyword "{keyword}" detected',
                        'recommendation': f'Consider removing "{keyword}"'
                    })
            
            return {
                'found': len(found_pii) > 0,
                'count': len(found_pii),
                'issues': found_pii
            }
            
        except Exception as e:
            self.logger.error(f"PII detection failed: {str(e)}")
            raise
    
    def detect_bias(self, text: str) -> Dict:
        """
        Detect biased language.
        
        Args:
            text: Text to scan
        
        Returns:
            Bias detection results
        """
        try:
            found_bias = []
            
            for bias_type, config in self.BIAS_PATTERNS.items():
                for pattern in config['patterns']:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        found_bias.append({
                            'type': bias_type,
                            'value': match.group(),
                            'position': match.start(),
                            'severity': config['severity'],
                            'message': config['message'],
                            'recommendation': self._get_bias_recommendation(bias_type, match.group())
                        })
            
            return {
                'found': len(found_bias) > 0,
                'count': len(found_bias),
                'issues': found_bias
            }
            
        except Exception as e:
            self.logger.error(f"Bias detection failed: {str(e)}")
            raise
    
    def check_gdpr_compliance(self, resume_data: Dict) -> Dict:
        """
        Check GDPR compliance.
        
        Args:
            resume_data: Resume content
        
        Returns:
            GDPR compliance results
        """
        try:
            warnings = []
            
            # Check for excluded fields
            for field in self.GDPR_EXCLUDE_FIELDS:
                if field in resume_data:
                    warnings.append({
                        'field': field,
                        'severity': 'high',
                        'message': f'GDPR-sensitive field "{field}" present',
                        'recommendation': f'Remove "{field}" for GDPR compliance'
                    })
            
            # Check for PII in text fields
            for field, value in resume_data.items():
                if isinstance(value, str):
                    pii_results = self.detect_pii(value)
                    if pii_results['found']:
                        warnings.append({
                            'field': field,
                            'severity': 'medium',
                            'message': f'PII detected in "{field}"',
                            'recommendation': 'Mask or remove PII'
                        })
            
            return {
                'compliant': len(warnings) == 0,
                'warnings': warnings
            }
            
        except Exception as e:
            self.logger.error(f"GDPR check failed: {str(e)}")
            raise
    
    def mask_pii(
        self,
        text: str,
        mask_char: str = '*',
        preserve_format: bool = True
    ) -> Tuple[str, List[Dict]]:
        """
        Mask PII in text.
        
        Args:
            text: Text to mask
            mask_char: Character to use for masking
            preserve_format: Preserve format (e.g., xxx-xx-xxxx for SSN)
        
        Returns:
            Tuple of (masked_text, masked_items)
        """
        try:
            masked_text = text
            masked_items = []
            
            # Sort patterns by priority (most specific first)
            priority_order = ['ssn', 'credit_card', 'email', 'phone', 'address']
            
            for pii_type in priority_order:
                if pii_type in self.PII_PATTERNS:
                    pattern = self.PII_PATTERNS[pii_type]
                    matches = list(re.finditer(pattern, masked_text, re.IGNORECASE))
                    
                    # Process in reverse to maintain positions
                    for match in reversed(matches):
                        original = match.group()
                        
                        if preserve_format:
                            masked = self._mask_with_format(original, pii_type, mask_char)
                        else:
                            masked = mask_char * len(original)
                        
                        masked_text = masked_text[:match.start()] + masked + masked_text[match.end():]
                        
                        masked_items.append({
                            'type': pii_type,
                            'original_length': len(original),
                            'position': match.start()
                        })
            
            return masked_text, masked_items
            
        except Exception as e:
            self.logger.error(f"PII masking failed: {str(e)}")
            raise
    
    def generate_gdpr_safe_resume(self, resume_data: Dict) -> Dict:
        """
        Generate GDPR-compliant version of resume.
        
        Args:
            resume_data: Original resume data
        
        Returns:
            GDPR-safe resume
        """
        try:
            safe_resume = {}
            
            # Include only safe fields
            for field, value in resume_data.items():
                if field in self.GDPR_SAFE_FIELDS or field not in self.GDPR_EXCLUDE_FIELDS:
                    # Mask PII in text fields
                    if isinstance(value, str):
                        masked_value, _ = self.mask_pii(value)
                        safe_resume[field] = masked_value
                    elif isinstance(value, list):
                        safe_resume[field] = self._mask_list_items(value)
                    elif isinstance(value, dict):
                        safe_resume[field] = self._mask_dict_items(value)
                    else:
                        safe_resume[field] = value
            
            # Add compliance metadata
            safe_resume['_compliance'] = {
                'gdpr_safe': True,
                'pii_masked': True,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return safe_resume
            
        except Exception as e:
            self.logger.error(f"GDPR-safe generation failed: {str(e)}")
            raise
    
    def generate_export_safe_resume(
        self,
        resume_data: Dict,
        export_format: str = 'pdf'
    ) -> Dict:
        """
        Generate export-safe resume with appropriate masking.
        
        Args:
            resume_data: Original resume data
            export_format: Export format (pdf, docx, txt)
        
        Returns:
            Export-safe resume
        """
        try:
            # Start with GDPR-safe version
            safe_resume = self.generate_gdpr_safe_resume(resume_data)
            
            # Additional export-specific processing
            if export_format == 'pdf':
                # PDF-specific: Remove metadata
                safe_resume.pop('_metadata', None)
                safe_resume.pop('_internal', None)
            
            elif export_format == 'docx':
                # DOCX-specific: Sanitize formatting
                safe_resume = self._sanitize_formatting(safe_resume)
            
            elif export_format == 'txt':
                # TXT-specific: Plain text only
                safe_resume = self._to_plain_text(safe_resume)
            
            # Add export metadata
            safe_resume['_export'] = {
                'format': export_format,
                'export_safe': True,
                'exported_at': datetime.utcnow().isoformat()
            }
            
            return safe_resume
            
        except Exception as e:
            self.logger.error(f"Export-safe generation failed: {str(e)}")
            raise
    
    def validate_compliance_policy(self, resume_data: Dict, policy: str = 'standard') -> Dict:
        """
        Validate resume against compliance policy.
        
        Args:
            resume_data: Resume data
            policy: Policy name (standard, strict, gdpr, export)
        
        Returns:
            Validation results
        """
        try:
            policies = {
                'standard': {
                    'check_pii': True,
                    'check_bias': True,
                    'check_gdpr': False,
                    'max_issues': 5
                },
                'strict': {
                    'check_pii': True,
                    'check_bias': True,
                    'check_gdpr': True,
                    'max_issues': 0
                },
                'gdpr': {
                    'check_pii': True,
                    'check_bias': False,
                    'check_gdpr': True,
                    'max_issues': 0
                },
                'export': {
                    'check_pii': True,
                    'check_bias': True,
                    'check_gdpr': True,
                    'max_issues': 0
                }
            }
            
            policy_config = policies.get(policy, policies['standard'])
            
            # Run scan
            scan_results = self.scan_resume(
                resume_data,
                check_pii=policy_config['check_pii'],
                check_bias=policy_config['check_bias'],
                check_gdpr=policy_config['check_gdpr']
            )
            
            # Validate against policy
            total_issues = scan_results['summary']['total_issues']
            passes_policy = total_issues <= policy_config['max_issues']
            
            return {
                'policy': policy,
                'passes': passes_policy,
                'scan_results': scan_results,
                'required_actions': self._generate_required_actions(scan_results, policy)
            }
            
        except Exception as e:
            self.logger.error(f"Policy validation failed: {str(e)}")
            raise
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _resume_to_text(self, resume_data: Dict) -> str:
        """Convert resume data to text for scanning"""
        text_parts = []
        
        def extract_text(obj):
            if isinstance(obj, str):
                text_parts.append(obj)
            elif isinstance(obj, dict):
                for value in obj.values():
                    extract_text(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_text(item)
        
        extract_text(resume_data)
        return ' '.join(text_parts)
    
    def _get_pii_severity(self, pii_type: str) -> str:
        """Get severity level for PII type"""
        critical = ['ssn', 'credit_card', 'passport', 'drivers_license']
        high = ['email', 'phone', 'address', 'date_of_birth']
        
        if pii_type in critical:
            return 'critical'
        elif pii_type in high:
            return 'high'
        else:
            return 'medium'
    
    def _get_bias_recommendation(self, bias_type: str, matched_text: str) -> str:
        """Get recommendation for bias issue"""
        recommendations = {
            'age_bias': 'Use age-neutral language. Focus on experience and skills.',
            'gender_bias': 'Use gender-neutral pronouns (they/them) or rephrase.',
            'cultural_bias': 'Use inclusive language. Avoid cultural assumptions.',
            'ability_bias': 'Use respectful, person-first language.'
        }
        return recommendations.get(bias_type, 'Review and revise language')
    
    def _mask_with_format(self, text: str, pii_type: str, mask_char: str) -> str:
        """Mask PII while preserving format"""
        if pii_type == 'ssn':
            return f'{mask_char*3}-{mask_char*2}-{mask_char*4}'
        elif pii_type == 'phone':
            return f'({mask_char*3}) {mask_char*3}-{mask_char*4}'
        elif pii_type == 'email':
            parts = text.split('@')
            if len(parts) == 2:
                return f'{mask_char*3}@{parts[1]}'
        
        return mask_char * len(text)
    
    def _mask_list_items(self, items: List) -> List:
        """Mask PII in list items"""
        masked_items = []
        for item in items:
            if isinstance(item, str):
                masked, _ = self.mask_pii(item)
                masked_items.append(masked)
            elif isinstance(item, dict):
                masked_items.append(self._mask_dict_items(item))
            else:
                masked_items.append(item)
        return masked_items
    
    def _mask_dict_items(self, data: Dict) -> Dict:
        """Mask PII in dictionary items"""
        masked_dict = {}
        for key, value in data.items():
            if key in self.GDPR_EXCLUDE_FIELDS:
                continue
            
            if isinstance(value, str):
                masked, _ = self.mask_pii(value)
                masked_dict[key] = masked
            elif isinstance(value, list):
                masked_dict[key] = self._mask_list_items(value)
            elif isinstance(value, dict):
                masked_dict[key] = self._mask_dict_items(value)
            else:
                masked_dict[key] = value
        
        return masked_dict
    
    def _sanitize_formatting(self, resume_data: Dict) -> Dict:
        """Sanitize formatting for export"""
        # Remove special characters, clean up formatting
        sanitized = {}
        for key, value in resume_data.items():
            if isinstance(value, str):
                # Remove special formatting characters
                cleaned = re.sub(r'[^\w\s\-.,;:()\'\"]+', '', value)
                sanitized[key] = cleaned
            else:
                sanitized[key] = value
        return sanitized
    
    def _to_plain_text(self, resume_data: Dict) -> Dict:
        """Convert to plain text format"""
        # Simplified version for plain text export
        plain = {}
        for key, value in resume_data.items():
            if isinstance(value, (str, int, float)):
                plain[key] = str(value)
            elif isinstance(value, list):
                plain[key] = ', '.join(str(v) for v in value)
        return plain
    
    def _generate_required_actions(self, scan_results: Dict, policy: str) -> List[str]:
        """Generate list of required actions"""
        actions = []
        
        for issue in scan_results['issues']:
            if issue.get('severity') in ['critical', 'high']:
                actions.append(issue.get('recommendation', 'Review and fix issue'))
        
        for warning in scan_results['warnings']:
            if warning.get('severity') == 'high':
                actions.append(warning.get('recommendation', 'Review and fix warning'))
        
        return list(set(actions))  # Remove duplicates

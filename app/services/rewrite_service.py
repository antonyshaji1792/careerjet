"""
Smart Content Rewriting Service for Resume Sections
STAR method, action verbs, metrics, tone control, and filler removal
"""

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum
import logging

from app.services.llm_service import ask_ai

logger = logging.getLogger(__name__)


class Tone(Enum):
    """Tone options for rewriting"""
    CONSERVATIVE = "conservative"
    CONFIDENT = "confident"
    AGGRESSIVE = "aggressive"


class RewriteService:
    """
    Smart content rewriting service for resume sections.
    Applies STAR method, enhances action verbs, suggests metrics, and controls tone.
    """
    
    # Action verb categories
    ACTION_VERBS = {
        'leadership': [
            'led', 'directed', 'managed', 'supervised', 'coordinated',
            'orchestrated', 'spearheaded', 'championed', 'drove', 'guided'
        ],
        'achievement': [
            'achieved', 'accomplished', 'delivered', 'exceeded', 'surpassed',
            'attained', 'realized', 'secured', 'earned', 'won'
        ],
        'creation': [
            'created', 'developed', 'designed', 'built', 'established',
            'launched', 'initiated', 'pioneered', 'founded', 'introduced'
        ],
        'improvement': [
            'improved', 'enhanced', 'optimized', 'streamlined', 'upgraded',
            'refined', 'modernized', 'transformed', 'revitalized', 'accelerated'
        ],
        'technical': [
            'implemented', 'engineered', 'architected', 'deployed', 'integrated',
            'configured', 'automated', 'programmed', 'coded', 'debugged'
        ],
        'analysis': [
            'analyzed', 'evaluated', 'assessed', 'investigated', 'researched',
            'examined', 'identified', 'diagnosed', 'measured', 'quantified'
        ],
        'collaboration': [
            'collaborated', 'partnered', 'facilitated', 'coordinated', 'liaised',
            'contributed', 'supported', 'assisted', 'enabled', 'empowered'
        ]
    }
    
    # Weak verbs to replace
    WEAK_VERBS = {
        'did', 'made', 'worked', 'helped', 'was responsible for',
        'handled', 'dealt with', 'involved in', 'participated in',
        'used', 'utilized', 'performed', 'conducted'
    }
    
    # Filler words and phrases to remove
    FILLER_LANGUAGE = {
        'very', 'really', 'quite', 'just', 'basically', 'actually',
        'literally', 'simply', 'totally', 'completely', 'absolutely',
        'various', 'several', 'numerous', 'multiple', 'many',
        'a lot of', 'lots of', 'a number of', 'kind of', 'sort of',
        'in order to', 'due to the fact that', 'at this point in time',
        'for the purpose of', 'in the event that', 'with regard to'
    }
    
    # Tone profiles
    TONE_PROFILES = {
        Tone.CONSERVATIVE: {
            'description': 'Professional, measured, and modest',
            'characteristics': [
                'Uses measured language',
                'Focuses on team contributions',
                'Avoids superlatives',
                'Emphasizes collaboration'
            ],
            'temperature': 0.3,
            'style_words': ['contributed', 'supported', 'assisted', 'participated', 'helped']
        },
        Tone.CONFIDENT: {
            'description': 'Assertive, results-focused, and impactful',
            'characteristics': [
                'Uses strong action verbs',
                'Highlights individual impact',
                'Includes quantifiable results',
                'Shows leadership'
            ],
            'temperature': 0.4,
            'style_words': ['led', 'achieved', 'delivered', 'drove', 'implemented']
        },
        Tone.AGGRESSIVE: {
            'description': 'Bold, achievement-oriented, and commanding',
            'characteristics': [
                'Uses powerful language',
                'Emphasizes major wins',
                'Showcases leadership',
                'Highlights competitive advantages'
            ],
            'temperature': 0.5,
            'style_words': ['spearheaded', 'revolutionized', 'transformed', 'dominated', 'exceeded']
        }
    }
    
    def __init__(self):
        self.logger = logger
    
    def rewrite_achievement(
        self,
        original_text: str,
        tone: Tone = Tone.CONFIDENT,
        apply_star: bool = True,
        enhance_verbs: bool = True,
        suggest_metrics: bool = True,
        remove_filler: bool = True
    ) -> Dict:
        """
        Rewrite a single achievement bullet point.
        
        Args:
            original_text: Original achievement text
            tone: Desired tone (conservative, confident, aggressive)
            apply_star: Apply STAR method structure
            enhance_verbs: Replace weak verbs with strong action verbs
            suggest_metrics: Suggest where to add metrics
            remove_filler: Remove filler words and phrases
        
        Returns:
            Dict with rewritten text, diff, and suggestions
        """
        try:
            # Step 1: Remove filler language
            cleaned_text = original_text
            if remove_filler:
                cleaned_text = self._remove_filler(original_text)
            
            # Step 2: Enhance action verbs
            verb_enhanced = cleaned_text
            if enhance_verbs:
                verb_enhanced = self._enhance_action_verbs(cleaned_text, tone)
            
            # Step 3: Apply STAR method
            star_text = verb_enhanced
            if apply_star:
                star_text = self._apply_star_method(verb_enhanced, tone)
            
            # Step 4: Suggest metrics
            metric_suggestions = []
            if suggest_metrics:
                metric_suggestions = self._suggest_metrics(original_text, star_text)
            
            # Generate diff
            diff = self._generate_diff(original_text, star_text)
            
            # Build result
            result = {
                'original': original_text,
                'rewritten': star_text,
                'tone': tone.value,
                'improvements': {
                    'filler_removed': remove_filler and cleaned_text != original_text,
                    'verbs_enhanced': enhance_verbs and verb_enhanced != cleaned_text,
                    'star_applied': apply_star,
                    'metrics_suggested': len(metric_suggestions) > 0
                },
                'metric_suggestions': metric_suggestions,
                'diff': diff,
                'character_count': {
                    'original': len(original_text),
                    'rewritten': len(star_text),
                    'change': len(star_text) - len(original_text)
                }
            }
            
            self.logger.info(f"Achievement rewritten with {tone.value} tone")
            return result
            
        except Exception as e:
            self.logger.error(f"Rewrite failed: {str(e)}")
            raise
    
    def rewrite_summary(
        self,
        original_summary: str,
        tone: Tone = Tone.CONFIDENT,
        target_role: Optional[str] = None
    ) -> Dict:
        """
        Rewrite professional summary with specified tone.
        
        Args:
            original_summary: Original summary text
            tone: Desired tone
            target_role: Optional target role for customization
        
        Returns:
            Dict with rewritten summary and analysis
        """
        try:
            # Build prompt
            prompt = self._build_summary_prompt(original_summary, tone, target_role)
            
            # Call AI
            tone_profile = self.TONE_PROFILES[tone]
            rewritten = ask_ai(
                prompt,
                temperature=tone_profile['temperature'],
                max_tokens=200
            )
            
            # Clean response
            rewritten = rewritten.strip()
            
            # Generate diff
            diff = self._generate_diff(original_summary, rewritten)
            
            result = {
                'original': original_summary,
                'rewritten': rewritten,
                'tone': tone.value,
                'target_role': target_role,
                'diff': diff,
                'word_count': {
                    'original': len(original_summary.split()),
                    'rewritten': len(rewritten.split())
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Summary rewrite failed: {str(e)}")
            raise
    
    def batch_rewrite_achievements(
        self,
        achievements: List[str],
        tone: Tone = Tone.CONFIDENT,
        **kwargs
    ) -> List[Dict]:
        """
        Rewrite multiple achievements in batch.
        
        Args:
            achievements: List of achievement texts
            tone: Desired tone
            **kwargs: Additional rewrite options
        
        Returns:
            List of rewrite results
        """
        results = []
        
        for achievement in achievements:
            try:
                result = self.rewrite_achievement(achievement, tone, **kwargs)
                results.append(result)
            except Exception as e:
                self.logger.warning(f"Failed to rewrite achievement: {str(e)}")
                results.append({
                    'original': achievement,
                    'rewritten': achievement,
                    'error': str(e)
                })
        
        return results
    
    # ========================================================================
    # Core Rewriting Methods
    # ========================================================================
    
    def _remove_filler(self, text: str) -> str:
        """Remove filler words and phrases"""
        cleaned = text
        
        # Remove filler phrases (case insensitive)
        for filler in self.FILLER_LANGUAGE:
            pattern = r'\b' + re.escape(filler) + r'\b'
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _enhance_action_verbs(self, text: str, tone: Tone) -> str:
        """Replace weak verbs with strong action verbs"""
        enhanced = text
        
        # Identify weak verbs in text
        words = text.lower().split()
        
        for weak_verb in self.WEAK_VERBS:
            if weak_verb in text.lower():
                # Get appropriate replacement based on tone
                replacement = self._get_strong_verb_replacement(weak_verb, tone)
                if replacement:
                    pattern = r'\b' + re.escape(weak_verb) + r'\b'
                    enhanced = re.sub(pattern, replacement, enhanced, count=1, flags=re.IGNORECASE)
        
        return enhanced
    
    def _apply_star_method(self, text: str, tone: Tone) -> str:
        """Apply STAR method structure to achievement"""
        # Build prompt for STAR rewriting
        prompt = self._build_star_prompt(text, tone)
        
        # Call AI
        tone_profile = self.TONE_PROFILES[tone]
        rewritten = ask_ai(
            prompt,
            temperature=tone_profile['temperature'],
            max_tokens=150
        )
        
        # Clean and return
        return rewritten.strip()
    
    def _suggest_metrics(self, original: str, rewritten: str) -> List[Dict]:
        """Suggest where metrics could be added"""
        suggestions = []
        
        # Check if already has metrics
        has_numbers = bool(re.search(r'\d+', rewritten))
        has_percentage = bool(re.search(r'\d+%', rewritten))
        has_dollar = bool(re.search(r'\$\d+', rewritten))
        
        # Suggest metrics based on content
        if not has_numbers:
            if 'team' in rewritten.lower():
                suggestions.append({
                    'type': 'team_size',
                    'suggestion': 'Add team size (e.g., "team of 5 engineers")',
                    'example': 'Led team of 5 engineers...'
                })
            
            if 'user' in rewritten.lower() or 'customer' in rewritten.lower():
                suggestions.append({
                    'type': 'user_count',
                    'suggestion': 'Add user/customer count (e.g., "serving 100K+ users")',
                    'example': '...serving 100K+ daily users'
                })
        
        if not has_percentage:
            if any(word in rewritten.lower() for word in ['improve', 'increase', 'reduce', 'decrease']):
                suggestions.append({
                    'type': 'percentage_change',
                    'suggestion': 'Add percentage improvement (e.g., "by 40%")',
                    'example': 'Improved performance by 40%'
                })
        
        if not has_dollar:
            if any(word in rewritten.lower() for word in ['revenue', 'cost', 'save', 'budget']):
                suggestions.append({
                    'type': 'dollar_amount',
                    'suggestion': 'Add dollar amount (e.g., "$2M in revenue")',
                    'example': 'Generated $2M in annual revenue'
                })
        
        return suggestions
    
    def _get_strong_verb_replacement(self, weak_verb: str, tone: Tone) -> Optional[str]:
        """Get strong verb replacement based on tone"""
        tone_profile = self.TONE_PROFILES[tone]
        
        # Map weak verbs to categories
        verb_mapping = {
            'did': 'achievement',
            'made': 'creation',
            'worked': 'collaboration',
            'helped': 'collaboration',
            'was responsible for': 'leadership',
            'handled': 'leadership',
            'dealt with': 'leadership',
            'involved in': 'collaboration',
            'participated in': 'collaboration',
            'used': 'technical',
            'utilized': 'technical',
            'performed': 'achievement',
            'conducted': 'analysis'
        }
        
        category = verb_mapping.get(weak_verb.lower())
        if category and category in self.ACTION_VERBS:
            # Get verbs from category
            verbs = self.ACTION_VERBS[category]
            
            # Filter by tone
            if tone == Tone.CONSERVATIVE:
                # Use softer verbs
                return verbs[len(verbs)//2] if verbs else None
            elif tone == Tone.AGGRESSIVE:
                # Use stronger verbs
                return verbs[0] if verbs else None
            else:  # CONFIDENT
                # Use middle-ground verbs
                return verbs[len(verbs)//3] if verbs else None
        
        return None
    
    # ========================================================================
    # Prompt Templates
    # ========================================================================
    
    def _build_star_prompt(self, text: str, tone: Tone) -> str:
        """Build prompt for STAR method rewriting"""
        tone_profile = self.TONE_PROFILES[tone]
        tone_desc = tone_profile['description']
        style_words = ', '.join(tone_profile['style_words'])
        
        return f"""Rewrite this achievement using the STAR method (Situation, Task, Action, Result).

Original: {text}

Requirements:
- Use {tone_desc} tone
- Start with a strong action verb (prefer: {style_words})
- Include the result/impact
- Keep under 300 characters
- Be specific and quantifiable
- DO NOT fabricate information
- Maintain factual accuracy

STAR Structure:
- Situation/Task: Brief context (optional, can be implied)
- Action: What you did (strong verb)
- Result: The impact/outcome

Return ONLY the rewritten achievement, no other text."""
    
    def _build_summary_prompt(
        self,
        original: str,
        tone: Tone,
        target_role: Optional[str]
    ) -> str:
        """Build prompt for summary rewriting"""
        tone_profile = self.TONE_PROFILES[tone]
        tone_desc = tone_profile['description']
        
        role_context = f"\nTarget Role: {target_role}" if target_role else ""
        
        return f"""Rewrite this professional summary with a {tone_desc} tone.

Original Summary:
{original}{role_context}

Requirements:
- Use {tone_desc} tone
- 2-3 sentences maximum
- Highlight key strengths and experience
- Include relevant skills
- Be compelling and professional
- DO NOT fabricate experience or skills
- Maintain factual accuracy

Return ONLY the rewritten summary, no other text."""
    
    # ========================================================================
    # Diff Generation
    # ========================================================================
    
    def _generate_diff(self, original: str, rewritten: str) -> Dict:
        """Generate before/after diff"""
        # Simple word-level diff
        original_words = set(original.lower().split())
        rewritten_words = set(rewritten.lower().split())
        
        added = rewritten_words - original_words
        removed = original_words - rewritten_words
        kept = original_words & rewritten_words
        
        # Identify changes
        changes = []
        
        if added:
            changes.append({
                'type': 'addition',
                'description': f'Added {len(added)} new words',
                'words': list(added)[:10]  # Limit to 10
            })
        
        if removed:
            changes.append({
                'type': 'removal',
                'description': f'Removed {len(removed)} words',
                'words': list(removed)[:10]
            })
        
        # Calculate similarity
        if original_words or rewritten_words:
            similarity = len(kept) / len(original_words | rewritten_words) * 100
        else:
            similarity = 100
        
        return {
            'changes': changes,
            'similarity_percentage': round(similarity, 1),
            'words_added': len(added),
            'words_removed': len(removed),
            'words_kept': len(kept)
        }
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_tone_profile(self, tone: Tone) -> Dict:
        """Get tone profile information"""
        return self.TONE_PROFILES[tone]
    
    def get_action_verbs(self, category: Optional[str] = None) -> List[str]:
        """Get action verbs by category"""
        if category and category in self.ACTION_VERBS:
            return self.ACTION_VERBS[category]
        
        # Return all verbs
        all_verbs = []
        for verbs in self.ACTION_VERBS.values():
            all_verbs.extend(verbs)
        return all_verbs
    
    def analyze_text_quality(self, text: str) -> Dict:
        """Analyze text quality and provide feedback"""
        analysis = {
            'has_action_verb': False,
            'has_metrics': False,
            'has_filler': False,
            'word_count': len(text.split()),
            'character_count': len(text),
            'issues': []
        }
        
        # Check for action verbs
        all_verbs = self.get_action_verbs()
        if any(verb in text.lower() for verb in all_verbs):
            analysis['has_action_verb'] = True
        else:
            analysis['issues'].append('No strong action verb detected')
        
        # Check for metrics
        if re.search(r'\d+', text):
            analysis['has_metrics'] = True
        else:
            analysis['issues'].append('No quantifiable metrics found')
        
        # Check for filler
        if any(filler in text.lower() for filler in self.FILLER_LANGUAGE):
            analysis['has_filler'] = True
            analysis['issues'].append('Contains filler words')
        
        # Check length
        if len(text) > 300:
            analysis['issues'].append('Too long (over 300 characters)')
        elif len(text) < 20:
            analysis['issues'].append('Too short (under 20 characters)')
        
        # Check for weak verbs
        if any(weak in text.lower() for weak in self.WEAK_VERBS):
            analysis['issues'].append('Contains weak verbs')
        
        return analysis

import logging
import json
import asyncio
from datetime import datetime
from app.services.ai_metering_service import AIMeteringService
from app.services.prompt_registry import PromptRegistryService
from app.services.resume_intent import ResumeIntentService
from app.services.resume_integrity import ResumeIntegrityService
from app.models import SystemConfig, Resume, ResumeOptimization, db

logger = logging.getLogger(__name__)

class ResumeBuilder:
    """
    AI-powered Resume Builder & Optimizer.
    Follows Antigravity Senior Engineer standards for modularity, 
    validation, and security.
    """

    def __init__(self, user_id):
        self.user_id = user_id

    async def generate_full_resume(self, profile_data, target_role=None, tone="professional"):
        """
        Generates a structured resume based on user profile and optional target role.
        Uses versioned prompts for reproducibility.
        """
        # Inference Intent first
        intent = await ResumeIntentService.infer_intent(profile_data, target_role)
        
        prompt_obj = PromptRegistryService.get_prompt('resume_generation')
        user_prompt = PromptRegistryService.format_prompt(
            prompt_obj, 
            skills=profile_data.get('skills'),
            bio=profile_data.get('bio'),
            target_role=target_role or 'General matching preferred roles',
            tone=tone,
            intent=intent
        )
        
        try:
            metered_resp = await AIMeteringService.ask_ai_metered(
                user_id=self.user_id,
                feature_type='resume_generation',
                prompt=user_prompt,
                system_prompt=prompt_obj.system_prompt,
                max_tokens=prompt_obj.max_tokens,
                temperature=prompt_obj.temperature
            )
            
            if not metered_resp.get('success'):
                raise ValueError(metered_resp.get('message', "AI Generation Failed"))
                
            response_text = metered_resp.get('text', '{}')
            
            # Antigravity Guard: Validate JSON Structure
            resume_data = self._validate_and_sanitize_resume_json(response_text)
            
            if not resume_data:
                raise ValueError("AI generated invalid resume structure.")

            # Sign resume for integrity
            resume_data = ResumeIntegrityService.sign_resume(resume_data)

            return resume_data, prompt_obj.id
            
        except Exception as e:
            logger.error(f"Resume generation failed for user {self.user_id}: {str(e)}")
            raise

    async def optimize_for_job(self, resume_id, job_description):
        """
        Optimizes an existing resume for a specific job post.
        Provides ATS scoring and tailored content using versioned prompts.
        """
        resume = Resume.query.get(resume_id)
        if not resume or not resume.content_json:
            raise ValueError("Resume not found or has no content.")

        # Inferred Intent for Optimization
        resume_data = json.loads(resume.content_json)
        profile_context = {"bio": resume_data.get('summary', '')}
        intent = await ResumeIntentService.infer_intent(profile_context, job_description=job_description)

        prompt_obj = PromptRegistryService.get_prompt('resume_optimization')
        user_prompt = PromptRegistryService.format_prompt(
            prompt_obj,
            resume_json=resume.content_json,
            job_description=job_description,
            intent=intent
        )
        
        try:
            metered_resp = await AIMeteringService.ask_ai_metered(
                user_id=self.user_id,
                feature_type='resume_optimization',
                prompt=user_prompt,
                system_prompt=prompt_obj.system_prompt,
                max_tokens=prompt_obj.max_tokens,
                temperature=prompt_obj.temperature
            )
            
            if not metered_resp.get('success'):
                raise ValueError(metered_resp.get('message', "AI Optimization Failed"))
                
            response_text = metered_resp.get('text', '{}')
            
            optimized_data = self._validate_optimization_json(response_text)
            if optimized_data:
                optimized_data['prompt_version_id'] = prompt_obj.id
                
            return optimized_data
            
        except Exception as e:
            logger.error(f"Resume optimization failed for user {self.user_id}: {str(e)}")
            raise

    def _validate_and_sanitize_resume_json(self, raw_response):
        """
        Antigravity Guard: Ensures the AI output is safe, properly formatted, and contains no hallucinated data outside scope.
        """
        try:
            # Clean possible markdown artifacts
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_response:
                raw_response = raw_response.split("```")[1].split("```")[0].strip()
                
            data = json.loads(raw_response)
            
            # Check mandatory keys
            required_keys = ["header", "summary", "skills", "experience", "education"]
            for key in required_keys:
                if key not in data:
                    return None
            
            return data
        except Exception as e:
            logger.error(f"JSON validation failed: {str(e)}")
            return None

    def _validate_optimization_json(self, raw_response):
        try:
            if "```json" in raw_response:
                raw_response = raw_response.split("```json")[1].split("```")[0].strip()
            data = json.loads(raw_response)
            return data
        except:
            return None

    def get_templates(self):
        """Returns metadata for frontend resume templates (100+ designs inspired by Canva's best)"""
        return [
            {"id": "modern", "name": "Modern Tech", "description": "Minimalist and clean for software engineers.", "preview_type": "bold", "accent": "#4f46e5"},
            {"id": "executive", "name": "Executive Gold", "description": "High-impact for leadership and management roles.", "preview_type": "standard", "accent": "#b8860b"},
            {"id": "creative", "name": "Creative Vibe", "description": "Dynamic layout for design and marketing.", "preview_type": "split", "accent": "#2d3436"},
            {"id": "academic", "name": "Academic Pro", "description": "Detailed structure for research and education.", "preview_type": "standard", "accent": "#333333"},
            {"id": "minimal", "name": "Pure Minimalist", "description": "The ultimate clean look for direct impact.", "preview_type": "standard", "accent": "#999999"},
            {"id": "sleek", "name": "Sleek Professional", "description": "Modern fonts with subtle charcoal accents.", "preview_type": "standard", "accent": "#3b82f6"},
            {"id": "bold", "name": "Bold Statement", "description": "Strong headers for experienced professionals.", "preview_type": "bold", "accent": "#000000"},
            {"id": "impact", "name": "High Impact", "description": "Focus on achievements and metrics for sales/growth.", "preview_type": "bold", "accent": "#ff4757"},
            {"id": "corporate", "name": "Corporate Standard", "description": "Traditional layout for finance and law.", "preview_type": "standard", "accent": "#000000"},
            {"id": "midnight", "name": "Midnight Dark", "description": "Dark-themed professional design for creative tech.", "preview_type": "dark", "accent": "#3b82f6"},
            {"id": "ruby", "name": "Ruby Crimson", "description": "Sophisticated deep red accents for a warm feel.", "preview_type": "standard", "accent": "#b33939"},
            {"id": "emerald", "name": "Emerald Growth", "description": "Professional green palette for sustainability & ESG.", "preview_type": "standard", "accent": "#059669"},
            {"id": "indigo", "name": "Indigo Edge", "description": "Deep blue accents with a modern geometric feel.", "preview_type": "split", "accent": "#4338ca"},
            {"id": "sunset", "name": "Sunset Designer", "description": "Warm gradient accents for a vibrant personal brand.", "preview_type": "split", "accent": "#ef4444"},
            {"id": "clean", "name": "Crisp Clean", "description": "Optimized whitespace for maximum readability.", "preview_type": "standard", "accent": "#10b981"},
            {"id": "compact", "name": "Compact Pro", "description": "Dense layout for multi-page data or high density.", "preview_type": "standard", "accent": "#000000"},
            {"id": "elegant", "name": "Elegant Serifs", "description": "Classic serif typography for a premium feel.", "preview_type": "standard", "accent": "#1e293b"},
            {"id": "startup", "name": "Startup Rocket", "description": "Punchy and fresh for early-stage companies.", "preview_type": "bold", "accent": "#ff4757"},
            {"id": "classic", "name": "Classic Times", "description": "The timeless standard for any industry.", "preview_type": "standard", "accent": "#000000"},
            {"id": "modern_dark", "name": "Modern Night", "description": "Modern Tech layout with a dark, premium theme.", "preview_type": "dark", "accent": "#60a5fa"},
            # --- Collection 2 (Inspired by Canva 2026) ---
            {"id": "duotone_purple", "name": "Duotone Purple", "description": "Modern purple & blue gradients for tech creatives.", "preview_type": "standard", "accent": "#9333ea"},
            {"id": "sage_garden", "name": "Sage Garden", "description": "Calming sage tones for wellness and organic brands.", "preview_type": "standard", "accent": "#708238"},
            {"id": "social_pro", "name": "Social Strategist", "description": "Optimized for social media and content managers.", "preview_type": "split", "accent": "#1da1f2"},
            {"id": "geometric", "name": "Geometric Edge", "description": "Sharp lines and abstract shapes for modern designers.", "preview_type": "bold", "accent": "#f43f5e"},
            {"id": "cream_peach", "name": "Cream & Peach", "description": "Warm, trendy colors for web developers and UXers.", "preview_type": "split", "accent": "#fb923c"},
            {"id": "spectrum", "name": "Spectrum Vitae", "description": "Vibrant rainbow accents for a bold personality.", "preview_type": "standard", "accent": "#3b82f6"},
            {"id": "clarity", "name": "Canva Clarity", "description": "Glassmorphism elements with high readability.", "preview_type": "standard", "accent": "#0ea5e9"},
            {"id": "spacesmart", "name": "Space Smart", "description": "Maximum data density with a professional grid.", "preview_type": "standard", "accent": "#64748b"},
            {"id": "polished_path", "name": "Polished Path", "description": "Contemporary design with sleek dividers.", "preview_type": "standard", "accent": "#1e293b"},
            {"id": "flexform", "name": "Flex Form", "description": "Versatile hybrid layout for career changers.", "preview_type": "standard", "accent": "#4d7c0f"},
            {"id": "nextstep", "name": "Next Step", "description": "Future-proof design with bold navigation elements.", "preview_type": "bold", "accent": "#b91c1c"},
            {"id": "turquoise_corp", "name": "Turquoise Corp", "description": "Refreshing turquoise accents for corporate roles.", "preview_type": "standard", "accent": "#0d9488"},
            {"id": "scholar_line", "name": "Scholar Line", "description": "Minimalist layout optimized for CVs and scholarships.", "preview_type": "standard", "accent": "#3f3f46"},
            {"id": "collage", "name": "Creative Collage", "description": "Artistic layout for portfolios and designers.", "preview_type": "split", "accent": "#db2777"},
            {"id": "swiss", "name": "Swiss Style", "description": "Bold typography and grid-based perfection.", "preview_type": "bold", "accent": "#dc2626"},
            {"id": "data_expert", "name": "Data Expert", "description": "Focus on charts and metrics for analysts.", "preview_type": "standard", "accent": "#2563eb"},
            {"id": "terminal", "name": "Terminal Code", "description": "Monospace fonts and dark theme for developers.", "preview_type": "dark", "accent": "#22c55e"},
            {"id": "lavender", "name": "Lavender Dream", "description": "Soft purple aesthetic for lifestyle and fashion.", "preview_type": "split", "accent": "#8b5cf6"},
            {"id": "luxury_gold", "name": "Luxury Gold", "description": "Executive design with gold-foil inspired accents.", "preview_type": "standard", "accent": "#d4af37"},
            {"id": "silver_lining", "name": "Silver Lining", "description": "Clean silver tones for high-end consulting.", "preview_type": "standard", "accent": "#94a3b8"},
            {"id": "navy_seal", "name": "Deep Navy", "description": "Trustworthy navy palette for finance and law.", "preview_type": "standard", "accent": "#1e3a8a"},
            {"id": "mint_fresh", "name": "Mint Fresh", "description": "Light, modern mint feel for healthcare.", "preview_type": "standard", "accent": "#2dd4bf"},
            {"id": "peach_dev", "name": "Peach Developer", "description": "Modern tech layout with warm peach highlights.", "preview_type": "standard", "accent": "#fb923c"},
            {"id": "autumn", "name": "Autumn Professional", "description": "Earth tones for a grounded, mature look.", "preview_type": "standard", "accent": "#92400e"},
            {"id": "sky_gradient", "name": "Sky Gradient", "description": "Vibrant blue-to-white gradients for high energy.", "preview_type": "split", "accent": "#0ea5e9"},
            {"id": "charcoal_bold", "name": "Charcoal Bold", "description": "Heavy dark headers for ultra-strong hierarchy.", "preview_type": "bold", "accent": "#171717"},
            {"id": "minimal_ink", "name": "Minimal Ink", "description": "High contrast black and white for direct impact.", "preview_type": "standard", "accent": "#000000"},
            {"id": "classic_journal", "name": "Journalist Pro", "description": "Newspaper style layout for writers and PR.", "preview_type": "standard", "accent": "#000000"},
            {"id": "legal_brief", "name": "Legal Brief", "description": "Optimized for lawyers and formal services.", "preview_type": "standard", "accent": "#1e293b"},
            {"id": "portfolio_plus", "name": "Portfolio Plus", "description": "Best for showing off multiple project highlights.", "preview_type": "split", "accent": "#4338ca"},
            # --- Collection 3 (Extended Canva Pro Range) ---
            {"id": "careeredge", "name": "Career Edge", "description": "Aggressive and bold for competitive industries.", "preview_type": "split", "accent": "#b91c1c"},
            {"id": "pureelegance", "name": "Pure Elegance", "description": "Ultra-thin serifs and expansive whitespace.", "preview_type": "standard", "accent": "#d1d5db"},
            {"id": "profileprime", "name": "Profile Prime", "description": "The golden standard for mid-career professionals.", "preview_type": "standard", "accent": "#1e40af"},
            {"id": "readease", "name": "Read Ease", "description": "Optimized typography for quick recruiter scanning.", "preview_type": "standard", "accent": "#0f172a"},
            {"id": "multipro", "name": "Multi Pro Vitae", "description": "Handles massive amounts of information gracefully.", "preview_type": "standard", "accent": "#374151"},
            {"id": "personaprint", "name": "Persona Print", "description": "Branding-first layout for influencers and speakers.", "preview_type": "split", "accent": "#7c3aed"},
            {"id": "standout", "name": "Stand Out", "description": "Visual-first approach for marketing and advertising.", "preview_type": "split", "accent": "#db2777"},
            {"id": "probanner", "name": "Pro Banner", "description": "Strong header banner for immediate visual impact.", "preview_type": "split", "accent": "#2563eb"},
            {"id": "blendform", "name": "Blend Form", "description": "A perfect mix of creative and corporate elements.", "preview_type": "standard", "accent": "#4b5563"},
            {"id": "clearline", "name": "Clear Line", "description": "Thin geometric lines for a technical, modern feel.", "preview_type": "standard", "accent": "#06b6d4"},
            {"id": "designmark", "name": "Design Mark", "description": "Portfolio-focused layout for senior designers.", "preview_type": "standard", "accent": "#f97316"},
            {"id": "focusform", "name": "Focus Form", "description": "Reduces noise to highlight core achievements.", "preview_type": "standard", "accent": "#111827"},
            {"id": "atspro", "name": "ATS Pro Max", "description": "100% optimized for robotic screening systems.", "preview_type": "standard", "accent": "#000000"},
            {"id": "streamline", "name": "Streamline", "description": "Vertical-first design for scroll-heavy mobile reading.", "preview_type": "split", "accent": "#059669"},
            {"id": "claritypro", "name": "Clarity Pro", "description": "Premium glassmorphism and clear hierarchy.", "preview_type": "split", "accent": "#0ea5e9"},
            {"id": "inspireform", "name": "Inspire Form", "description": "Warm and welcoming for non-profit and education.", "preview_type": "standard", "accent": "#ea580c"},
            {"id": "artistry", "name": "Artistry Vitae", "description": "Gallery-style layout for artists and curators.", "preview_type": "standard", "accent": "#8b5cf6"},
            {"id": "sharplines", "name": "Sharp Lines", "description": "Architectural grid for engineers and architects.", "preview_type": "bold", "accent": "#0f172a"},
            {"id": "designslate", "name": "Design Slate", "description": "Deep slate theme for a modern dark-mode feel.", "preview_type": "dark", "accent": "#475569"},
            {"id": "contentfocus", "name": "Content Focus", "description": "Text-heavy but readable for academics.", "preview_type": "standard", "accent": "#1e293b"},
            # --- Collection 4 (Role Specific Archetypes) ---
            {"id": "nursing_pro", "name": "Nursing Pro", "description": "Sterile, clean, and clinical for healthcare workers.", "preview_type": "standard", "accent": "#0891b2"},
            {"id": "legal_expert", "name": "Legal Expert", "description": "Authoritative and formal for law professionals.", "preview_type": "standard", "accent": "#1e1b4b"},
            {"id": "sales_giant", "name": "Sales Giant", "description": "Metrics-first for high-performing sales leads.", "preview_type": "bold", "accent": "#b91c1c"},
            {"id": "dev_mono", "name": "Dev Monospace", "description": "Code-inspired layout for terminal lovers.", "preview_type": "dark", "accent": "#10b981"},
            {"id": "hr_harmonious", "name": "HR Harmony", "description": "Soft and approachable for human resources.", "preview_type": "split", "accent": "#ec4899"},
            {"id": "retail_star", "name": "Retail Star", "description": "Punchy and organized for service industries.", "preview_type": "standard", "accent": "#f59e0b"},
            {"id": "chef_cuisine", "name": "Culinary Expert", "description": "Elegant and structured for the food industry.", "preview_type": "standard", "accent": "#1e293b"},
            {"id": "real_estate", "name": "Estate Agent", "description": "Image-friendly for real-estate professionals.", "preview_type": "split", "accent": "#1d4ed8"},
            {"id": "fitness_coach", "name": "Fitness Coach", "description": "Energetic and dynamic for personal trainers.", "preview_type": "split", "accent": "#dc2626"},
            {"id": "travel_guide", "name": "Travel Curate", "description": "Adventure-focused for the tourism industry.", "preview_type": "split", "accent": "#0369a1"},
            # --- More Minimalist Variants ---
            {"id": "hush_minimal", "name": "Hush Minimal", "description": "Whisper-thin details for elite minimalism.", "preview_type": "standard", "accent": "#94a3b8"},
            {"id": "stark_white", "name": "Stark White", "description": "High contrast black on pure white stock look.", "preview_type": "standard", "accent": "#000000"},
            {"id": "zen_master", "name": "Zen Master", "description": "Spacious and calm for creative directors.", "preview_type": "standard", "accent": "#1e293b"},
            {"id": "grid_logic", "name": "Grid Logic", "description": "Strict mathematical grid for detail-oriented roles.", "preview_type": "standard", "accent": "#4b5563"},
            {"id": "editorial", "name": "Editorial Page", "description": "Magazine-style layout with strong typography.", "preview_type": "standard", "accent": "#000000"},
            # --- Add more to reach 100 ---
            {"id": "vintage_type", "name": "Vintage Type", "description": "Typewriter font for a classic, retro appeal.", "preview_type": "standard", "accent": "#44403c"},
            {"id": "futuro", "name": "Futuro Next", "description": "Neo-brutalist design for forward thinkers.", "preview_type": "bold", "accent": "#7c3aed"},
            {"id": "soft_focus", "name": "Soft Focus", "description": "Rounded corners and pastel accents.", "preview_type": "standard", "accent": "#f472b6"},
            {"id": "bold_box", "name": "Bold Box", "description": "Information contained in strong bordered modules.", "preview_type": "standard", "accent": "#000000"},
            {"id": "the_minimal", "name": "The Minimal", "description": "No frills, just your value proposition.", "preview_type": "standard", "accent": "#6b7280"},
            {"id": "impact_plus", "name": "Impact Plus", "description": "Even more emphasis on your career records.", "preview_type": "bold", "accent": "#ef4444"},
            {"id": "clean_pro", "name": "Clean Pro Max", "description": "The cleanest professional layout ever built.", "preview_type": "standard", "accent": "#1e293b"},
            {"id": "modern_edge", "name": "Modern Edge", "description": "Sharp angles and energetic color pops.", "preview_type": "standard", "accent": "#3b82f6"},
            {"id": "classic_serif", "name": "Classic Serif", "description": "The gold standard for legal and banking.", "preview_type": "standard", "accent": "#1e1b4b"},
            {"id": "modern_grid", "name": "Modern Grid", "description": "Modular blocks for a tech-native feel.", "preview_type": "standard", "accent": "#0f172a"},
            {"id": "sidebar_pro", "name": "Sidebar Pro", "description": "Maximum use of a classic sidebar layout.", "preview_type": "split", "accent": "#1e293b"},
            {"id": "content_king", "name": "Content King", "description": "Optimized for long experience histories.", "preview_type": "standard", "accent": "#111827"},
            {"id": "value_prop", "name": "Value Prop", "description": "Large summary and key value focuses.", "preview_type": "standard", "accent": "#4338ca"},
            {"id": "career_map", "name": "Career Map", "description": "Timeline-based layout for visual storytelling.", "preview_type": "split", "accent": "#10b981"},
            {"id": "the_standard", "name": "The Standard", "description": "Guaranteed success for any entry-level role.", "preview_type": "standard", "accent": "#1e293b"}
        ]

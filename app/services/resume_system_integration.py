"""
Final System Integration
Wires all Resume Builder services together with proper dependency management
"""

import logging
from typing import Optional

# Import all services
from app.services.resume_generation_service import ResumeGenerationService
from app.services.ats_scoring_service import ATSScoringService
from app.services.rewrite_service import RewriteService
from app.services.skill_gap_service import SkillGapService
from app.services.resume_job_link_service import ResumeJobLinkService
from app.services.resume_analytics_service import ResumeAnalyticsService
from app.services.resume_coach_agent import ResumeCoachAgent
from app.services.recruiter_persona_service import RecruiterPersonaSimulation
from app.services.compliance_service import ComplianceService
from app.services.auto_apply_integration import AutoApplyResumeIntegration

logger = logging.getLogger(__name__)


class ResumeBuilderSystem:
    """
    Integrated Resume Builder System.
    Central orchestrator for all resume-related services.
    """
    
    def __init__(self, user_id: int):
        """
        Initialize the integrated system.
        
        Args:
            user_id: User ID for context
        """
        self.user_id = user_id
        self.logger = logger
        
        # Initialize services (no circular dependencies)
        self._init_services()
    
    def _init_services(self):
        """Initialize all services in correct order"""
        # Level 1: Independent services (no dependencies)
        self.compliance = ComplianceService()
        self.ats_scoring = ATSScoringService()
        
        # Level 2: Services with Level 1 dependencies
        self.rewrite = RewriteService()
        self.skill_gap = SkillGapService()
        
        # Level 3: Services with Level 1-2 dependencies
        self.generation = ResumeGenerationService(user_id=self.user_id)
        self.link_service = ResumeJobLinkService(user_id=self.user_id)
        
        # Level 4: Services with Level 1-3 dependencies
        self.analytics = ResumeAnalyticsService(user_id=self.user_id)
        self.coach = ResumeCoachAgent(user_id=self.user_id)
        self.persona_sim = RecruiterPersonaSimulation()
        
        # Level 5: Integration services
        self.auto_apply = AutoApplyResumeIntegration
        
        self.logger.info(f"Resume Builder System initialized for user {self.user_id}")
    
    # ========================================================================
    # High-Level Workflows
    # ========================================================================
    
    def create_optimized_resume(
        self,
        base_resume: dict,
        job_description: str,
        num_variants: int = 3
    ) -> dict:
        """
        Complete workflow: Generate, optimize, and validate resume.
        
        Args:
            base_resume: Base resume data
            job_description: Target job description
            num_variants: Number of variants to generate
        
        Returns:
            Complete result with all analysis
        """
        try:
            self.logger.info("Starting optimized resume creation workflow")
            
            # Step 1: Compliance check on base resume
            compliance_report = self.compliance.scan_resume(base_resume)
            if not compliance_report['compliant']:
                self.logger.warning(f"Base resume has {compliance_report['summary']['total_issues']} compliance issues")
            
            # Step 2: Generate job-aware variants
            variants = self.generation.generate_job_aware_resume(
                job_description=job_description,
                base_resume=base_resume,
                num_variants=num_variants
            )
            
            # Step 3: Score each variant
            scored_variants = []
            for variant in variants:
                ats_report = self.ats_scoring.calculate_ats_score(
                    resume_data=variant['resume'],
                    job_description=job_description
                )
                
                scored_variants.append({
                    'variant_id': variant['variant_id'],
                    'resume': variant['resume'],
                    'ats_score': ats_report['overall_score'],
                    'ats_grade': ats_report['grade'],
                    'ats_report': ats_report
                })
            
            # Step 4: Sort by ATS score
            scored_variants.sort(key=lambda x: x['ats_score'], reverse=True)
            best_variant = scored_variants[0]
            
            # Step 5: Skill gap analysis
            resume_skills = best_variant['resume'].get('skills', [])
            skill_gap_report = self.skill_gap.analyze_skill_gap(
                resume_skills=resume_skills,
                job_description=job_description
            )
            
            # Step 6: Compliance check on best variant
            final_compliance = self.compliance.scan_resume(best_variant['resume'])
            
            # Step 7: Generate GDPR-safe version
            gdpr_safe = self.compliance.generate_gdpr_safe_resume(best_variant['resume'])
            
            return {
                'success': True,
                'best_variant': best_variant,
                'all_variants': scored_variants,
                'skill_gap_analysis': skill_gap_report,
                'compliance': final_compliance,
                'gdpr_safe_resume': gdpr_safe,
                'recommendations': self._generate_recommendations(
                    best_variant,
                    skill_gap_report,
                    final_compliance
                )
            }
            
        except Exception as e:
            self.logger.error(f"Optimized resume creation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def review_and_improve_resume(
        self,
        resume_id: int,
        job_description: Optional[str] = None,
        coach_mode: str = 'professional'
    ) -> dict:
        """
        Complete review workflow: Coach feedback + Persona simulation.
        
        Args:
            resume_id: Resume ID
            job_description: Optional job description
            coach_mode: Coach mode to use
        
        Returns:
            Complete review with all perspectives
        """
        try:
            self.logger.info(f"Starting resume review workflow for resume {resume_id}")
            
            # Step 1: Coach review
            self.coach.mode = coach_mode
            coach_review = self.coach.review_resume(
                resume_id=resume_id,
                job_description=job_description
            )
            
            # Step 2: Multi-persona evaluation
            persona_evaluation = self.persona_sim.evaluate_with_all_personas(
                resume_id=resume_id,
                user_id=self.user_id,
                job_description=job_description
            )
            
            # Step 3: Get improvement suggestions
            suggestions = self.coach.get_improvement_suggestions(
                resume_id=resume_id
            )
            
            # Step 4: Compliance check
            from app.models.resume import Resume
            resume = Resume.query.get(resume_id)
            compliance = self.compliance.scan_resume(resume.content_json)
            
            return {
                'success': True,
                'coach_review': coach_review,
                'persona_evaluations': persona_evaluation,
                'improvement_suggestions': suggestions,
                'compliance': compliance,
                'overall_recommendation': self._synthesize_recommendations(
                    coach_review,
                    persona_evaluation,
                    suggestions
                )
            }
            
        except Exception as e:
            self.logger.error(f"Resume review failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def prepare_for_application(
        self,
        resume_id: int,
        job_id: int,
        job_description: str
    ) -> dict:
        """
        Complete application preparation workflow.
        
        Args:
            resume_id: Resume ID
            job_id: Job ID
            job_description: Job description
        
        Returns:
            Application-ready package
        """
        try:
            self.logger.info(f"Preparing resume {resume_id} for job {job_id}")
            
            # Step 1: Select/optimize resume
            resume, version = self.link_service.select_resume_for_job(
                job_id=job_id,
                resume_id=resume_id
            )
            
            # Step 2: ATS scoring
            resume_data = version.content_json if version else resume.content_json
            ats_report = self.ats_scoring.calculate_ats_score(
                resume_data=resume_data,
                job_description=job_description
            )
            
            # Step 3: Skill gap analysis
            resume_skills = resume_data.get('skills', [])
            skill_gaps = self.skill_gap.analyze_skill_gap(
                resume_skills=resume_skills,
                job_description=job_description
            )
            
            # Step 4: Compliance check
            compliance = self.compliance.scan_resume(resume_data)
            
            # Step 5: Generate export-safe versions
            pdf_safe = self.compliance.generate_export_safe_resume(
                resume_data=resume_data,
                export_format='pdf'
            )
            
            docx_safe = self.compliance.generate_export_safe_resume(
                resume_data=resume_data,
                export_format='docx'
            )
            
            # Step 6: Validation
            validation = self.auto_apply.validate_resume_for_application(
                user_id=self.user_id,
                resume_id=resume_id,
                job_description=job_description
            )
            
            return {
                'success': True,
                'resume_id': resume.id,
                'version_id': version.id if version else None,
                'ats_score': ats_report['overall_score'],
                'ats_grade': ats_report['grade'],
                'skill_match': skill_gaps['summary']['match_percentage'],
                'missing_skills': skill_gaps['skill_gaps'],
                'compliance': compliance,
                'validation': validation,
                'export_ready': {
                    'pdf': pdf_safe,
                    'docx': docx_safe
                },
                'ready_to_apply': validation['valid'] and compliance['compliant']
            }
            
        except Exception as e:
            self.logger.error(f"Application preparation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_comprehensive_analytics(self, days: int = 30) -> dict:
        """
        Get comprehensive analytics dashboard.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Complete analytics
        """
        try:
            self.logger.info(f"Generating analytics for {days} days")
            
            # Get dashboard metrics
            metrics = self.analytics.get_dashboard_metrics(days=days)
            
            return {
                'success': True,
                'metrics': metrics
            }
            
        except Exception as e:
            self.logger.error(f"Analytics generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _generate_recommendations(
        self,
        best_variant: dict,
        skill_gap_report: dict,
        compliance: dict
    ) -> list:
        """Generate actionable recommendations"""
        recommendations = []
        
        # ATS recommendations
        if best_variant['ats_score'] < 70:
            recommendations.append({
                'priority': 'high',
                'category': 'ats',
                'message': f"ATS score is {best_variant['ats_score']}/100. Optimize for better results.",
                'action': 'Review ATS report and implement suggested improvements'
            })
        
        # Skill gap recommendations
        if skill_gap_report['summary']['mandatory_missing'] > 0:
            recommendations.append({
                'priority': 'critical',
                'category': 'skills',
                'message': f"{skill_gap_report['summary']['mandatory_missing']} mandatory skills missing",
                'action': 'Add missing mandatory skills or acquire them through learning'
            })
        
        # Compliance recommendations
        if not compliance['compliant']:
            recommendations.append({
                'priority': 'high',
                'category': 'compliance',
                'message': f"{compliance['summary']['total_issues']} compliance issues found",
                'action': 'Fix compliance issues before sharing resume'
            })
        
        return recommendations
    
    def _synthesize_recommendations(
        self,
        coach_review: dict,
        persona_evaluation: dict,
        suggestions: dict
    ) -> dict:
        """Synthesize recommendations from multiple sources"""
        # Get average score from personas
        avg_persona_score = persona_evaluation['comparison']['average_score']
        
        # Determine overall recommendation
        if coach_review['ats_score'] >= 80 and avg_persona_score >= 75:
            overall = 'strong'
            message = 'Resume is strong and ready for applications'
        elif coach_review['ats_score'] >= 70 and avg_persona_score >= 65:
            overall = 'good'
            message = 'Resume is good but could be improved'
        else:
            overall = 'needs_work'
            message = 'Resume needs significant improvement'
        
        return {
            'overall': overall,
            'message': message,
            'coach_score': coach_review['ats_score'],
            'persona_avg_score': avg_persona_score,
            'top_actions': coach_review.get('action_items', [])[:3]
        }
    
    def health_check(self) -> dict:
        """
        System health check.
        
        Returns:
            Health status of all services
        """
        health = {
            'system': 'Resume Builder',
            'status': 'healthy',
            'services': {}
        }
        
        # Check each service
        services = [
            'compliance', 'ats_scoring', 'rewrite', 'skill_gap',
            'generation', 'link_service', 'analytics', 'coach',
            'persona_sim'
        ]
        
        for service_name in services:
            try:
                service = getattr(self, service_name)
                health['services'][service_name] = {
                    'status': 'healthy',
                    'initialized': service is not None
                }
            except Exception as e:
                health['services'][service_name] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health['status'] = 'degraded'
        
        return health


# ============================================================================
# Service Registry (for dependency injection)
# ============================================================================

class ServiceRegistry:
    """
    Central service registry for dependency injection.
    Ensures single instance per user session.
    """
    
    _instances = {}
    
    @classmethod
    def get_system(cls, user_id: int) -> ResumeBuilderSystem:
        """
        Get or create Resume Builder System instance.
        
        Args:
            user_id: User ID
        
        Returns:
            ResumeBuilderSystem instance
        """
        if user_id not in cls._instances:
            cls._instances[user_id] = ResumeBuilderSystem(user_id)
        
        return cls._instances[user_id]
    
    @classmethod
    def clear_cache(cls, user_id: Optional[int] = None):
        """Clear cached instances"""
        if user_id:
            cls._instances.pop(user_id, None)
        else:
            cls._instances.clear()


# ============================================================================
# Integration Helpers
# ============================================================================

def initialize_resume_builder(app):
    """
    Initialize Resume Builder system with Flask app.
    
    Args:
        app: Flask application
    """
    logger.info("Initializing Resume Builder System")
    
    # Register blueprints
    from app.routes.resume_api import resume_bp
    from app.routes.resume_coach_api import resume_coach_bp
    
    app.register_blueprint(resume_bp)
    app.register_blueprint(resume_coach_bp)
    
    # Initialize auto-apply integration
    from app.services.auto_apply_integration import integrate_with_autopilot
    integrate_with_autopilot()
    
    logger.info("Resume Builder System initialized successfully")


def get_resume_system(user_id: int) -> ResumeBuilderSystem:
    """
    Convenience function to get Resume Builder System.
    
    Args:
        user_id: User ID
    
    Returns:
        ResumeBuilderSystem instance
    """
    return ServiceRegistry.get_system(user_id)

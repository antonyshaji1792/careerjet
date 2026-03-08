"""
Skill Recommendation Service
Provides actionable, vendor-neutral recommendations for skill gaps
"""

from typing import Dict, List, Optional
import logging

from app.models.skill_intelligence import SkillCategory

logger = logging.getLogger(__name__)


class SkillRecommendationService:
    """
    Generate actionable recommendations for skill gaps.
    Vendor-neutral, generic learning paths.
    """
    
    # ========================================================================
    # Recommendation Database
    # ========================================================================
    
    SKILL_RECOMMENDATIONS = {
        # Programming Languages
        'python': {
            'course_types': [
                'Online interactive coding course (beginner to advanced)',
                'University-level programming fundamentals course',
                'Bootcamp-style intensive program (8-12 weeks)',
                'Self-paced video tutorial series'
            ],
            'certification_types': [
                'Entry-level Python programming certification',
                'Associate-level Python developer certification',
                'Professional Python developer certification'
            ],
            'project_ideas': [
                'Build a REST API for a task management system',
                'Create a data analysis dashboard with visualization',
                'Develop a web scraper for job listings',
                'Build a command-line tool for file processing',
                'Create an automated testing framework'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Developed Python applications for [specific use case] using [frameworks/libraries]',
                'Built and maintained Python-based REST APIs serving [X] requests/day',
                'Automated [process] using Python scripts, reducing manual effort by [X]%',
                'Implemented data processing pipelines in Python handling [X] records',
                'Created Python tools for [specific purpose], improving efficiency by [X]%'
            ],
            'learning_time': '2-3 months',
            'difficulty': 'intermediate'
        },
        
        'javascript': {
            'course_types': [
                'Modern JavaScript fundamentals course (ES6+)',
                'Full-stack JavaScript development program',
                'Interactive coding platform with JavaScript track',
                'Project-based JavaScript course'
            ],
            'certification_types': [
                'JavaScript developer certification',
                'Frontend developer certification',
                'Full-stack JavaScript certification'
            ],
            'project_ideas': [
                'Build a single-page application (SPA) for task tracking',
                'Create an interactive data visualization dashboard',
                'Develop a real-time chat application',
                'Build a browser extension for productivity',
                'Create a progressive web app (PWA)'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Developed interactive web applications using JavaScript and modern frameworks',
                'Built responsive front-end interfaces with JavaScript, improving user engagement by [X]%',
                'Implemented real-time features using JavaScript and WebSocket technology',
                'Created reusable JavaScript components for [specific purpose]',
                'Optimized JavaScript code performance, reducing load time by [X]%'
            ],
            'learning_time': '2-3 months',
            'difficulty': 'intermediate'
        },
        
        # Frameworks
        'react': {
            'course_types': [
                'React fundamentals and hooks course',
                'Modern React development bootcamp',
                'React with TypeScript course',
                'Advanced React patterns and best practices'
            ],
            'certification_types': [
                'React developer certification',
                'Frontend framework certification',
                'Modern web development certification'
            ],
            'project_ideas': [
                'Build a full-featured e-commerce product catalog',
                'Create a social media dashboard with real-time updates',
                'Develop a project management tool with drag-and-drop',
                'Build a weather app with API integration',
                'Create a portfolio website with animations'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Developed responsive web applications using React and modern JavaScript',
                'Built reusable React components library used across [X] projects',
                'Implemented state management solutions in React applications',
                'Created React-based dashboards for data visualization and analytics',
                'Optimized React application performance, improving render time by [X]%'
            ],
            'learning_time': '1-2 months',
            'difficulty': 'intermediate'
        },
        
        'django': {
            'course_types': [
                'Django web development fundamentals',
                'Full-stack development with Django',
                'Django REST framework course',
                'Advanced Django patterns and deployment'
            ],
            'certification_types': [
                'Django developer certification',
                'Python web framework certification',
                'Backend development certification'
            ],
            'project_ideas': [
                'Build a blog platform with user authentication',
                'Create a REST API for a mobile app backend',
                'Develop a content management system (CMS)',
                'Build an e-commerce backend with payment integration',
                'Create a multi-tenant SaaS application'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Developed scalable web applications using Django framework',
                'Built RESTful APIs with Django REST Framework serving [X] users',
                'Implemented authentication and authorization systems in Django',
                'Created Django-based backend systems handling [X] transactions/day',
                'Optimized Django ORM queries, reducing database load by [X]%'
            ],
            'learning_time': '1-2 months',
            'difficulty': 'intermediate'
        },
        
        # Cloud Platforms
        'aws': {
            'course_types': [
                'Cloud computing fundamentals course',
                'AWS solutions architect training',
                'Hands-on AWS labs and workshops',
                'Cloud infrastructure and deployment course'
            ],
            'certification_types': [
                'Cloud Practitioner certification',
                'Solutions Architect Associate certification',
                'Developer Associate certification',
                'SysOps Administrator certification'
            ],
            'project_ideas': [
                'Deploy a web application on EC2 with auto-scaling',
                'Build a serverless API using Lambda and API Gateway',
                'Create a CI/CD pipeline with CodePipeline',
                'Set up a data lake using S3 and analytics services',
                'Implement infrastructure as code with CloudFormation'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Deployed and managed applications on AWS cloud infrastructure',
                'Implemented AWS services including EC2, S3, Lambda, and RDS',
                'Designed scalable cloud architectures handling [X] users/requests',
                'Automated infrastructure deployment using AWS CloudFormation/Terraform',
                'Reduced infrastructure costs by [X]% through AWS optimization'
            ],
            'learning_time': '2-3 months',
            'difficulty': 'intermediate'
        },
        
        'kubernetes': {
            'course_types': [
                'Container orchestration fundamentals',
                'Kubernetes administration course',
                'Cloud-native application development',
                'Kubernetes deployment and operations'
            ],
            'certification_types': [
                'Certified Kubernetes Administrator (CKA)',
                'Certified Kubernetes Application Developer (CKAD)',
                'Kubernetes security certification'
            ],
            'project_ideas': [
                'Deploy a microservices application on Kubernetes',
                'Set up monitoring and logging with Prometheus/Grafana',
                'Implement auto-scaling and load balancing',
                'Create a CI/CD pipeline deploying to Kubernetes',
                'Build a multi-environment Kubernetes cluster'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Deployed and managed containerized applications on Kubernetes',
                'Orchestrated microservices architecture using Kubernetes',
                'Implemented auto-scaling and load balancing in Kubernetes clusters',
                'Managed Kubernetes deployments across [X] environments',
                'Reduced deployment time by [X]% using Kubernetes automation'
            ],
            'learning_time': '1-2 months',
            'difficulty': 'advanced'
        },
        
        'docker': {
            'course_types': [
                'Containerization fundamentals course',
                'Docker for developers training',
                'Container security and best practices',
                'Docker Compose and multi-container apps'
            ],
            'certification_types': [
                'Docker Certified Associate',
                'Container technology certification'
            ],
            'project_ideas': [
                'Containerize a multi-tier web application',
                'Create Docker Compose setup for microservices',
                'Build optimized Docker images for production',
                'Set up development environment with Docker',
                'Implement container security scanning'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Containerized applications using Docker for consistent deployments',
                'Built and optimized Docker images reducing size by [X]%',
                'Implemented Docker-based development environments for [X] projects',
                'Created Docker Compose configurations for multi-container applications',
                'Streamlined deployment process using Docker containers'
            ],
            'learning_time': '2-4 weeks',
            'difficulty': 'beginner-intermediate'
        },
        
        # Databases
        'postgresql': {
            'course_types': [
                'Relational database fundamentals',
                'PostgreSQL administration and optimization',
                'Database design and modeling course',
                'Advanced SQL and query optimization'
            ],
            'certification_types': [
                'PostgreSQL administrator certification',
                'Database professional certification',
                'SQL expert certification'
            ],
            'project_ideas': [
                'Design and implement a normalized database schema',
                'Build a data warehouse with ETL processes',
                'Create stored procedures and triggers',
                'Implement database replication and backup',
                'Optimize queries for high-traffic application'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Designed and optimized PostgreSQL databases handling [X] transactions/day',
                'Implemented database schemas and indexing strategies',
                'Wrote complex SQL queries for data analysis and reporting',
                'Managed PostgreSQL databases with [X]GB of data',
                'Improved query performance by [X]% through optimization'
            ],
            'learning_time': '1-2 months',
            'difficulty': 'intermediate'
        },
        
        'mongodb': {
            'course_types': [
                'NoSQL database fundamentals',
                'MongoDB development course',
                'Document database design patterns',
                'MongoDB administration and scaling'
            ],
            'certification_types': [
                'MongoDB developer certification',
                'MongoDB administrator certification',
                'NoSQL database certification'
            ],
            'project_ideas': [
                'Build a content management system with MongoDB',
                'Create a real-time analytics dashboard',
                'Implement a user profile and session store',
                'Design a product catalog with flexible schema',
                'Build an event logging and monitoring system'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Developed applications using MongoDB for flexible data storage',
                'Designed MongoDB schemas for [specific use case]',
                'Implemented MongoDB aggregation pipelines for analytics',
                'Managed MongoDB databases with [X] million documents',
                'Optimized MongoDB queries improving response time by [X]%'
            ],
            'learning_time': '1-2 months',
            'difficulty': 'intermediate'
        },
        
        # Tools
        'git': {
            'course_types': [
                'Version control fundamentals',
                'Git workflow and best practices',
                'Collaborative development with Git',
                'Advanced Git techniques'
            ],
            'certification_types': [
                'Git fundamentals certification',
                'Version control professional certification'
            ],
            'project_ideas': [
                'Set up branching strategy for team project',
                'Create Git hooks for automated testing',
                'Implement code review workflow',
                'Manage open-source contributions',
                'Set up Git-based deployment pipeline'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Managed source code using Git version control',
                'Implemented Git workflows for team collaboration',
                'Maintained code repositories with branching strategies',
                'Conducted code reviews using Git-based tools',
                'Streamlined development workflow using Git best practices'
            ],
            'learning_time': '2-4 weeks',
            'difficulty': 'beginner'
        },
        
        'terraform': {
            'course_types': [
                'Infrastructure as Code fundamentals',
                'Terraform for cloud infrastructure',
                'DevOps automation course',
                'Multi-cloud deployment with Terraform'
            ],
            'certification_types': [
                'Terraform Associate certification',
                'Infrastructure as Code certification',
                'Cloud automation certification'
            ],
            'project_ideas': [
                'Automate cloud infrastructure provisioning',
                'Create reusable Terraform modules',
                'Implement multi-environment deployments',
                'Build disaster recovery infrastructure',
                'Automate network and security configurations'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Automated infrastructure provisioning using Terraform',
                'Created reusable Terraform modules for [X] environments',
                'Managed cloud resources as code with Terraform',
                'Reduced infrastructure deployment time by [X]% using Terraform',
                'Implemented infrastructure versioning and rollback capabilities'
            ],
            'learning_time': '1-2 months',
            'difficulty': 'intermediate'
        },
        
        # Methodologies
        'agile': {
            'course_types': [
                'Agile methodology fundamentals',
                'Scrum framework training',
                'Agile project management course',
                'Lean and Agile principles'
            ],
            'certification_types': [
                'Certified ScrumMaster (CSM)',
                'Agile Certified Practitioner',
                'Professional Scrum Master'
            ],
            'project_ideas': [
                'Lead sprint planning and retrospectives',
                'Implement Kanban board for team workflow',
                'Facilitate daily standups and ceremonies',
                'Create user stories and acceptance criteria',
                'Track and improve team velocity'
            ],
            'resume_section': 'Professional Experience',
            'bullet_point_templates': [
                'Led Agile development teams using Scrum methodology',
                'Facilitated sprint planning, daily standups, and retrospectives',
                'Improved team velocity by [X]% through Agile practices',
                'Managed product backlog and sprint deliverables',
                'Collaborated with stakeholders using Agile frameworks'
            ],
            'learning_time': '2-4 weeks',
            'difficulty': 'beginner'
        },
        
        'ci/cd': {
            'course_types': [
                'Continuous Integration/Deployment fundamentals',
                'DevOps pipeline automation',
                'Build and release management',
                'Automated testing and deployment'
            ],
            'certification_types': [
                'DevOps engineer certification',
                'CI/CD specialist certification',
                'Automation engineer certification'
            ],
            'project_ideas': [
                'Build automated testing pipeline',
                'Create deployment pipeline for multiple environments',
                'Implement automated code quality checks',
                'Set up continuous monitoring and alerts',
                'Automate database migrations in pipeline'
            ],
            'resume_section': 'Technical Skills',
            'bullet_point_templates': [
                'Implemented CI/CD pipelines for automated testing and deployment',
                'Reduced deployment time from [X] to [Y] using automation',
                'Built automated testing frameworks integrated with CI/CD',
                'Managed release processes across [X] environments',
                'Improved deployment success rate to [X]% through automation'
            ],
            'learning_time': '1-2 months',
            'difficulty': 'intermediate'
        }
    }
    
    # Generic template for skills not in database
    GENERIC_RECOMMENDATION = {
        'course_types': [
            'Online fundamentals course',
            'Hands-on workshop or bootcamp',
            'Self-paced learning platform',
            'University-level course'
        ],
        'certification_types': [
            'Entry-level certification',
            'Professional certification',
            'Advanced specialist certification'
        ],
        'project_ideas': [
            'Build a sample project demonstrating the skill',
            'Contribute to open-source projects',
            'Create a portfolio piece',
            'Solve real-world problems using the skill',
            'Build a tutorial or documentation'
        ],
        'resume_section': 'Technical Skills',
        'bullet_point_templates': [
            'Developed projects using [skill] for [specific purpose]',
            'Implemented [skill] solutions improving [metric] by [X]%',
            'Applied [skill] to solve [specific problem]',
            'Created [deliverable] using [skill] and related technologies',
            'Demonstrated proficiency in [skill] through [achievement]'
        ],
        'learning_time': '1-2 months',
        'difficulty': 'intermediate'
    }
    
    def __init__(self):
        self.logger = logger
    
    # ========================================================================
    # Main Recommendation Methods
    # ========================================================================
    
    def get_recommendations_for_skill(
        self,
        skill_name: str,
        skill_key: str,
        gap_type: str = 'missing',
        current_proficiency: Optional[str] = None,
        job_context: Optional[str] = None
    ) -> Dict:
        """
        Get comprehensive recommendations for a skill gap.
        
        Args:
            skill_name: Display name of skill
            skill_key: Normalized skill key
            gap_type: 'missing' or 'weak_proficiency'
            current_proficiency: Current proficiency level if weak
            job_context: Context from job description
        
        Returns:
            Structured recommendations
        """
        # Get base recommendations
        base_rec = self.SKILL_RECOMMENDATIONS.get(
            skill_key,
            self.GENERIC_RECOMMENDATION
        )
        
        # Customize based on gap type
        if gap_type == 'weak_proficiency':
            recommendations = self._customize_for_weak_proficiency(
                base_rec,
                skill_name,
                current_proficiency
            )
        else:
            recommendations = self._customize_for_missing_skill(
                base_rec,
                skill_name
            )
        
        # Add metadata
        recommendations['skill_name'] = skill_name
        recommendations['skill_key'] = skill_key
        recommendations['gap_type'] = gap_type
        
        return recommendations
    
    def get_bulk_recommendations(
        self,
        skill_gaps: List[Dict]
    ) -> List[Dict]:
        """
        Get recommendations for multiple skill gaps.
        
        Args:
            skill_gaps: List of skill gap dictionaries
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        for gap in skill_gaps:
            rec = self.get_recommendations_for_skill(
                skill_name=gap.get('skill_name'),
                skill_key=gap.get('skill_key'),
                gap_type=gap.get('gap_type', 'missing'),
                current_proficiency=gap.get('current_proficiency')
            )
            recommendations.append(rec)
        
        return recommendations
    
    # ========================================================================
    # Customization Methods
    # ========================================================================
    
    def _customize_for_missing_skill(
        self,
        base_rec: Dict,
        skill_name: str
    ) -> Dict:
        """Customize recommendations for missing skill"""
        return {
            'learning_path': {
                'phase_1': {
                    'title': f'Learn {skill_name} Fundamentals',
                    'duration': '4-6 weeks',
                    'activities': [
                        f'Complete a {skill_name} fundamentals course',
                        'Practice with hands-on exercises',
                        'Build 2-3 small projects',
                        'Read official documentation'
                    ]
                },
                'phase_2': {
                    'title': f'Apply {skill_name} in Projects',
                    'duration': '4-6 weeks',
                    'activities': [
                        f'Build a portfolio project using {skill_name}',
                        'Contribute to open-source projects',
                        'Solve coding challenges',
                        'Create a blog post or tutorial'
                    ]
                },
                'phase_3': {
                    'title': f'Master {skill_name}',
                    'duration': '4-8 weeks',
                    'activities': [
                        'Study advanced concepts and patterns',
                        'Optimize and refactor previous projects',
                        'Consider certification if applicable',
                        'Mentor others or teach the skill'
                    ]
                }
            },
            'course_types': base_rec['course_types'],
            'certification_types': base_rec['certification_types'],
            'project_ideas': base_rec['project_ideas'],
            'resume_placement': {
                'section': base_rec['resume_section'],
                'bullet_points': base_rec['bullet_point_templates'],
                'skill_listing': f'Add "{skill_name}" to your skills section',
                'context_tips': [
                    f'Mention {skill_name} in relevant project descriptions',
                    f'Quantify impact when using {skill_name}',
                    f'Include version/tools related to {skill_name}'
                ]
            },
            'estimated_time': base_rec['learning_time'],
            'difficulty_level': base_rec['difficulty'],
            'success_metrics': [
                f'Complete 2-3 projects using {skill_name}',
                f'Contribute to 1-2 open-source projects',
                f'Pass a {skill_name} assessment or quiz',
                'Add skill to resume with concrete examples'
            ]
        }
    
    def _customize_for_weak_proficiency(
        self,
        base_rec: Dict,
        skill_name: str,
        current_proficiency: Optional[str]
    ) -> Dict:
        """Customize recommendations for weak proficiency"""
        return {
            'improvement_path': {
                'current_level': current_proficiency or 'beginner',
                'target_level': 'intermediate',
                'focus_areas': [
                    f'Deepen understanding of {skill_name} core concepts',
                    'Practice with real-world scenarios',
                    'Study best practices and design patterns',
                    'Build more complex projects'
                ],
                'activities': [
                    f'Take an intermediate {skill_name} course',
                    'Refactor existing code to use advanced features',
                    'Read advanced documentation and articles',
                    'Pair program with experienced developers'
                ]
            },
            'project_ideas': [
                f'Rebuild a previous project with advanced {skill_name} features',
                f'Optimize existing {skill_name} code for performance',
                f'Implement design patterns in {skill_name}',
                f'Create a complex feature using {skill_name}'
            ],
            'resume_updates': {
                'current_bullet': f'Used {skill_name} for basic tasks',
                'improved_bullet': base_rec['bullet_point_templates'][0],
                'tips': [
                    'Add quantifiable achievements',
                    'Mention advanced features used',
                    'Highlight problem-solving with the skill'
                ]
            },
            'estimated_time': '2-4 weeks',
            'difficulty_level': 'intermediate',
            'success_metrics': [
                f'Build 1-2 intermediate-level {skill_name} projects',
                f'Demonstrate advanced {skill_name} features',
                'Update resume with stronger examples',
                'Feel confident discussing the skill in interviews'
            ]
        }
    
    # ========================================================================
    # Resume Section Mapping
    # ========================================================================
    
    def get_resume_section_for_skill(
        self,
        skill_key: str,
        skill_category: str
    ) -> str:
        """Determine appropriate resume section for skill"""
        
        # Check skill-specific recommendation
        if skill_key in self.SKILL_RECOMMENDATIONS:
            return self.SKILL_RECOMMENDATIONS[skill_key]['resume_section']
        
        # Fallback to category-based mapping
        category_mapping = {
            SkillCategory.LANGUAGE: 'Technical Skills',
            SkillCategory.FRAMEWORK: 'Technical Skills',
            SkillCategory.TOOL: 'Technical Skills',
            SkillCategory.PLATFORM: 'Technical Skills',
            SkillCategory.METHODOLOGY: 'Professional Experience',
            SkillCategory.SOFT_SKILL: 'Professional Summary',
            SkillCategory.HARD_SKILL: 'Technical Skills'
        }
        
        return category_mapping.get(skill_category, 'Technical Skills')
    
    def generate_bullet_point(
        self,
        skill_name: str,
        skill_key: str,
        context: Optional[str] = None
    ) -> str:
        """Generate a resume bullet point for a skill"""
        
        # Get templates
        rec = self.SKILL_RECOMMENDATIONS.get(
            skill_key,
            self.GENERIC_RECOMMENDATION
        )
        
        # Use first template and customize
        template = rec['bullet_point_templates'][0]
        
        # Replace placeholders
        bullet = template.replace('[skill]', skill_name)
        bullet = bullet.replace('[X]', '25')  # Example metric
        bullet = bullet.replace('[specific use case]', 'production applications')
        bullet = bullet.replace('[frameworks/libraries]', 'modern frameworks')
        
        return bullet
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_all_supported_skills(self) -> List[str]:
        """Get list of all skills with detailed recommendations"""
        return list(self.SKILL_RECOMMENDATIONS.keys())
    
    def has_detailed_recommendation(self, skill_key: str) -> bool:
        """Check if skill has detailed recommendation"""
        return skill_key in self.SKILL_RECOMMENDATIONS

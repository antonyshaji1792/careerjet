"""
Complete Resume Domain Model Migration
Creates all tables for granular resume management
"""

from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def upgrade(db_engine):
    """Create all resume domain tables"""
    
    with db_engine.connect() as conn:
        
        # 1. Resume Sections Table
        logger.info("Creating resume_sections table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                version_id INTEGER,
                section_type VARCHAR(50) NOT NULL,
                section_order INTEGER DEFAULT 0,
                content TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_ai_generated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES resume_versions(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        
        # 2. Resume Summaries Table
        logger.info("Creating resume_summaries table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                version_id INTEGER,
                summary_text TEXT NOT NULL,
                tone VARCHAR(50),
                word_count INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES resume_versions(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        
        # 3. Resume Experiences Table
        logger.info("Creating resume_experiences table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                version_id INTEGER,
                company_name VARCHAR(200) NOT NULL,
                job_title VARCHAR(200) NOT NULL,
                location VARCHAR(200),
                start_date DATE,
                end_date DATE,
                is_current BOOLEAN DEFAULT 0,
                description TEXT,
                achievements TEXT,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                is_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES resume_versions(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        
        # 4. Resume Education Table
        logger.info("Creating resume_education table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_education (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                version_id INTEGER,
                institution_name VARCHAR(200) NOT NULL,
                degree VARCHAR(200) NOT NULL,
                field_of_study VARCHAR(200),
                start_date DATE,
                end_date DATE,
                is_current BOOLEAN DEFAULT 0,
                gpa REAL,
                honors VARCHAR(200),
                activities TEXT,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES resume_versions(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        
        # 5. Resume Projects Table
        logger.info("Creating resume_projects table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                version_id INTEGER,
                project_name VARCHAR(200) NOT NULL,
                description TEXT,
                technologies TEXT,
                url VARCHAR(500),
                github_url VARCHAR(500),
                start_date DATE,
                end_date DATE,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES resume_versions(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        
        # 6. Resume Certifications Table
        logger.info("Creating resume_certifications table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_certifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                version_id INTEGER,
                certification_name VARCHAR(200) NOT NULL,
                issuing_organization VARCHAR(200),
                issue_date DATE,
                expiration_date DATE,
                credential_id VARCHAR(100),
                credential_url VARCHAR(500),
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES resume_versions(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        
        # 7. Resume Job Links Table
        logger.info("Creating resume_job_links table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_job_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                version_id INTEGER,
                link_type VARCHAR(50) DEFAULT 'applied',
                match_score REAL,
                application_id INTEGER,
                application_status VARCHAR(50),
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_at TIMESTAMP,
                viewed_at TIMESTAMP,
                responded_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                deleted_at TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES job_post(id) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES resume_versions(id) ON DELETE SET NULL,
                FOREIGN KEY (application_id) REFERENCES application(id) ON DELETE SET NULL,
                UNIQUE(resume_id, job_id)
            )
        """))
        conn.commit()
        
        # 8. ATS Scores Table
        logger.info("Creating ats_scores table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ats_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                version_id INTEGER,
                job_id INTEGER,
                overall_score INTEGER NOT NULL,
                formatting_score INTEGER,
                keywords_score INTEGER,
                structure_score INTEGER,
                readability_score INTEGER,
                experience_score INTEGER,
                education_score INTEGER,
                matched_keywords TEXT,
                missing_keywords TEXT,
                keyword_density REAL,
                recommendations TEXT,
                score_version VARCHAR(20) DEFAULT '1.0',
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES resume_versions(id) ON DELETE SET NULL,
                FOREIGN KEY (job_id) REFERENCES job_post(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        
        # 9. Resume Metrics Table
        logger.info("Creating resume_metrics table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                version_id INTEGER,
                job_id INTEGER,
                views INTEGER DEFAULT 0,
                unique_views INTEGER DEFAULT 0,
                downloads INTEGER DEFAULT 0,
                applications_sent INTEGER DEFAULT 0,
                applications_viewed INTEGER DEFAULT 0,
                applications_rejected INTEGER DEFAULT 0,
                phone_screens INTEGER DEFAULT 0,
                interviews_scheduled INTEGER DEFAULT 0,
                interviews_completed INTEGER DEFAULT 0,
                offers_received INTEGER DEFAULT 0,
                view_to_apply_rate REAL DEFAULT 0.0,
                apply_to_interview_rate REAL DEFAULT 0.0,
                interview_to_offer_rate REAL DEFAULT 0.0,
                avg_response_time_hours REAL,
                first_view_at TIMESTAMP,
                last_view_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES resume_versions(id) ON DELETE SET NULL,
                FOREIGN KEY (job_id) REFERENCES job_post(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        
        # 10. Resume Tags Table
        logger.info("Creating resume_tags table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL,
                slug VARCHAR(50) NOT NULL,
                tag_type VARCHAR(20) DEFAULT 'custom',
                color VARCHAR(7) DEFAULT '#3b82f6',
                icon VARCHAR(50),
                user_id INTEGER,
                is_public BOOLEAN DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """))
        conn.commit()
        
        # 11. Resume Tag Associations Table
        logger.info("Creating resume_tag_associations table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_tag_associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by INTEGER,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES resume_tags(id) ON DELETE CASCADE,
                FOREIGN KEY (added_by) REFERENCES user(id) ON DELETE SET NULL,
                UNIQUE(resume_id, tag_id)
            )
        """))
        conn.commit()
        
        # 12. Resume Activity Log Table
        logger.info("Creating resume_activity_log table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                user_id INTEGER,
                action VARCHAR(50) NOT NULL,
                action_details TEXT,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL
            )
        """))
        conn.commit()
        
        # Create Indexes for Performance
        logger.info("Creating indexes...")
        
        indexes = [
            # Resume Sections
            "CREATE INDEX IF NOT EXISTS idx_resume_section_type ON resume_sections(resume_id, section_type)",
            "CREATE INDEX IF NOT EXISTS idx_resume_section_active ON resume_sections(resume_id, is_active)",
            
            # Resume Experiences
            "CREATE INDEX IF NOT EXISTS idx_experience_company ON resume_experiences(resume_id, company_name)",
            "CREATE INDEX IF NOT EXISTS idx_experience_dates ON resume_experiences(start_date, end_date)",
            
            # Resume Job Links
            "CREATE INDEX IF NOT EXISTS idx_resume_job_status ON resume_job_links(resume_id, application_status)",
            "CREATE INDEX IF NOT EXISTS idx_job_resume_score ON resume_job_links(job_id, match_score)",
            "CREATE INDEX IF NOT EXISTS idx_resume_job_linked ON resume_job_links(linked_at)",
            
            # ATS Scores
            "CREATE INDEX IF NOT EXISTS idx_ats_resume_job ON ats_scores(resume_id, job_id)",
            "CREATE INDEX IF NOT EXISTS idx_ats_score_date ON ats_scores(resume_id, calculated_at)",
            "CREATE INDEX IF NOT EXISTS idx_ats_overall_score ON ats_scores(overall_score)",
            
            # Resume Metrics
            "CREATE INDEX IF NOT EXISTS idx_metrics_resume_job ON resume_metrics(resume_id, job_id)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_updated ON resume_metrics(updated_at)",
            
            # Resume Tags
            "CREATE INDEX IF NOT EXISTS idx_tag_name ON resume_tags(name)",
            "CREATE INDEX IF NOT EXISTS idx_tag_slug ON resume_tags(slug)",
            "CREATE INDEX IF NOT EXISTS idx_tag_user_slug ON resume_tags(user_id, slug)",
            
            # Resume Tag Associations
            "CREATE INDEX IF NOT EXISTS idx_tag_assoc_resume ON resume_tag_associations(resume_id)",
            "CREATE INDEX IF NOT EXISTS idx_tag_assoc_tag ON resume_tag_associations(tag_id)",
            
            # Activity Log
            "CREATE INDEX IF NOT EXISTS idx_activity_resume_action ON resume_activity_log(resume_id, action)",
            "CREATE INDEX IF NOT EXISTS idx_activity_user_date ON resume_activity_log(user_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_activity_created ON resume_activity_log(created_at)"
        ]
        
        for index_sql in indexes:
            conn.execute(text(index_sql))
        
        conn.commit()
        
        logger.info("Resume domain model migration completed successfully!")
        return True


def downgrade(db_engine):
    """Drop all resume domain tables"""
    
    with db_engine.connect() as conn:
        logger.info("Rolling back resume domain model...")
        
        tables = [
            'resume_activity_log',
            'resume_tag_associations',
            'resume_tags',
            'resume_metrics',
            'ats_scores',
            'resume_job_links',
            'resume_certifications',
            'resume_projects',
            'resume_education',
            'resume_experiences',
            'resume_summaries',
            'resume_sections'
        ]
        
        for table in tables:
            logger.info(f"Dropping {table}...")
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        
        conn.commit()
        logger.info("Rollback completed!")
        return True


if __name__ == '__main__':
    from app import create_app
    
    app = create_app()
    with app.app_context():
        from app.extensions import db
        
        print("=" * 60)
        print("Resume Domain Model Migration")
        print("=" * 60)
        print()
        print("This will create the following tables:")
        print("  - resume_sections")
        print("  - resume_summaries")
        print("  - resume_experiences")
        print("  - resume_education")
        print("  - resume_projects")
        print("  - resume_certifications")
        print("  - resume_job_links")
        print("  - ats_scores")
        print("  - resume_metrics")
        print("  - resume_tags")
        print("  - resume_tag_associations")
        print("  - resume_activity_log")
        print()
        
        confirm = input("Proceed with migration? (yes/no): ")
        
        if confirm.lower() == 'yes':
            upgrade(db.engine)
            print()
            print("✓ Migration completed successfully!")
        else:
            print("Migration cancelled.")

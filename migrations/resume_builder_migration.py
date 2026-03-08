"""
Database migration script for Resume Builder enhancements
Adds analytics, tracking, and optimization features
"""

from app import db
from app.extensions import db as db_ext
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Apply database migrations for Resume Builder"""
    
    try:
        # Add missing columns to resumes table
        with db.engine.connect() as conn:
            # Check if columns exist before adding
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='resumes' AND column_name='ats_score'
            """))
            
            if not result.fetchone():
                logger.info("Adding ats_score column to resumes table")
                conn.execute(text("""
                    ALTER TABLE resumes 
                    ADD COLUMN ats_score INTEGER DEFAULT NULL
                """))
                conn.commit()
            
            # Add keywords_json column
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='resumes' AND column_name='keywords_json'
            """))
            
            if not result.fetchone():
                logger.info("Adding keywords_json column to resumes table")
                conn.execute(text("""
                    ALTER TABLE resumes 
                    ADD COLUMN keywords_json TEXT DEFAULT NULL
                """))
                conn.commit()
            
            # Add template_id column
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='resumes' AND column_name='template_id'
            """))
            
            if not result.fetchone():
                logger.info("Adding template_id column to resumes table")
                conn.execute(text("""
                    ALTER TABLE resumes 
                    ADD COLUMN template_id VARCHAR(50) DEFAULT 'modern_tech'
                """))
                conn.commit()
        
        # Create resume_analytics table
        logger.info("Creating resume_analytics table")
        db.engine.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                job_id INTEGER,
                views INTEGER DEFAULT 0,
                downloads INTEGER DEFAULT 0,
                applications INTEGER DEFAULT 0,
                responses INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id) REFERENCES job_post(id) ON DELETE SET NULL
            )
        """))
        
        # Create resume_uploads table
        logger.info("Creating resume_uploads table")
        db.engine.execute(text("""
            CREATE TABLE IF NOT EXISTS resume_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_filename VARCHAR(255),
                file_size INTEGER,
                mime_type VARCHAR(100),
                upload_status VARCHAR(50) DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            )
        """))
        
        # Create indexes for performance
        logger.info("Creating indexes")
        db.engine.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_resume_analytics_resume_id 
            ON resume_analytics(resume_id)
        """))
        
        db.engine.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_resume_analytics_job_id 
            ON resume_analytics(job_id)
        """))
        
        db.engine.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_resume_uploads_user_id 
            ON resume_uploads(user_id)
        """))
        
        db.engine.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_resumes_template_id 
            ON resumes(template_id)
        """))
        
        logger.info("Resume Builder database migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise


def downgrade():
    """Rollback database migrations"""
    
    try:
        with db.engine.connect() as conn:
            logger.info("Removing added columns from resumes table")
            
            # Note: SQLite doesn't support DROP COLUMN directly
            # In production with PostgreSQL, use:
            # conn.execute(text("ALTER TABLE resumes DROP COLUMN ats_score"))
            # conn.execute(text("ALTER TABLE resumes DROP COLUMN keywords_json"))
            # conn.execute(text("ALTER TABLE resumes DROP COLUMN template_id"))
            
            logger.info("Dropping resume_analytics table")
            conn.execute(text("DROP TABLE IF EXISTS resume_analytics"))
            conn.commit()
            
            logger.info("Dropping resume_uploads table")
            conn.execute(text("DROP TABLE IF EXISTS resume_uploads"))
            conn.commit()
        
        logger.info("Resume Builder database rollback completed")
        return True
        
    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        raise


if __name__ == '__main__':
    from app import create_app
    
    app = create_app()
    with app.app_context():
        print("Running Resume Builder database migration...")
        upgrade()
        print("Migration completed!")

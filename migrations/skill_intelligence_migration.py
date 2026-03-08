"""
Skill Gap Intelligence Database Migration
Creates tables for comprehensive skill tracking and analysis
"""

from app.extensions import db


def upgrade():
    """Create skill intelligence tables"""
    
    # Table 1: Resume Skills Extracted
    db.session.execute("""
    CREATE TABLE IF NOT EXISTS resume_skills_extracted (
        id SERIAL PRIMARY KEY,
        resume_id INTEGER NOT NULL REFERENCES resume(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        
        -- Skill information
        skill_name VARCHAR(100) NOT NULL,
        skill_name_normalized VARCHAR(100) NOT NULL,
        category VARCHAR(50) NOT NULL,
        
        -- Proficiency and context
        proficiency_level VARCHAR(20) DEFAULT 'unknown',
        years_of_experience FLOAT,
        context TEXT,
        
        -- Scoring
        ats_weight FLOAT DEFAULT 1.0,
        confidence_score FLOAT DEFAULT 1.0,
        
        -- Source tracking
        source VARCHAR(20) NOT NULL DEFAULT 'ai_extracted',
        extraction_method VARCHAR(50),
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Constraints
        CONSTRAINT check_confidence_range CHECK (confidence_score >= 0 AND confidence_score <= 1),
        CONSTRAINT check_ats_weight_positive CHECK (ats_weight >= 0)
    );
    
    -- Indexes for resume_skills_extracted
    CREATE INDEX IF NOT EXISTS idx_resume_skills_skill_name ON resume_skills_extracted(skill_name);
    CREATE INDEX IF NOT EXISTS idx_resume_skills_normalized ON resume_skills_extracted(skill_name_normalized);
    CREATE INDEX IF NOT EXISTS idx_resume_skills_category ON resume_skills_extracted(category);
    CREATE INDEX IF NOT EXISTS idx_resume_skill_lookup ON resume_skills_extracted(resume_id, skill_name_normalized);
    CREATE INDEX IF NOT EXISTS idx_user_skills ON resume_skills_extracted(user_id, skill_name_normalized);
    CREATE INDEX IF NOT EXISTS idx_category_proficiency ON resume_skills_extracted(category, proficiency_level);
    """)
    
    # Table 2: Job Skills Extracted
    db.session.execute("""
    CREATE TABLE IF NOT EXISTS job_skills_extracted (
        id SERIAL PRIMARY KEY,
        job_id INTEGER NOT NULL REFERENCES job_post(id) ON DELETE CASCADE,
        
        -- Skill information
        skill_name VARCHAR(100) NOT NULL,
        skill_name_normalized VARCHAR(100) NOT NULL,
        category VARCHAR(50) NOT NULL,
        
        -- Requirement level
        requirement_type VARCHAR(20) NOT NULL,
        priority_score FLOAT DEFAULT 5.0,
        
        -- Market intelligence
        market_demand_score FLOAT DEFAULT 5.0,
        salary_impact FLOAT,
        
        -- Context
        context TEXT,
        section VARCHAR(50),
        
        -- Scoring
        ats_weight FLOAT DEFAULT 1.0,
        confidence_score FLOAT DEFAULT 1.0,
        
        -- Source tracking
        source VARCHAR(20) NOT NULL DEFAULT 'ai_extracted',
        extraction_method VARCHAR(50),
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Constraints
        CONSTRAINT check_job_confidence_range CHECK (confidence_score >= 0 AND confidence_score <= 1),
        CONSTRAINT check_priority_range CHECK (priority_score >= 1 AND priority_score <= 10),
        CONSTRAINT check_demand_range CHECK (market_demand_score >= 1 AND market_demand_score <= 10)
    );
    
    -- Indexes for job_skills_extracted
    CREATE INDEX IF NOT EXISTS idx_job_skills_skill_name ON job_skills_extracted(skill_name);
    CREATE INDEX IF NOT EXISTS idx_job_skills_normalized ON job_skills_extracted(skill_name_normalized);
    CREATE INDEX IF NOT EXISTS idx_job_skills_category ON job_skills_extracted(category);
    CREATE INDEX IF NOT EXISTS idx_job_skills_requirement ON job_skills_extracted(requirement_type);
    CREATE INDEX IF NOT EXISTS idx_job_skill_lookup ON job_skills_extracted(job_id, skill_name_normalized);
    CREATE INDEX IF NOT EXISTS idx_skill_requirement ON job_skills_extracted(skill_name_normalized, requirement_type);
    CREATE INDEX IF NOT EXISTS idx_market_demand ON job_skills_extracted(market_demand_score, category);
    """)
    
    # Table 3: Skill Gap Analysis
    db.session.execute("""
    CREATE TABLE IF NOT EXISTS skill_gap_analysis (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        resume_id INTEGER NOT NULL REFERENCES resume(id) ON DELETE CASCADE,
        job_id INTEGER REFERENCES job_post(id) ON DELETE SET NULL,
        
        -- Analysis results
        match_percentage FLOAT NOT NULL,
        ats_score FLOAT,
        potential_score FLOAT,
        
        -- Gap counts
        total_jd_skills INTEGER DEFAULT 0,
        total_resume_skills INTEGER DEFAULT 0,
        mandatory_missing INTEGER DEFAULT 0,
        preferred_missing INTEGER DEFAULT 0,
        nice_to_have_missing INTEGER DEFAULT 0,
        matched_skills_count INTEGER DEFAULT 0,
        
        -- Detailed results (JSON)
        skill_gaps JSONB,
        matched_skills JSONB,
        ranked_gaps JSONB,
        learning_paths JSONB,
        score_predictions JSONB,
        category_breakdown JSONB,
        recommendations JSONB,
        market_insights JSONB,
        
        -- Metadata
        analysis_version VARCHAR(20) DEFAULT '2.0',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Constraints
        CONSTRAINT check_match_percentage CHECK (match_percentage >= 0 AND match_percentage <= 100)
    );
    
    -- Indexes for skill_gap_analysis
    CREATE INDEX IF NOT EXISTS idx_gap_analysis_user ON skill_gap_analysis(user_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_gap_analysis_resume_job ON skill_gap_analysis(resume_id, job_id);
    CREATE INDEX IF NOT EXISTS idx_gap_analysis_match ON skill_gap_analysis(match_percentage, ats_score);
    CREATE INDEX IF NOT EXISTS idx_gap_analysis_created ON skill_gap_analysis(created_at);
    """)
    
    # Table 4: Skill Impact Scores
    db.session.execute("""
    CREATE TABLE IF NOT EXISTS skill_impact_scores (
        id SERIAL PRIMARY KEY,
        
        -- Skill information
        skill_name VARCHAR(100) NOT NULL UNIQUE,
        skill_name_normalized VARCHAR(100) NOT NULL UNIQUE,
        category VARCHAR(50) NOT NULL,
        
        -- Impact scores
        ats_weight FLOAT DEFAULT 1.0,
        market_demand_score FLOAT DEFAULT 5.0,
        salary_impact_percentage FLOAT,
        
        -- Market statistics
        job_frequency INTEGER DEFAULT 0,
        mandatory_frequency INTEGER DEFAULT 0,
        preferred_frequency INTEGER DEFAULT 0,
        
        -- Trend data
        trend_score FLOAT DEFAULT 0.0,
        growth_rate FLOAT,
        
        -- Related data (JSON)
        related_skills JSONB,
        alternative_names JSONB,
        
        -- Learning metadata
        avg_learning_time_weeks INTEGER,
        difficulty_level VARCHAR(20) DEFAULT 'intermediate',
        
        -- Metadata
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        data_points INTEGER DEFAULT 0,
        
        -- Constraints
        CONSTRAINT check_impact_demand_range CHECK (market_demand_score >= 1 AND market_demand_score <= 10),
        CONSTRAINT check_impact_ats_weight CHECK (ats_weight >= 0)
    );
    
    -- Indexes for skill_impact_scores
    CREATE INDEX IF NOT EXISTS idx_impact_skill_name ON skill_impact_scores(skill_name);
    CREATE INDEX IF NOT EXISTS idx_impact_normalized ON skill_impact_scores(skill_name_normalized);
    CREATE INDEX IF NOT EXISTS idx_impact_category ON skill_impact_scores(category);
    CREATE INDEX IF NOT EXISTS idx_impact_demand_category ON skill_impact_scores(market_demand_score, category);
    CREATE INDEX IF NOT EXISTS idx_impact_trending ON skill_impact_scores(trend_score, market_demand_score);
    CREATE INDEX IF NOT EXISTS idx_impact_updated ON skill_impact_scores(last_updated);
    """)
    
    db.session.commit()
    print("✅ Skill intelligence tables created successfully!")


def downgrade():
    """Drop skill intelligence tables"""
    db.session.execute("DROP TABLE IF EXISTS resume_skills_extracted CASCADE;")
    db.session.execute("DROP TABLE IF EXISTS job_skills_extracted CASCADE;")
    db.session.execute("DROP TABLE IF EXISTS skill_gap_analysis CASCADE;")
    db.session.execute("DROP TABLE IF EXISTS skill_impact_scores CASCADE;")
    db.session.commit()
    print("✅ Skill intelligence tables dropped successfully!")


if __name__ == '__main__':
    from app import create_app
    
    app = create_app()
    with app.app_context():
        print("Running skill intelligence migration...")
        upgrade()
        print("Migration complete!")

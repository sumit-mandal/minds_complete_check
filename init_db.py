#!/usr/bin/env python3
"""
Initialize PostgreSQL tables for interview sessions
"""
from utils.database import engine
from sqlalchemy import text, inspect

if __name__ == "__main__":
    print("Creating interview tables...")
    
    # Verify users table exists
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            )
        """))
        users_exists = result.scalar()
        
        if not users_exists:
            print("❌ Error: 'users' table not found in database!")
            print("   Please ensure the users table exists before creating interview tables.")
            exit(1)
        
        print("✅ Found 'users' table")
        
        # Check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Create interview_sessions table (without FK constraint initially)
        if "interview_sessions" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE interview_sessions (
                    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP WITH TIME ZONE,
                    max_questions INTEGER,
                    total_questions INTEGER,
                    progress_percentage DOUBLE PRECISION,
                    covered_skills INTEGER,
                    total_skills INTEGER,
                    completion_reason VARCHAR(255),
                    overall_score DOUBLE PRECISION,
                    status VARCHAR(50) NOT NULL DEFAULT 'in_progress'
                )
            """))
            print("✅ Created interview_sessions")
            
            # Add foreign key constraint
            conn.execute(text("""
                ALTER TABLE interview_sessions
                ADD CONSTRAINT fk_interview_sessions_user_id
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            """))
            print("✅ Added foreign key constraint to interview_sessions")
            
            # Create index
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id 
                ON interview_sessions(user_id)
            """))
        else:
            print("⏭️  interview_sessions already exists")
        
        # Create interview_responses table
        if "interview_responses" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE interview_responses (
                    id SERIAL PRIMARY KEY,
                    session_id UUID NOT NULL,
                    question_number INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    user_response TEXT NOT NULL,
                    question_type VARCHAR(100),
                    target_skills VARCHAR[],
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_interview_responses_session_id
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                )
            """))
            print("✅ Created interview_responses")
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_interview_responses_session_id 
                ON interview_responses(session_id)
            """))
        else:
            print("⏭️  interview_responses already exists")
        
        # Create skill_evaluations table
        if "skill_evaluations" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE skill_evaluations (
                    id SERIAL PRIMARY KEY,
                    session_id UUID NOT NULL,
                    response_id INTEGER NOT NULL,
                    skill_name VARCHAR(255) NOT NULL,
                    score DOUBLE PRECISION,
                    confidence_level DOUBLE PRECISION,
                    reasoning TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_skill_evaluations_session_id
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
                    CONSTRAINT fk_skill_evaluations_response_id
                    FOREIGN KEY (response_id) REFERENCES interview_responses(id) ON DELETE CASCADE
                )
            """))
            print("✅ Created skill_evaluations")
        else:
            print("⏭️  skill_evaluations already exists")
        
        # Create final_results table
        if "final_results" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE final_results (
                    session_id UUID PRIMARY KEY,
                    overall_score DOUBLE PRECISION,
                    domain_scores JSONB DEFAULT '{}',
                    skill_scores JSONB DEFAULT '{}',
                    hierarchical_results JSONB DEFAULT '{}',
                    summary JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_final_results_session_id
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                )
            """))
            print("✅ Created final_results")
        else:
            print("⏭️  final_results already exists")
        
        # Create domain_summaries table
        if "domain_summaries" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE domain_summaries (
                    session_id UUID PRIMARY KEY,
                    data JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_domain_summaries_session_id
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                )
            """))
            print("✅ Created domain_summaries")
        else:
            print("⏭️  domain_summaries already exists")
        
        # Create persona_trait_reports table
        if "persona_trait_reports" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE persona_trait_reports (
                    session_id UUID PRIMARY KEY,
                    data JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_persona_trait_reports_session_id
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                )
            """))
            print("✅ Created persona_trait_reports")
        else:
            print("⏭️  persona_trait_reports already exists")
        
        # Remove conn.commit() - begin() auto-commits on success
        print("\n✅ All tables created successfully!")
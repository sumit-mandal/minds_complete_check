#!/usr/bin/env python3
"""
Database module for storing interview responses and results
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class InterviewDatabase:
    """SQLite database for storing interview data"""
    
    def __init__(self, db_path: str = "interview_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    max_questions INTEGER,
                    total_questions INTEGER,
                    progress_percentage REAL,
                    covered_skills INTEGER,
                    total_skills INTEGER,
                    completion_reason TEXT,
                    overall_score REAL,
                    status TEXT
                )
            """)
            
            # Create responses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interview_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    question_number INTEGER,
                    question_text TEXT,
                    user_response TEXT,
                    question_type TEXT,
                    target_skills TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions (session_id)
                )
            """)
            
            # Create evaluations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    response_id INTEGER,
                    skill_name TEXT,
                    score REAL,
                    confidence_level REAL,
                    reasoning TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions (session_id),
                    FOREIGN KEY (response_id) REFERENCES interview_responses (id)
                )
            """)
            
            # Create final results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS final_results (
                    session_id TEXT PRIMARY KEY,
                    overall_score REAL,
                    domain_scores TEXT,
                    skill_scores TEXT,
                    hierarchical_results TEXT,
                    summary TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions (session_id)
                )
            """)
            
            conn.commit()
    
    def save_session_start(self, session_id: str, max_questions: int):
        """Save session start information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO interview_sessions 
                (session_id, start_time, max_questions, status)
                VALUES (?, ?, ?, ?)
            """, (session_id, datetime.now(), max_questions, "in_progress"))
            conn.commit()
    
    def save_response(self, session_id: str, question_number: int, question_text: str, 
                     user_response: str, question_type: str, target_skills: List[str]):
        """Save a user response"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interview_responses 
                (session_id, question_number, question_text, user_response, question_type, target_skills, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, 
                question_number, 
                question_text, 
                user_response, 
                question_type, 
                json.dumps(target_skills),
                datetime.now()
            ))
            response_id = cursor.lastrowid
            
            # Update session progress
            cursor.execute("""
                UPDATE interview_sessions 
                SET total_questions = ?
                WHERE session_id = ?
            """, (question_number, session_id))
            
            conn.commit()
            return response_id
    
    def save_evaluation(self, session_id: str, response_id: int, evaluation: Dict[str, Any]):
        """Save skill evaluation results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            skill_scores = evaluation.get("skill_scores", {})
            confidence_level = evaluation.get("confidence_level", 0.0)
            reasoning = evaluation.get("reasoning", "")
            
            for skill_name, score in skill_scores.items():
                cursor.execute("""
                    INSERT INTO skill_evaluations 
                    (session_id, response_id, skill_name, score, confidence_level, reasoning, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, 
                    response_id, 
                    skill_name, 
                    score, 
                    confidence_level, 
                    reasoning,
                    datetime.now()
                ))
            
            conn.commit()
    
    def save_session_completion(self, session_id: str, final_results: Dict[str, Any], 
                              completion_reason: str):
        """Save session completion information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update session table
            cursor.execute("""
                UPDATE interview_sessions 
                SET end_time = ?, 
                    progress_percentage = ?, 
                    covered_skills = ?, 
                    total_skills = ?, 
                    completion_reason = ?, 
                    overall_score = ?, 
                    status = ?
                WHERE session_id = ?
            """, (
                datetime.now(),
                final_results.get("interview_progress", 0.0),
                final_results.get("covered_skills", 0),
                final_results.get("total_skills", 0),
                completion_reason,
                final_results.get("overall_score", 0.0),
                "completed",
                session_id
            ))
            
            # Save final results
            cursor.execute("""
                INSERT OR REPLACE INTO final_results 
                (session_id, overall_score, domain_scores, skill_scores, hierarchical_results, summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                final_results.get("overall_score", 0.0),
                json.dumps(final_results.get("domain_scores", {})),
                json.dumps(final_results.get("skill_scores", {})),
                json.dumps(final_results.get("hierarchical_results", {})),
                json.dumps(final_results.get("summary", {})),
                datetime.now()
            ))
            
            conn.commit()
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get complete session data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get session info
            cursor.execute("SELECT * FROM interview_sessions WHERE session_id = ?", (session_id,))
            session_row = cursor.fetchone()
            
            if not session_row:
                return None
            
            session_data = dict(session_row)
            
            # Get responses
            cursor.execute("""
                SELECT * FROM interview_responses 
                WHERE session_id = ? 
                ORDER BY question_number
            """, (session_id,))
            responses = [dict(row) for row in cursor.fetchall()]
            
            # Get evaluations for each response
            for response in responses:
                cursor.execute("""
                    SELECT * FROM skill_evaluations 
                    WHERE response_id = ? 
                    ORDER BY skill_name
                """, (response['id'],))
                evaluations = [dict(row) for row in cursor.fetchall()]
                response['evaluations'] = evaluations
            
            # Get final results
            cursor.execute("SELECT * FROM final_results WHERE session_id = ?", (session_id,))
            final_results_row = cursor.fetchone()
            final_results = dict(final_results_row) if final_results_row else {}
            
            return {
                "session": session_data,
                "responses": responses,
                "final_results": final_results
            }
    
    def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get LLM-generated conversation summary for a session"""
        from utils.graph_3_llm_helper import summarizer_llm
        from langchain_core.prompts import ChatPromptTemplate
        import json
        
        # Get session data
        session_data = self.get_session_data(session_id)
        if not session_data:
            return None
        
        # Prepare conversation data for LLM
        conversation_data = {
            "session_info": session_data["session"],
            "responses": []
        }
        
        for response in session_data["responses"]:
            response_data = {
                "question_number": response["question_number"],
                "question": response["question_text"],
                "user_response": response["user_response"],
                "evaluations": {}
            }
            
            # Group evaluations by skill
            for eval_data in response["evaluations"]:
                skill_name = eval_data["skill_name"]
                response_data["evaluations"][skill_name] = {
                    "score": eval_data["score"],
                    "confidence": eval_data["confidence_level"],
                    "reasoning": eval_data["reasoning"]
                }
            
            conversation_data["responses"].append(response_data)
        
        # Generate summary using LLM
        try:
            from utils.graph_3_llm_helper import evaluation_llm
            
            summary_prompt = f"""You are an expert interview analyst. Analyze the complete conversation and provide a comprehensive summary.

Conversation Data: {json.dumps(conversation_data, indent=2)}

Please provide a detailed analysis in the following JSON format:

{{
    "overall_score": 7.5,
    "key_strengths": ["Clear communication", "Problem-solving ability"],
    "areas_for_improvement": ["Could provide more specific examples"],
    "communication_style": "Professional and articulate",
    "problem_solving_approach": "Systematic and collaborative",
    "emotional_intelligence": "Good self-awareness and regulation",
    "professional_maturity": "Demonstrates leadership qualities",
    "specific_examples": ["Handled team conflict effectively", "Showed adaptability"],
    "recommendations": ["Continue developing specific examples", "Practice stress management"],
    "overall_impression": "Strong candidate with room for growth"
}}

Be thorough, constructive, and professional in your analysis. Return only the JSON object."""
            
            response = evaluation_llm.invoke(summary_prompt)
            response_text = response.content.strip()
            
            # Try to extract JSON from the response
            if response_text.startswith('{') and response_text.endswith('}'):
                summary_data = json.loads(response_text)
            else:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    summary_data = json.loads(json_match.group())
                else:
                    raise ValueError("No valid JSON found in response")
            
            return {
                "session_id": session_id,
                "conversation_summary": summary_data,
                "conversation_data": conversation_data
            }
            
        except Exception as e:
            print(f"Error generating conversation summary: {e}")
            return {
                "session_id": session_id,
                "conversation_summary": {
                    "overall_score": 0.0,
                    "analysis": "Error generating summary",
                    "strengths": [],
                    "improvements": [],
                    "recommendations": []
                },
                "conversation_data": conversation_data
            }
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get all interview sessions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM interview_sessions 
                ORDER BY start_time DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total sessions
            cursor.execute("SELECT COUNT(*) FROM interview_sessions")
            total_sessions = cursor.fetchone()[0]
            
            # Completed sessions
            cursor.execute("SELECT COUNT(*) FROM interview_sessions WHERE status = 'completed'")
            completed_sessions = cursor.fetchone()[0]
            
            # Average score
            cursor.execute("SELECT AVG(overall_score) FROM final_results")
            avg_score = cursor.fetchone()[0] or 0.0
            
            # Average questions per session
            cursor.execute("SELECT AVG(total_questions) FROM interview_sessions WHERE status = 'completed'")
            avg_questions = cursor.fetchone()[0] or 0.0
            
            return {
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "average_score": round(avg_score, 2),
                "average_questions": round(avg_questions, 1),
                "completion_rate": round((completed_sessions / total_sessions * 100) if total_sessions > 0 else 0, 1)
            }

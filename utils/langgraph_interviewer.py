#!/usr/bin/env python3
"""
LangGraph-based Automated Interviewer
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict
from enum import Enum

from utils.state_manager import StateManager, Persona, CandidatePersona
from utils.graph_3_llm_helper import (
    question_generator_llm, 
    evaluation_llm,
    summarizer_llm
)
# INTERVIEW_DOMAINS is now passed dynamically from the request body
from utils.database import InterviewDatabase
from utils.langgraph_flow import build_interview_graph, InterviewState

class LangGraphInterviewer:
    """LangGraph-based automated interviewer"""
    
    def __init__(self, max_questions: int = None):
        self.max_questions = max_questions
        self.database = InterviewDatabase()
        self.graph = build_interview_graph()
        self.session_states = {}  # In-memory session state storage
    
    def start_interview(self, session_id: str = None, persona: Persona = Persona.MENTOR, candidate_persona: CandidatePersona = CandidatePersona.PROFESSIONAL, interview_domains: Dict[str, Any] = None, max_questions: int = None, target_skills: List[str] = None) -> Dict[str, Any]:
        """Start a new interview session"""
        
        if session_id is None:
            session_id = f"interview_{int(time.time())}"
        
        # max_questions must be provided from request body
        if max_questions is None:
            raise ValueError("max_questions must be provided in the request body")
        
        # Initialize state for LangGraph
        initial_state = InterviewState(
            session_id=session_id,
            current_question="",
            target_skills=target_skills or [],  # Use provided target skills or empty list
            question_type="",
            user_response=None,
            evaluation=None,
            progress={},
            question_count=0,
            max_questions=max_questions,  # Use dynamic max_questions
            interview_complete=False,
            summary=None,
            final_results=None,
            completion_reason=None,
            last_response=None,
            interview_started=False,
            state_manager_data=None,
            persona=persona,
            candidate_persona=candidate_persona,
            interview_domains=interview_domains  # Pass interview domains
        )
        
        # Run the graph
        result = self.graph.invoke(initial_state)
        
        # Store the state for this session
        self.session_states[session_id] = result
        
        return {
            "session_id": result["session_id"],
            "current_question": result["current_question"],
            "target_skills": result["target_skills"],
            "question_type": result["question_type"],
            "progress": result["progress"],
            "max_questions": result["max_questions"]
        }
    
    def submit_response(self, user_response: str, session_id: str) -> Dict[str, Any]:
        """Submit a user response and get the next question or results"""
        
        if not user_response.strip():
            raise ValueError("User response cannot be empty")
        
        # Get current state for this session
        current_state = self.session_states.get(session_id)
        if not current_state:
            raise ValueError(f"No active session found for {session_id}")
        
        # Update state with user response
        state = InterviewState(
            session_id=session_id,
            current_question=current_state["current_question"],
            target_skills=current_state["target_skills"],
            question_type=current_state["question_type"],
            user_response=user_response,
            evaluation=current_state.get("evaluation"),
            progress=current_state.get("progress", {}),
            question_count=current_state.get("question_count", 0),
            max_questions=current_state.get("max_questions"),  # Use state max_questions from request
            interview_complete=current_state.get("interview_complete", False),
            summary=current_state.get("summary"),
            final_results=current_state.get("final_results"),
            completion_reason=current_state.get("completion_reason"),
            last_response=current_state.get("last_response"),
            interview_started=current_state.get("interview_started", True),
            state_manager_data=current_state.get("state_manager_data"),
            persona=current_state.get("persona", Persona.MENTOR),
            candidate_persona=current_state.get("candidate_persona", CandidatePersona.PROFESSIONAL),
            interview_domains=current_state.get("interview_domains")  # Include interview domains
        )
        
        # Run the graph
        result = self.graph.invoke(state)
        
        # Update session state
        self.session_states[session_id] = result
        
        if result["interview_complete"]:
            return {
                "interview_complete": True,
                "summary": result["summary"],
                "final_results": result["final_results"],
                "completion_reason": result["completion_reason"]
            }
        else:
            return {
                "interview_complete": False,
                "current_question": result["current_question"],
                "target_skills": result["target_skills"],
                "question_type": result["question_type"],
                "progress": result["progress"],
                "last_evaluation": result.get("evaluation"),
                "question_number": result["question_count"],
                "max_questions": result["max_questions"]
            }
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current interview progress"""
        # This would need to be implemented with proper state persistence
        return {"progress_percentage": 0, "covered_skills": 0, "total_skills": 0}
    
    def get_results(self) -> Dict[str, Any]:
        """Get current interview results"""
        # This would need to be implemented with proper state persistence
        return {"overall_score": 0, "skill_scores": {}}
    
    def reset_interview(self):
        """Reset the interview state"""
        self.session_states.clear()

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
from utils.graph_3_llm_helper import llm, evaluation_llm
from utils.database import InterviewDatabase
from utils.langgraph_flow import build_interview_graph, InterviewState, ensure_persona_enum, ensure_candidate_persona_enum

class LangGraphInterviewer:
    """LangGraph-based automated interviewer with checkpointing"""
    
    def __init__(self, max_questions: int = None):
        self.max_questions = max_questions
        self.database = InterviewDatabase()
        self.graph = build_interview_graph()
    
    def start_interview(self, session_id: str = None, user_id: str = None, persona: Persona = Persona.MENTOR, candidate_persona: CandidatePersona = CandidatePersona.PROFESSIONAL, interview_domains: Dict[str, Any] = None, max_questions: int = None, target_skills: List[str] = None, name: str = None, pronoun: Optional[str] = None, career_level: Optional[str] = None, industry: Optional[str] = None) -> Dict[str, Any]:
        """Start a new interview session"""
        
        if session_id is None:
            raise ValueError("session_id must be provided")
        
        if max_questions is None:
            raise ValueError("max_questions must be provided in the request body")
        
        initial_state = InterviewState(
            session_id=session_id,
            user_id=user_id,
            name=name,
            current_question="",
            target_skills=target_skills or [],
            question_type="",
            user_response=None,
            evaluation=None,
            progress={},
            question_count=0,
            max_questions=max_questions,
            interview_complete=False,
            summary=None,
            final_results=None,
            completion_reason=None,
            last_response=None,
            interview_started=False,
            state_manager_data=None,
            persona=persona,
            candidate_persona=candidate_persona,
            interview_domains=interview_domains,
            pronoun=pronoun,
            career_level=career_level,
            industry=industry
        )
        
        config = {"configurable": {"thread_id": session_id}}
        result = self.graph.invoke(initial_state, config)
        
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
        
        config = {"configurable": {"thread_id": session_id}}
        
        current_state = self.graph.get_state(config)
        if not current_state.values:
            raise ValueError(f"No active session found for {session_id}")
        
        state = InterviewState(
            session_id=session_id,
            user_id=current_state.values.get("user_id"),
            name=current_state.values.get("name"),
            current_question=current_state.values["current_question"],
            target_skills=current_state.values["target_skills"],
            question_type=current_state.values["question_type"],
            user_response=user_response,
            evaluation=current_state.values.get("evaluation"),
            progress=current_state.values.get("progress", {}),
            question_count=current_state.values.get("question_count", 0),
            max_questions=current_state.values.get("max_questions"),
            interview_complete=current_state.values.get("interview_complete", False),
            summary=current_state.values.get("summary"),
            final_results=current_state.values.get("final_results"),
            completion_reason=current_state.values.get("completion_reason"),
            last_response=current_state.values.get("last_response"),
            interview_started=current_state.values.get("interview_started", True),
            state_manager_data=current_state.values.get("state_manager_data"),
            persona=ensure_persona_enum(current_state.values.get("persona", Persona.MENTOR)),
            candidate_persona=ensure_candidate_persona_enum(current_state.values.get("candidate_persona", CandidatePersona.PROFESSIONAL)),
            interview_domains=current_state.values.get("interview_domains"),
            pronoun=current_state.values.get("pronoun"),
            career_level=current_state.values.get("career_level"),
            industry=current_state.values.get("industry")
        )
        
        result = self.graph.invoke(state, config)
        
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
    
    def get_progress(self, session_id: str) -> Dict[str, Any]:
        """Get current interview progress"""
        config = {"configurable": {"thread_id": session_id}}
        state = self.graph.get_state(config)
        
        if not state.values:
            raise ValueError(f"No session found for {session_id}")
        
        return state.values.get("progress", {})
    
    def get_results(self, session_id: str) -> Dict[str, Any]:
        """Get current interview results"""
        config = {"configurable": {"thread_id": session_id}}
        state = self.graph.get_state(config)
        
        if not state.values:
            raise ValueError(f"No session found for {session_id}")
        
        return {
            "final_results": state.values.get("final_results"),
            "summary": state.values.get("summary"),
            "evaluation": state.values.get("evaluation")
        }

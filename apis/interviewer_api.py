from fastapi import APIRouter, HTTPException, Depends, Form
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

from utils.langgraph_interviewer import LangGraphInterviewer
from utils.database import InterviewDatabase
from utils.state_manager import Persona, CandidatePersona
from utils.trait_analyzer import generate_persona_report

router = APIRouter(prefix="/interviewer", tags=["Automated Interviewer"])

# Global instances
interviewer = LangGraphInterviewer()  # max_questions will come from request body
database = InterviewDatabase()  # Database instance

# Request/Response models
class StartInterviewRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: str 
    name: str 
    persona: Optional[Persona] = Persona.MENTOR
    candidate_persona: Optional[CandidatePersona] = CandidatePersona.PROFESSIONAL
    interview_domains: Dict[str, Any]
    max_questions: int

class StartInterviewResponse(BaseModel):
    session_id: str
    current_question: str
    target_skills: list
    question_type: str
    progress: Dict[str, Any]
    max_questions: int

class SubmitResponseRequest(BaseModel):
    user_response: str
    session_id: str

class SubmitResponseResponse(BaseModel):
    interview_complete: bool
    current_question: Optional[str] = None
    target_skills: Optional[list] = None
    question_type: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    last_evaluation: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    final_results: Optional[Dict[str, Any]] = None
    question_number: Optional[int] = None
    max_questions: Optional[int] = None
    completion_reason: Optional[str] = None

class ProgressResponse(BaseModel):
    progress: Dict[str, Any]

class ResultsResponse(BaseModel):
    results: Dict[str, Any]

class SessionDataResponse(BaseModel):
    session: Dict[str, Any]
    responses: List[Dict[str, Any]]
    final_results: Dict[str, Any]
    conversation_summary: Optional[Dict[str, Any]] = None

class SessionsListResponse(BaseModel):
    sessions: List[Dict[str, Any]]

class StatisticsResponse(BaseModel):
    statistics: Dict[str, Any]

@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(request: StartInterviewRequest):
    """Start a new interview session"""
    if request.session_id:
        session_id = request.session_id
    else:
        session_id = database.create_session(request.user_id, request.max_questions)
    
    persona = request.persona or Persona.MENTOR
    candidate_persona = request.candidate_persona or CandidatePersona.PROFESSIONAL
    interview_domains = request.interview_domains
    max_questions = request.max_questions
    
    
    result = interviewer.start_interview(session_id, request.user_id, persona, candidate_persona, interview_domains, max_questions,name = request.name)
    
    return StartInterviewResponse(
        session_id=result["session_id"],
        current_question=result["current_question"],
        target_skills=result["target_skills"],
        question_type=result["question_type"],
        progress=result["progress"],
        max_questions=result["max_questions"],
    )

@router.post("/submit", response_model=SubmitResponseResponse)
async def submit_response(request: SubmitResponseRequest):
    """Submit a user response and get the next question or results"""
    # try:
    if not request.user_response.strip():
        raise HTTPException(status_code=400, detail="User response cannot be empty")
    
    result = interviewer.submit_response(request.user_response, request.session_id)
    
    if result["interview_complete"]:
        return SubmitResponseResponse(
            interview_complete=True,
            summary=result["summary"],
            final_results=result["final_results"],
            completion_reason=result.get("completion_reason")
        )
    else:
        return SubmitResponseResponse(
            interview_complete=False,
            current_question=result["current_question"],
            target_skills=result["target_skills"],
            question_type=result["question_type"],
            progress=result["progress"],
            last_evaluation=result["last_evaluation"],
            question_number=result.get("question_number"),
            max_questions=result.get("max_questions")
        )


@router.get("/progress/{session_id}", response_model=ProgressResponse)
async def get_progress(session_id: str):
    """Get current interview progress"""
    try:
        progress = interviewer.get_progress()
        return ProgressResponse(progress=progress)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")

@router.get("/results/{session_id}", response_model=ResultsResponse)
async def get_results(session_id: str):
    """Get current interview results"""
    try:
        results = interviewer.get_results()
        return ResultsResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")

@router.post("/reset")
async def reset_interview():
    """Reset the interview state"""
    try:
        interviewer.reset_interview()
        return {"message": "Interview reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset interview: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Database endpoints
@router.get("/sessions", response_model=SessionsListResponse)
async def get_all_sessions():
    """Get all interview sessions"""
    try:
        sessions = database.get_all_sessions()
        return SessionsListResponse(sessions=sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")

@router.get("/sessions/{session_id}", response_model=SessionDataResponse)
async def get_session_data(session_id: str):
    """Get complete data for a specific session"""
    try:
        session_data = database.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get conversation summary
        conversation_summary = database.get_conversation_summary(session_id)
        
        # Add conversation summary to response
        session_data["conversation_summary"] = conversation_summary.get("conversation_summary") if conversation_summary else None
        
        return SessionDataResponse(**session_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session data: {str(e)}")

@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """Get overall interview statistics"""
    try:
        statistics = database.get_session_statistics()
        return StatisticsResponse(statistics=statistics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.get("/persona-trait/{session_id}")
async def get_persona_trait_report(session_id: str):
    """Get persona trait report for a specific session"""
    session_data = database.get_session_data(session_id) 
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    final_results = session_data.get("final_results", {})
    hierarchical_results_raw = final_results.get("hierarchical_results")
    
    # Check if hierarchical_results is None, empty dict, or missing
    if not hierarchical_results_raw or (isinstance(hierarchical_results_raw, dict) and len(hierarchical_results_raw) == 0):
        # Try to use domain_scores as fallback
        domain_scores = final_results.get("domain_scores", {})
        if not domain_scores:
            raise HTTPException(status_code=404, detail="No hierarchical results or domain scores found")
        else:
            print(f"DEBUG API: hierarchical_results is empty, using domain_scores as fallback: {domain_scores}")
            hierarchical_results_raw = {}  # Set to empty dict, will use fallback

    print(f"DEBUG API: hierarchical_results_raw type: {type(hierarchical_results_raw)}")
    print(f"DEBUG API: hierarchical_results_raw keys: {list(hierarchical_results_raw.keys()) if isinstance(hierarchical_results_raw, dict) else 'Not a dict'}")
    if isinstance(hierarchical_results_raw, dict):
        for key, value in hierarchical_results_raw.items():
            print(f"DEBUG API: Domain '{key}': type={type(value)}, has average_score={isinstance(value, dict) and 'average_score' in value}")

    conversation_summary_data = database.get_conversation_summary(session_id) 
    conversation_summary = conversation_summary_data.get("conversation_summary") if conversation_summary_data else None
    
    # Get fallback domain_scores in case hierarchical_results is empty or malformed
    fallback_domain_scores = final_results.get("domain_scores", {})
    print(f"DEBUG API: fallback_domain_scores: {fallback_domain_scores}")
    
    report = generate_persona_report(hierarchical_results_raw, conversation_summary, fallback_domain_scores=fallback_domain_scores)
    print("Persona Trait Report:",report)
    return report


class UserInterviewsResponse(BaseModel):
    user_id: str
    total_sessions: int
    interviews: List[Dict[str, Any]]
    
@router.get("/user/{user_id}/interviews", response_model=UserInterviewsResponse)
async def get_all_interviews_by_user_id(user_id: str): 
    interviews = database.get_all_interviews_by_user_id(user_id)
    
    if user_id:
        return UserInterviewsResponse(user_id=user_id,
                total_sessions=len(interviews),
                interviews=interviews)
    else:
        return "User not found"
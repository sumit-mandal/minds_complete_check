from fastapi import APIRouter, HTTPException, Depends, Form
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from utils.simple_interviewer import SimpleAutomatedInterviewer

router = APIRouter(prefix="/interviewer", tags=["Automated Interviewer"])

# Global interviewer instance
interviewer = SimpleAutomatedInterviewer(max_questions=3)  # Set max questions to 3

# Request/Response models
class StartInterviewRequest(BaseModel):
    session_id: Optional[str] = None

class StartInterviewResponse(BaseModel):
    session_id: str
    current_question: str
    target_skills: list
    question_type: str
    progress: Dict[str, Any]

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

@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(request: StartInterviewRequest):
    """Start a new interview session"""
    try:
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"
        result = interviewer.start_interview(session_id)
        
        return StartInterviewResponse(
            session_id=result["session_id"],
            current_question=result["current_question"],
            target_skills=result["target_skills"],
            question_type=result["question_type"],
            progress=result["progress"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {str(e)}")

@router.post("/submit", response_model=SubmitResponseResponse)
async def submit_response(request: SubmitResponseRequest):
    """Submit a user response and get the next question or results"""
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process response: {str(e)}")

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

from fastapi import APIRouter, HTTPException,WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime

from utils.langgraph_interviewer import LangGraphInterviewer
from utils.database import InterviewDatabase
from utils.state_manager import Persona, CandidatePersona
from utils.trait_analyzer import generate_persona_report
from utils.state_for_websocket import reconstruct_interview_state
from utils.graph_3_llm_helper import generate_domain_summary


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
    pronoun: Optional[str] = None
    career_level: Optional[str] = None
    industry: Optional[str] = None

class StartInterviewResponse(BaseModel):
    session_id: str
    current_question: str
    target_skills: list
    question_type: str
    progress: Dict[str, Any]
    max_questions: int
    persona: Optional[Persona] = None
    industry: Optional[str] = None
    name: Optional[str] = None
    pronoun: Optional[str] = None
    start_time: Optional[str] = None
    duration_seconds: Optional[int] = None

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
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[int] = None

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
    
    
    result = interviewer.start_interview(session_id, request.user_id, persona, candidate_persona, interview_domains, max_questions, name=request.name, pronoun=request.pronoun, career_level=request.career_level, industry=request.industry)
    
    # Get session time info
    time_info = database.get_session_time_info(session_id)
    
    return StartInterviewResponse(
        session_id=result["session_id"],
        current_question=result["current_question"],
        target_skills=result["target_skills"],
        question_type=result["question_type"],
        progress=result["progress"],
        max_questions=result["max_questions"],
        persona=request.persona,
        industry=request.industry,
        name=request.name,
        pronoun=request.pronoun,
        start_time=time_info.get("start_time") if time_info else None,
        duration_seconds=time_info.get("duration_seconds") if time_info else None,
    )

@router.post("/submit", response_model=SubmitResponseResponse)
async def submit_response(request: SubmitResponseRequest):
    """Submit a user response and get the next question or results"""
    # try:
    if not request.user_response.strip():
        raise HTTPException(status_code=400, detail="User response cannot be empty")
    
    result = interviewer.submit_response(request.user_response, request.session_id)
    
    # Get session time info
    time_info = database.get_session_time_info(request.session_id)
    
    if result["interview_complete"]:
        return SubmitResponseResponse(
            interview_complete=True,
            summary=result["summary"],
            final_results=result["final_results"],
            completion_reason=result.get("completion_reason"),
            start_time=time_info.get("start_time") if time_info else None,
            end_time=time_info.get("end_time") if time_info else None,
            duration_seconds=time_info.get("duration_seconds") if time_info else None,
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
            max_questions=result.get("max_questions"),
            start_time=time_info.get("start_time") if time_info else None,
            end_time=time_info.get("end_time") if time_info else None,
            duration_seconds=time_info.get("duration_seconds") if time_info else None,
        )


@router.get("/progress/{session_id}", response_model=ProgressResponse)
async def get_progress(session_id: str):
    """Get current interview progress"""
    try:
        progress = interviewer.get_progress(session_id)
        return ProgressResponse(progress=progress)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")

@router.get("/results/{session_id}", response_model=ResultsResponse)
async def get_results(session_id: str):
    """Get current interview results"""
    try:
        results = interviewer.get_results(session_id)
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

class DomainSummaryResponse(BaseModel):
    session_id: str
    domain_summary: Dict[str, Any]
    cached: bool = False
    
@router.get("/user/{user_id}/interviews", response_model=UserInterviewsResponse)
async def get_all_interviews_by_user_id(user_id: str): 
    interviews = database.get_all_interviews_by_user_id(user_id)
    
    if user_id:
        return UserInterviewsResponse(user_id=user_id,
                total_sessions=len(interviews),
                interviews=interviews)
    else:
        return "User not found"

@router.get("/domains-summary/{session_id}", response_model=DomainSummaryResponse)
async def get_domains_summary(session_id: str):
    """Get a comprehensive summary of all domains covered in the interview"""
    try:
        # Check if session exists
        session_data = database.get_session_data(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if domain summary already exists in database
        cached_summary = database.get_domain_summary(session_id)
        if cached_summary:
            return DomainSummaryResponse(
                session_id=session_id,
                domain_summary=cached_summary,
                cached=True
            )
        
        # Get final results
        final_results = session_data.get("final_results", {})
        hierarchical_results = final_results.get("hierarchical_results", {})
        domain_scores = final_results.get("domain_scores", {})
        
        if not hierarchical_results and not domain_scores:
            raise HTTPException(
                status_code=404, 
                detail="No domain data found for this session. The interview may not be completed yet."
            )
        
        # Get conversation summary if available
        conversation_summary_data = database.get_conversation_summary(session_id)
        conversation_summary = conversation_summary_data.get("conversation_summary") if conversation_summary_data else None
        
        # Get candidate info from LangGraph state if available
        name = None
        pronoun = None
        career_level = None
        industry = None
        persona = None
        
        try:
            interviewer = LangGraphInterviewer()
            config = {"configurable": {"thread_id": session_id}}
            current_state = interviewer.graph.get_state(config)
            if current_state.values:
                name = current_state.values.get("name")
                pronoun = current_state.values.get("pronoun")
                career_level = current_state.values.get("career_level")
                industry = current_state.values.get("industry")
                persona_value = current_state.values.get("persona")
                if persona_value:
                    if isinstance(persona_value, str):
                        try:
                            persona = Persona(persona_value).value
                        except ValueError:
                            persona = str(persona_value)
                    else:
                        persona = persona_value.value if hasattr(persona_value, 'value') else str(persona_value)
        except Exception as e:
            print(f"Could not retrieve candidate info from LangGraph state: {e}")
        
        # Generate domain summary
        domain_summary = generate_domain_summary(
            hierarchical_results=hierarchical_results,
            domain_scores=domain_scores,
            conversation_summary=conversation_summary,
            name=name,
            pronoun=pronoun,
            career_level=career_level,
            industry=industry,
            persona=persona
        )
        
        # Save to database
        database.save_domain_summary(session_id, domain_summary)
        
        return DomainSummaryResponse(
            session_id=session_id,
            domain_summary=domain_summary,
            cached=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate domain summary: {str(e)}")



@router.websocket("/submit/stream")
async def submit_response_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming interview responses"""
    await websocket.accept()

    try: 
        data = await websocket.receive_json()
        user_response = data.get("user_response")
        session_id = data.get("session_id")

        if not user_response or not session_id:
            await websocket.send_json({
                "type": "error",
                "message": "user_response and session_id are required"
            })
            await websocket.close() 
            return 

        if not user_response.strip(): 
            await websocket.send_json({
                "type":"error",
                "message": "User response cannot be empty"
            
            }) 
            await websocket.close() 
            return 

        # Get the graph and config
        config = {"configurable": {"thread_id": session_id}}

        # Check if session exists 

        current_state = interviewer.graph.get_state(config) 
        if not current_state.values: 
            await websocket.send_json({
                "type":"error",
                "message": f"No active session found for {session_id}"
            })
            await websocket.close()
            return

        state = reconstruct_interview_state(user_response, session_id, current_state.values)

        # Track streaming state 
        current_stream_type = None # 'evaluation', 'question', 'summary', 'final_results',etc
        accumulated_content = {}
        final_result = None 

        async for event in interviewer.graph.astream_events(state,config,version="v2"):
            event_type = event.get("type")
            event_name = event.get("name","")

            # stream LLM tokens in real-time
            if event_type == "on_chat_model_stream":
                # Extract the chunk content
                chunk = event.get("data",{}).get("chunk","")
                if hasattr(chunk,"content") and chunk.content:
                    content = chunk.content

    except Exception as e:
        pass
        
from typing import Dict, Any
from utils.langgraph_flow import InterviewState, ensure_persona_enum, ensure_candidate_persona_enum
from utils.state_manager import Persona, CandidatePersona


def reconstruct_interview_state(
    user_response: str,
    session_id: str,
    current_state_values: Dict[str, Any]
) -> InterviewState:
    """
    Reconstruct InterviewState from current state values and user response.
    This is used for WebSocket streaming and maintains the same logic as submit_response.
    
    Args:
        user_response: The user's response to the current question
        session_id: The session ID
        current_state_values: The current state values from the graph
        
    Returns:
        InterviewState: Reconstructed state ready for graph execution
    """
    return InterviewState(
        session_id=session_id,
        user_id=current_state_values.get("user_id"),
        name=current_state_values.get("name"),
        current_question=current_state_values["current_question"],
        target_skills=current_state_values["target_skills"],
        question_type=current_state_values["question_type"],
        user_response=user_response,
        evaluation=current_state_values.get("evaluation"),
        progress=current_state_values.get("progress", {}),
        question_count=current_state_values.get("question_count", 0),
        max_questions=current_state_values.get("max_questions"),
        interview_complete=current_state_values.get("interview_complete", False),
        summary=current_state_values.get("summary"),
        final_results=current_state_values.get("final_results"),
        completion_reason=current_state_values.get("completion_reason"),
        last_response=current_state_values.get("last_response"),
        interview_started=current_state_values.get("interview_started", True),
        state_manager_data=current_state_values.get("state_manager_data"),
        persona=ensure_persona_enum(current_state_values.get("persona", Persona.MENTOR)),
        candidate_persona=ensure_candidate_persona_enum(current_state_values.get("candidate_persona", CandidatePersona.PROFESSIONAL)),
        interview_domains=current_state_values.get("interview_domains"),
        pronoun=current_state_values.get("pronoun"),
        career_level=current_state_values.get("career_level"),
        industry=current_state_values.get("industry")
    )
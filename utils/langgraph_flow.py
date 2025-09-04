#!/usr/bin/env python3
"""
LangGraph Flow for Automated Interviewer
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate

from utils.state_manager import StateManager
from utils.graph_3_llm_helper import (
    question_generator_llm, 
    evaluation_llm,
    summarizer_llm
)
from utils.graph_1_interview_domains import INTERVIEW_DOMAINS
from utils.database import InterviewDatabase

class InterviewState(TypedDict):
    """State for the LangGraph interview flow"""
    session_id: str
    current_question: str
    target_skills: List[str]
    question_type: str
    user_response: Optional[str]
    evaluation: Optional[Dict[str, Any]]
    progress: Dict[str, Any]
    question_count: int
    max_questions: int
    interview_complete: bool
    summary: Optional[Dict[str, Any]]
    final_results: Optional[Dict[str, Any]]
    completion_reason: Optional[str]
    last_response: Optional[str]
    interview_started: bool
    state_manager_data: Optional[Dict[str, Any]]

def start_interview(state: InterviewState) -> InterviewState:
    """Start a new interview session or continue existing one"""
    session_id = state["session_id"]
    max_questions = state["max_questions"]
    
    if state.get("interview_started", False):
        # Interview already started, just pass through to evaluation
        return state
    
    # Create new state manager for new interview
    state_manager = StateManager(INTERVIEW_DOMAINS)
    
    # Save session start to database
    database = InterviewDatabase()
    database.save_session_start(session_id, max_questions)
    
    return {
        **state,
        "current_question": "Please tell us about yourself. What are your main interests and hobbies? Can you also share a bit about your childhood and how it has shaped who you are today? This will help us understand your background and tailor the interview to your specific situation.",
        "target_skills": [],
        "question_type": "introduction",
        "progress": state_manager.get_interview_progress(),
        "question_count": 0,
        "interview_started": False,
        "interview_complete": False,
        "state_manager_data": serialize_state_manager(state_manager)
    }

def evaluate_response(state: InterviewState) -> InterviewState:
    """Evaluate the user response"""
    user_response = state["user_response"]
    session_id = state["session_id"]
    question_count = state["question_count"]
    
    # Reconstruct state manager
    state_manager = deserialize_state_manager(state["state_manager_data"])
    
    # Mark interview as started after first response
    if not state.get("interview_started", False):
        state["interview_started"] = True
    
    # Evaluate the response
    evaluation = evaluate_response_comprehensive(user_response, state_manager)
    
    # Update state manager
    update_state_manager(state_manager, user_response, evaluation)
    
    # Save to database
    database = InterviewDatabase()
    response_id = database.save_response(
        session_id=session_id,
        question_number=question_count,
        question_text=state["current_question"],
        user_response=user_response,
        question_type=state["question_type"],
        target_skills=state["target_skills"]
    )
    
    database.save_evaluation(
        session_id=session_id,
        response_id=response_id,
        evaluation=evaluation
    )
    
    # Increment question count after evaluation
    question_count += 1
    
    # Check if interview is complete after incrementing question count
    progress = state_manager.get_interview_progress()
    if (progress["progress_percentage"] >= 99 or 
        progress["covered_skills"] >= progress["total_skills"] or
        question_count >= state["max_questions"]):
        
        # Generate summary
        summary = generate_summary(state_manager)
        final_results = state_manager.export_results()
        completion_reason = get_completion_reason(progress, question_count, state["max_questions"])
        
        # Save session completion
        database = InterviewDatabase()
        database.save_session_completion(
            session_id=session_id,
            final_results=final_results,
            completion_reason=completion_reason
        )
        
        return {
            **state,
            "evaluation": evaluation,
            "last_response": user_response,
            "question_count": question_count,
            "interview_complete": True,
            "summary": summary,
            "final_results": final_results,
            "completion_reason": completion_reason,
            "progress": progress,
            "state_manager_data": serialize_state_manager(state_manager)
        }
    
    return {
        **state,
        "evaluation": evaluation,
        "last_response": user_response,
        "question_count": question_count,
        "state_manager_data": serialize_state_manager(state_manager)
    }

def generate_question(state: InterviewState) -> InterviewState:
    """Generate the next question"""
    # Reconstruct state manager
    state_manager = deserialize_state_manager(state["state_manager_data"])
    
    # If this was the introduction, mark interview as started
    if not state["interview_started"]:
        state["interview_started"] = True
    
    # Use the question count from the state (already incremented in evaluate_response)
    question_count = state["question_count"]
    
    # Get uncovered skills and progress
    uncovered_skills = state_manager.get_uncovered_skills()
    progress = state_manager.get_interview_progress()
    
    # Check if interview is complete
    # Debug output removed
    if (progress["progress_percentage"] >= 99 or 
        progress["covered_skills"] >= progress["total_skills"] or
        question_count >= state["max_questions"]):
        
        # Generate summary
        summary = generate_summary(state_manager)
        final_results = state_manager.export_results()
        completion_reason = get_completion_reason(progress, question_count, state["max_questions"])
        
        # Save session completion
        database = InterviewDatabase()
        database.save_session_completion(
            session_id=state["session_id"],
            final_results=final_results,
            completion_reason=completion_reason
        )
        
        return {
            **state,
            "question_count": question_count,
            "interview_complete": True,
            "summary": summary,
            "final_results": final_results,
            "completion_reason": completion_reason,
            "progress": progress,
            "state_manager_data": serialize_state_manager(state_manager)
        }
    
    # Generate next question
    if not uncovered_skills:
        return {
            **state,
            "question_count": question_count,
            "current_question": "Interview complete! Thank you for your responses.",
            "target_skills": [],
            "question_type": "completion",
            "interview_complete": True,
            "progress": progress,
            "state_manager_data": serialize_state_manager(state_manager)
        }
    
    # Get next question
    next_question_result = get_next_question_contextual(state_manager, state["last_response"], state["evaluation"])
    
    return {
        **state,
        "question_count": question_count,
        "current_question": next_question_result["question"],
        "target_skills": next_question_result["target_skills"],
        "question_type": next_question_result["question_type"],
        "progress": progress,
        "state_manager_data": serialize_state_manager(state_manager)
    }

def should_evaluate_response(state: InterviewState) -> str:
    """Determine if we should evaluate a response"""
    if state.get("user_response"):
        return "evaluate"
    return "end"

def should_start_interview(state: InterviewState) -> str:
    """Determine if we should start interview or go directly to evaluation"""
    if state.get("user_response"):
        # Have a response, go to evaluation
        return "evaluate"
    else:
        # No response yet, start the interview
        return "start"

def should_generate_question(state: InterviewState) -> str:
    """Determine if we should generate a question"""
    if state.get("interview_complete", False):
        return "end"
    return "generate"

# Removed should_continue_interview as it's no longer needed

def serialize_state_manager(state_manager: StateManager) -> Dict[str, Any]:
    """Serialize state manager for storage"""
    return {
        "domains": [domain.model_dump() for domain in state_manager.state.domains],
        "current_domain": state_manager.state.current_domain,
        "current_subdomain": state_manager.state.current_subdomain,
        "current_question": state_manager.state.current_question,
        "interview_progress": state_manager.state.interview_progress,
        "total_skills": state_manager.state.total_skills,
        "covered_skills": state_manager.state.covered_skills,
        "session_id": state_manager.state.session_id,
        "user_responses": state_manager.state.user_responses,
        "interview_complete": state_manager.state.interview_complete
    }

def deserialize_state_manager(data: Dict[str, Any]) -> StateManager:
    """Deserialize state manager data"""
    from utils.state_manager import InterviewState as StateManagerInterviewState
    
    # Reconstruct domains
    domains = []
    for domain_data in data.get("domains", []):
        from utils.state_manager import Domain, Subdomain, CoreSkill, SkillLevel
        
        subdomains = []
        for subdomain_data in domain_data.get("subdomains", []):
            core_skills = []
            for skill_data in subdomain_data.get("core_skills", []):
                skill = CoreSkill(
                    name=skill_data["name"],
                    score=skill_data.get("score", 0.0),
                    covered=skill_data.get("covered", False),
                    asked_in_question=skill_data.get("asked_in_question", False),
                    knowledge_areas=skill_data.get("knowledge_areas", []),
                    practical_applications=skill_data.get("practical_applications", []),
                    level=SkillLevel(skill_data.get("level", "Medium")),
                    assessment_history=skill_data.get("assessment_history", [])
                )
                core_skills.append(skill)
            
            subdomain = Subdomain(
                name=subdomain_data["name"],
                core_skills=core_skills,
                covered=subdomain_data.get("covered", False)
            )
            subdomains.append(subdomain)
        
        domain = Domain(
            name=domain_data["name"],
            subdomains=subdomains,
            covered=domain_data.get("covered", False)
        )
        domains.append(domain)
    
    # Create state manager with the reconstructed state
    state_manager = StateManager(INTERVIEW_DOMAINS)
    state_manager.state = StateManagerInterviewState(
        domains=domains,
        current_domain=data.get("current_domain"),
        current_subdomain=data.get("current_subdomain"),
        current_question=data.get("current_question"),
        interview_progress=data.get("interview_progress", 0.0),
        total_skills=data.get("total_skills", 0),
        covered_skills=data.get("covered_skills", 0),
        session_id=data.get("session_id"),
        user_responses=data.get("user_responses", []),
        interview_complete=data.get("interview_complete", False)
    )
    

    
    return state_manager

def evaluate_response_comprehensive(user_response: str, state_manager: StateManager) -> Dict[str, Any]:
    """Evaluate a user response for ALL skills it might cover"""
    
    # Get ALL skills from the domains
    all_skills = []
    for domain in state_manager.state.domains:
        for subdomain in domain.subdomains:
            for skill in subdomain.core_skills:
                all_skills.append({
                    "name": skill.name,
                    "knowledge_areas": skill.knowledge_areas,
                    "practical_applications": skill.practical_applications,
                    "level": skill.level
                })
    
    try:
        # Use the custom evaluation function
        from utils.graph_3_llm_helper import evaluate_response_with_llm
        evaluation = evaluate_response_with_llm(user_response, all_skills)
        return evaluation
    except Exception as e:
        # Fallback evaluation if LLM fails
        print(f"Warning: LLM evaluation failed: {e}")
        fallback_skills = ["Clarity of Thought", "Problem-Solving Confidence"]
        return {
            "skill_scores": {skill: 5.0 for skill in fallback_skills},
            "confidence_level": 0.5,
            "reasoning": "Fallback evaluation due to LLM error",
            "follow_up_needed": False,
            "skills_covered": fallback_skills
        }

def update_state_manager(state_manager: StateManager, user_response: str, evaluation: Dict[str, Any]):
    """Update the state manager with the response and evaluation"""
    # Add response to state
    response_data = {
        "response": user_response,
        "evaluation": evaluation,
        "timestamp": datetime.now().isoformat()
    }
    state_manager.add_user_response(response_data)
    
    # Update skill scores
    skill_scores = evaluation.get("skill_scores", {})
    if isinstance(skill_scores, str):
        try:
            skill_scores = json.loads(skill_scores)
        except (json.JSONDecodeError, TypeError):
            skill_scores = {}
    
    if isinstance(skill_scores, dict):
        state_manager.update_skill_scores(skill_scores, response_data)

def get_next_question_contextual(state_manager: StateManager, user_response: str, evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """Get the next question based on previous response and remaining skills"""
    
    # Get uncovered skills
    uncovered_skills = state_manager.get_uncovered_skills()
    
    if not uncovered_skills:
        # All skills covered
        return {
            "question": "Interview complete! Thank you for your responses.",
            "target_skills": [],
            "question_type": "completion"
        }
    
    # Select skills to target based on context
    target_skills = select_target_skills_contextual(state_manager, uncovered_skills, evaluation)
    
    # NEW: Mark these skills as asked about in questions
    for skill_info in target_skills:
        state_manager.mark_skill_asked_in_question(skill_info["skill"])
    
    # Generate contextual question
    skill_details = []
    for skill_info in target_skills:
        skill_details.append({
            "name": skill_info["skill"],
            "knowledge_areas": skill_info["knowledge_areas"],
            "practical_applications": skill_info["practical_applications"],
            "level": skill_info["level"]
        })
    
    try:
        question_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert interviewer. Generate a contextual question that builds upon the user's previous response and assesses the target skills.

Previous user response: {previous_response}
Skills to assess: {skill_details}
Last evaluation: {last_evaluation}

Guidelines for question generation:
1. Build upon what the user shared in their previous response
2. Create a natural follow-up question that flows from their experience
3. Target the specific skills that still need assessment
4. Make the question engaging and relevant to their background
5. Ask for specific examples or experiences related to the target skills
6. Make it open-ended enough to allow detailed responses
7. Connect to their previous response when possible
8. IMPORTANT: Ensure the question directly addresses the target skills to avoid topic skipping

Generate a question that naturally follows from their previous response and assesses the target skills."""),
            ("human", "Please generate a contextual interview question.")
        ])
        
        question_data = question_generator_llm.invoke(
            question_prompt.format_messages(
                previous_response=user_response or "No previous response",
                skill_details=json.dumps(skill_details, indent=2),
                last_evaluation=json.dumps(evaluation, indent=2) if evaluation else "No previous evaluation"
            )
        )
        
        # Check if question_data is valid
        if question_data and hasattr(question_data, 'question_text') and question_data.question_text:
            return {
                "question": question_data.question_text,
                "target_skills": question_data.target_skills,
                "question_type": question_data.question_type
            }
        else:
            raise ValueError("Invalid question data returned from LLM")
    except Exception as e:
        # Fallback question if LLM fails
        print(f"Warning: LLM question generation failed: {e}")
        return {
            "question": f"Based on what you shared, could you tell me more about a time when you demonstrated {skill_details[0]['name']} and {skill_details[1]['name'] if len(skill_details) > 1 else 'your skills'}? What was the context, what actions did you take, and what was the outcome?",
            "target_skills": [skill["name"] for skill in skill_details],
            "question_type": "behavioral"
        }

def select_target_skills_contextual(state_manager: StateManager, uncovered_skills: List[Dict], evaluation: Dict) -> List[Dict]:
    """Select target skills based on context and previous response, ensuring no topics are skipped"""
    
    # If this is the first question after introduction, prioritize skills that weren't covered
    if not evaluation or not evaluation.get("skill_scores"):
        # Take first 2-3 uncovered skills
        return uncovered_skills[:3]
    
    # NEW LOGIC: Use the enhanced StateManager methods to ensure no topics are skipped
    # Get skills that need direct questions (highest priority)
    skills_needing_questions = state_manager.get_skills_needing_direct_questions()
    
    # Get skills that were scored in the last response
    last_skills_covered = evaluation.get("skill_scores", {}).keys()
    
    # Find skills that are related to the previously covered skills
    related_skills = []
    unrelated_skills = []
    
    for skill_info in skills_needing_questions:
        skill_name = skill_info["skill"]
        
        # Check if this skill is related to previously covered skills
        # (same domain or subdomain)
        is_related = False
        for covered_skill in last_skills_covered:
            # Check if they're in the same domain/subdomain
            for domain in state_manager.state.domains:
                for subdomain in domain.subdomains:
                    skill_names = [s.name for s in subdomain.core_skills]
                    if skill_name in skill_names and covered_skill in skill_names:
                        is_related = True
                        break
                if is_related:
                    break
            if is_related:
                break
        
        if is_related:
            related_skills.append(skill_info)
        else:
            unrelated_skills.append(skill_info)
    
    # Build target skills list prioritizing never-asked and low-scored skills
    target_skills = []
    
    # First, add high-priority skills that need direct questions
    if skills_needing_questions:
        # Take top 2-3 skills that need questions
        target_skills.extend(skills_needing_questions[:3])
    
    # If we still need more skills, add from uncovered skills
    if len(target_skills) < 2:
        remaining_uncovered = [s for s in uncovered_skills if s not in target_skills]
        
        # Sort by score (lower scores first) to prioritize skills that need more assessment
        remaining_uncovered.sort(key=lambda x: x.get("score", 0.0))
        
        # Add 1-2 related skills if available
        related_remaining = [s for s in remaining_uncovered if s in related_skills]
        if related_remaining:
            target_skills.extend(related_remaining[:1])
        
        # Add unrelated skills for diversity
        unrelated_remaining = [s for s in remaining_uncovered if s in unrelated_skills]
        if unrelated_remaining and len(target_skills) < 3:
            target_skills.extend(unrelated_remaining[:3-len(target_skills)])
        
        # If we still don't have enough, add more from uncovered
        if len(target_skills) < 2:
            final_remaining = [s for s in remaining_uncovered if s not in target_skills]
            target_skills.extend(final_remaining[:2-len(target_skills)])
    
    return target_skills[:3]  # Limit to 3 skills max

def get_skills_never_asked_in_questions(state_manager: StateManager) -> List[Dict[str, Any]]:
    """Get skills that have never been asked about in questions (only covered in answers)"""
    # Use the new StateManager method
    return state_manager.get_skills_never_asked_in_questions()

def get_completion_reason(progress: Dict[str, Any], question_count: int, max_questions: int) -> str:
    """Determine why the interview completed"""
    if progress["progress_percentage"] >= 95:
        return "Progress threshold reached (95%+)"
    elif progress["covered_skills"] >= progress["total_skills"]:
        return "All skills covered"
    elif question_count >= max_questions:
        return f"Maximum questions reached ({max_questions})"
    else:
        return "Unknown completion reason"

def generate_summary(state_manager: StateManager) -> Dict[str, Any]:
    """Generate interview summary"""
    
    results = state_manager.export_results()
    user_responses = state_manager.state.user_responses
    
    try:
        # Use a simpler approach without structured output to avoid validation issues
        summary_prompt = f"""You are an expert interview analyst. Generate a comprehensive summary of the interview results.

Interview Results: {json.dumps(results, indent=2)}
User Responses: {json.dumps(user_responses, indent=2)}

Create a detailed summary including:
1. Overall assessment score and interpretation
2. Domain-specific scores and analysis
3. Key strengths identified
4. Areas for improvement
5. Specific recommendations for growth
6. Overall impressions and insights

Be thorough, professional, and constructive in your analysis.

Return your response as a JSON object with the following structure:
{{
    "overall_score": <numeric_score>,
    "strengths": ["strength1", "strength2", ...],
    "areas_for_improvement": ["area1", "area2", ...],
    "recommendations": ["recommendation1", "recommendation2", ...],
    "analysis": "detailed analysis text"
}}"""

        # Use the regular LLM instead of structured output
        from utils.graph_3_llm_helper import llm
        response = llm.invoke(summary_prompt)
        response_text = response.content.strip()
        
        # Try to extract JSON from the response
        if response_text.startswith('{') and response_text.endswith('}'):
            summary = json.loads(response_text)
        else:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                summary = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")
        
        return summary
    except Exception as e:
        # Fallback summary if LLM fails
        print(f"Warning: LLM summary generation failed: {e}")
        return {
            "overall_score": results.get("overall_score", 0),
            "strengths": ["Good communication skills", "Problem-solving ability"],
            "areas_for_improvement": ["Could provide more specific examples"],
            "recommendations": ["Continue developing skills through practice"],
            "analysis": "Fallback analysis due to LLM error"
        }

def build_interview_graph():
    """Build the LangGraph interview flow"""
    
    # Create the graph
    workflow = StateGraph(InterviewState)
    
    # Add nodes
    workflow.add_node("start_interview", start_interview)
    workflow.add_node("evaluate_response", evaluate_response)
    workflow.add_node("generate_question", generate_question)
    
    # Define the flow
    workflow.set_entry_point("start_interview")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "start_interview",
        should_start_interview,
        {
            "start": END,  # Show introduction question and end
            "evaluate": "evaluate_response"
        }
    )
    
    workflow.add_conditional_edges(
        "evaluate_response",
        should_generate_question,
        {
            "generate": "generate_question",
            "end": END
        }
    )
    
    # Remove the loop - generate_question should always end
    workflow.add_edge("generate_question", END)
    
    return workflow.compile()

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
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

from utils.state_manager import StateManager, Persona, CandidatePersona
from utils.persona_helper import PersonaHelper
from utils.graph_3_llm_helper import llm, evaluation_llm
from utils.database import DATABASE_URL, InterviewDatabase

def filter_domains_by_target_skills(target_skills: List[str], domains: Dict[str, Any]) -> Dict[str, Any]:
    """Filter domains to only include the specified target skills"""
    if not target_skills:
        return domains
    
    filtered_domains = []
    
    for domain in domains["domains"]:
        filtered_subdomains = []
        
        for subdomain in domain["subdomains"]:
            filtered_core_skills = []
            
            for skill in subdomain["core_skills"]:
                if skill["name"] in target_skills:
                    filtered_core_skills.append(skill)
            
            # Only include subdomain if it has skills we want to assess
            if filtered_core_skills:
                filtered_subdomain = subdomain.copy()
                filtered_subdomain["core_skills"] = filtered_core_skills
                filtered_subdomains.append(filtered_subdomain)
        
        # Only include domain if it has subdomains with skills we want to assess
        if filtered_subdomains:
            filtered_domain = domain.copy()
            filtered_domain["subdomains"] = filtered_subdomains
            filtered_domains.append(filtered_domain)
    
    return {"domains": filtered_domains}

class InterviewState(TypedDict):
    """State for the LangGraph interview flow"""
    session_id: str
    user_id: Optional[str]  # Add this line
    name: Optional[str]
    current_question: str
    target_skills: List[str]  # Skills to assess (can be custom or all)
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
    persona: Persona
    candidate_persona: CandidatePersona
    interview_domains: Optional[Dict[str, Any]]
    pronoun: Optional[str]
    career_level: Optional[str]
    industry: Optional[str]

def generate_introduction_question(persona: Persona, candidate_persona: CandidatePersona, name: str, pronoun: Optional[str] = None, career_level: Optional[str] = None, industry: Optional[str] = None) -> str:
    """Generate completely dynamic AI-based introduction question with persona and candidate context"""
    
    try:
        # Get base persona prompt (shared with question generation)
        base_prompt = PersonaHelper.get_base_persona_prompt(persona, candidate_persona, pronoun, career_level, industry)
        
        # Create a completely AI-driven introduction prompt
        introduction_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{base_prompt}

Create a warm, engaging introduction question that:
1. Starts with a natural, friendly greeting using the person's name: {name}
2. Uses their name to make them feel comfortable and welcomed
3. Asks about something personal to help them feel at ease and boost their confidence
4. Can ask about their goals, aspirations, interests, hobbies, or anything they're passionate about
5. IMPORTANT: Introduction Question should be 100% unique and never asked before in any other interview or conversation.
6. IMPORTANT: candidate_persona should be taken into account when generating the introduction question. For example, if the candidate is a student, the introduction question should be more academic and focused on their studies and goals. If the candidate is a professional, the introduction question should be more professional and focused on their career and goals.
7. Never ask any question that says outside of your work to a professional candidate . Since they are professionals they should be asked only about their work and career.
8. Is contextually appropriate for their background (student vs professional)
9. Feels authentic and conversational
10. Is under 300 characters total
11. Varies every time - be creative and unique
12. Makes them feel comfortable and excited to share
13. IMPORTANT: Incorporates their career level and industry context naturally if provided

Generate a unique, authentic introduction question that naturally flows and feels personal.
Return ONLY the question text, nothing else."""),
            ("human", "Please create a warm introduction question for starting our conversation.")
        ])
        
        # Use regular LLM for introduction (no structured output needed - we only need text)
        from utils.graph_3_llm_helper import llm
        question_data = (introduction_prompt | llm).invoke({})
        
        # Extract question text from the response
        if hasattr(question_data, 'content'):
            question_text = question_data.content.strip()
        else:
            question_text = str(question_data).strip()
        
        # Clean up any markdown or extra formatting
        question_text = question_text.strip('"').strip("'").strip()
        
        
        return question_text
        
    except Exception as e:
        print(f"Error generating introduction question: {e}")
        # If AI generation fails, raise an error with details - no hardcoded fallbacks
        raise RuntimeError(f"Failed to generate introduction question using AI: {str(e)}. Check your API key and LLM configuration.")

def ensure_persona_enum(persona_value):
    """Convert persona value to Persona enum if it's a string"""
    if isinstance(persona_value, Persona):
        return persona_value
    if isinstance(persona_value, str):
        return Persona(persona_value)
    return Persona.MENTOR

def ensure_candidate_persona_enum(candidate_persona_value):
    """Convert candidate_persona value to CandidatePersona enum if it's a string"""
    if isinstance(candidate_persona_value, CandidatePersona):
        return candidate_persona_value
    if isinstance(candidate_persona_value, str):
        return CandidatePersona(candidate_persona_value)
    return CandidatePersona.PROFESSIONAL

def start_interview(state: InterviewState) -> InterviewState:
    """Start a new interview session or continue existing one"""
    session_id = state["session_id"]
    max_questions = state["max_questions"]
    user_id = state.get("user_id")
    name = state.get("name")
    
    if not user_id:
        raise ValueError("user_id must be provided in the interview state")
    
    if not name:
        raise ValueError("name must be provided in the interview state")
    
    persona = ensure_persona_enum(state.get("persona", Persona.MENTOR))
    candidate_persona = ensure_candidate_persona_enum(state.get("candidate_persona", CandidatePersona.PROFESSIONAL))
    target_skills = state.get("target_skills", [])
    interview_domains = state.get("interview_domains")
    
    if state.get("interview_started", False):
        return state
    
    if not interview_domains:
        raise ValueError("interview_domains must be provided in the request body")
    
    domains_to_use = interview_domains
    
    if target_skills:
        domains_to_use = filter_domains_by_target_skills(target_skills, domains_to_use)
    
    state_manager = StateManager(domains_to_use, persona, candidate_persona)
    
    database = InterviewDatabase()
    database.save_session_start(session_id, user_id, max_questions)
    
    pronoun = state.get("pronoun")
    career_level = state.get("career_level")
    industry = state.get("industry")
    introduction_question = generate_introduction_question(persona, candidate_persona, name, pronoun=pronoun, career_level=career_level, industry=industry)
    
    return {
        **state,
        "current_question": introduction_question,
        "target_skills": [],
        "question_type": "introduction",
        "progress": state_manager.get_interview_progress(),
        "question_count": 0,
        "interview_started": False,
        "interview_complete": False,
        "persona": persona,
        "state_manager_data": serialize_state_manager(state_manager),
        "pronoun": pronoun,
        "career_level": career_level,
        "industry": industry
    }

def evaluate_response(state: InterviewState) -> InterviewState:
    """Evaluate the user response"""
    user_response = state["user_response"]
    session_id = state["session_id"]
    question_count = state["question_count"]
    
    print("curent_question number is ", question_count)
    # Reconstruct state manager
    state_manager = deserialize_state_manager(state["state_manager_data"])
    
    # Mark interview as started after first response
    if not state.get("interview_started", False):
        state["interview_started"] = True
    
    # Evaluate the response - only assess targeted skills
    target_skills = state.get("target_skills", [])
    if target_skills:
        evaluation = evaluate_response_targeted(user_response, state_manager, target_skills)
    else:
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
        
        # Generate summary with personalization
        persona = ensure_persona_enum(state.get("persona", Persona.MENTOR))
        candidate_persona = ensure_candidate_persona_enum(state.get("candidate_persona", CandidatePersona.PROFESSIONAL))
        summary = generate_summary(
            state_manager,
            name=state.get("name"),
            persona=persona,
            candidate_persona=candidate_persona,
            pronoun=state.get("pronoun"),
            career_level=state.get("career_level"),
            industry=state.get("industry")
        )
        final_results = state_manager.export_results()
        completion_reason = get_completion_reason(progress, question_count, state["max_questions"])
        
        # Save session completion
        database = InterviewDatabase()
        database.save_session_completion(
            session_id=session_id,
            final_results=final_results,
            completion_reason=completion_reason,
            summary=summary
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
        
        # Generate summary with personalization
        persona = ensure_persona_enum(state.get("persona", Persona.MENTOR))
        candidate_persona = ensure_candidate_persona_enum(state.get("candidate_persona", CandidatePersona.PROFESSIONAL))
        summary = generate_summary(
            state_manager,
            name=state.get("name"),
            persona=persona,
            candidate_persona=candidate_persona,
            pronoun=state.get("pronoun"),
            career_level=state.get("career_level"),
            industry=state.get("industry")
        )
        final_results = state_manager.export_results()
        completion_reason = get_completion_reason(progress, question_count, state["max_questions"])
        
        # Save session completion
        database = InterviewDatabase()
        database.save_session_completion(
            session_id=state["session_id"],
            final_results=final_results,
            completion_reason=completion_reason,
            summary=summary
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
    
    persona = ensure_persona_enum(state.get("persona", Persona.MENTOR))
    candidate_persona = ensure_candidate_persona_enum(state.get("candidate_persona", CandidatePersona.PROFESSIONAL))
    pronoun = state.get("pronoun")
    career_level = state.get("career_level")
    industry = state.get("industry")
    
    # Get previous questions to avoid repetition
    database = InterviewDatabase()
    previous_questions = database.get_previous_questions(state["session_id"], limit=10)
    
    next_question_result = get_next_question_contextual(
        state_manager, 
        state["last_response"], 
        state["evaluation"], 
        persona, 
        candidate_persona, 
        pronoun=pronoun, 
        career_level=career_level, 
        industry=industry,
        previous_questions=previous_questions
    )
    
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
        "interview_complete": state_manager.state.interview_complete,
        "persona": state_manager.state.persona,
        "candidate_persona": state_manager.state.candidate_persona
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
    persona = Persona(data.get("persona", "mentor"))
    candidate_persona = CandidatePersona(data.get("candidate_persona", "professional"))
    # Use domains from serialized data - no defaults
    domains_data = data.get("domains", [])
    if not domains_data:
        raise ValueError("No domain data found in serialized state")
    
    # The serialized domains are already in the correct format for StateManager
    # They were serialized using model_dump() which gives us the raw dict format
    reconstructed_domains = {"domains": domains_data}
    state_manager = StateManager(reconstructed_domains, persona, candidate_persona)
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
        interview_complete=data.get("interview_complete", False),
        persona=persona,
        candidate_persona=candidate_persona
    )
    

    
    return state_manager

def evaluate_response_targeted(user_response: str, state_manager: StateManager, target_skills: List[str]) -> Dict[str, Any]:
    """Evaluate a user response for ONLY the targeted skills"""
    
    # Get only the targeted skills from the domains
    targeted_skills = []
    for domain in state_manager.state.domains:
        for subdomain in domain.subdomains:
            for skill in subdomain.core_skills:
                if skill.name in target_skills:
                    targeted_skills.append({
                        "name": skill.name,
                        "domain": domain.name,
                        "knowledge_areas": skill.knowledge_areas,
                        "practical_applications": skill.practical_applications,
                        "level": skill.level
                    })
    
    try:
        from utils.graph_3_llm_helper import evaluate_response_with_llm
        evaluation = evaluate_response_with_llm(user_response, targeted_skills, previous_responses=state_manager.state.user_responses)
        return evaluation
    except Exception as e:
        print(f"Warning: LLM evaluation failed: {e}")
        raise e

def evaluate_response_comprehensive(user_response: str, state_manager: StateManager) -> Dict[str, Any]:
    """Evaluate a user response for ALL skills it might cover"""
    
    # Get ALL skills from the domains
    all_skills = []
    for domain in state_manager.state.domains:
        for subdomain in domain.subdomains:
            for skill in subdomain.core_skills:
                all_skills.append({
                    "name": skill.name,
                    "domain": domain.name,
                    "knowledge_areas": skill.knowledge_areas,
                    "practical_applications": skill.practical_applications,
                    "level": skill.level
                })
    
    try:
        from utils.graph_3_llm_helper import evaluate_response_with_llm
        evaluation = evaluate_response_with_llm(user_response, all_skills, previous_responses=state_manager.state.user_responses)
        return evaluation
    except Exception as e:
        print(f"Warning: LLM evaluation failed: {e}")
        raise e

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

def get_next_question_contextual(state_manager: StateManager, user_response: str, evaluation: Dict[str, Any], persona: Persona, candidate_persona: CandidatePersona, pronoun: Optional[str] = None, career_level: Optional[str] = None, industry: Optional[str] = None, previous_questions: Optional[List[str]] = None) -> Dict[str, Any]:
    """Get the next question based on previous response and remaining skills"""
    
    # Get uncovered skills
    uncovered_skills = state_manager.get_uncovered_skills()
    
    if not uncovered_skills:
        # All skills covered - generate AI completion message using base LLM
        try:
            completion_prompt = ChatPromptTemplate.from_messages([
                ("system", f"Generate a warm, personalized completion message as a {persona.value.replace('_', ' ')}. Thank them for their responses and acknowledge their participation. Return ONLY the completion message text, no JSON or extra formatting."),
                ("human", "Generate a completion message.")
            ])
            # Use base LLM for simple text response
            completion_response = (completion_prompt | llm).invoke({})
            completion_message = completion_response.content.strip()
            
            return {
                "question": completion_message,
                "target_skills": [],
                "question_type": "completion"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to generate completion message using AI: {str(e)}. Check your API key and LLM configuration.")
    
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
        # Get persona-specific prompt
        persona_prompt = PersonaHelper.get_question_generation_prompt(persona, candidate_persona, pronoun=pronoun, career_level=career_level, industry=industry)
        
        # Build previous questions context
        previous_questions_context = ""
        if previous_questions and len(previous_questions) > 0:
            previous_questions_context = f"""
CRITICAL: Avoid repeating similar questions. Here are the previous {len(previous_questions)} questions asked:
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(previous_questions)])}

IMPORTANT GUIDELINES TO AVOID REPETITION:
- Do NOT use similar opening phrases (e.g., "In your consulting work", "Thinking about your consulting work", "In a government consulting project")
- Do NOT ask about the same type of situation/scenario multiple times
- Vary your question structure completely - use different sentence patterns, question types, and approaches
- If previous questions mentioned specific contexts (e.g., "consulting work", "government consulting"), find NEW angles or contexts
- Use completely different phrasing, vocabulary, and sentence structure
- Make each question feel fresh and unique - avoid any patterns from previous questions
- Consider asking from different perspectives or about different aspects of their experience
- Change the focus: if previous questions were about challenges, ask about successes; if about teams, ask about individual work, etc.
"""
        
        question_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{persona_prompt}

Previous user response: {{previous_response}}
Skills to assess: {{skill_details}}
Last evaluation: {{last_evaluation}}
{previous_questions_context}

Generate a question that naturally follows from their previous response and assesses the target skills.

CRITICAL: The question MUST be completely different from all previous questions in structure, phrasing, opening, and approach. Avoid any patterns or similarities.

Return your response in JSON format with these fields:
- question_text: The interview question to ask (MUST be unique and different from previous questions)
- target_skills: List of core skills this question assesses
- question_type: Type of question (behavioral, situational, technical, etc.)
- difficulty_level: Easy, Medium, or Hard
- expected_indicators: What to look for in the response

Return ONLY valid JSON, no other text."""),
            ("human", "Please generate a contextual interview question.")
        ])
        
        # Use base LLM without structured output to avoid schema issues
        response = (question_prompt | llm).invoke({
            "previous_response": user_response or "No previous response",
            "skill_details": json.dumps(skill_details, indent=2),
            "last_evaluation": json.dumps(evaluation, indent=2) if evaluation else "No previous evaluation"
        })
        
        # Parse JSON from response
        response_text = response.content.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        question_data = json.loads(response_text)
        
        question_text = question_data.get('question_text', '')
        target_skills = question_data.get('target_skills', [])
        question_type = question_data.get('question_type', '')
        
        if question_text:
            return {
                "question": question_text,
                "target_skills": target_skills,
                "question_type": question_type
            }
        else:
            raise ValueError("Invalid question data returned from LLM: missing question_text")
    except Exception as e:
        # If AI generation fails, raise an error with details - no hardcoded fallbacks
        raise RuntimeError(f"Failed to generate contextual question using AI: {str(e)}. Check your API key and LLM configuration.")

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

def generate_summary(state_manager: StateManager, name: Optional[str] = None, persona: Optional[Persona] = None, candidate_persona: Optional[CandidatePersona] = None, pronoun: Optional[str] = None, career_level: Optional[str] = None, industry: Optional[str] = None) -> Dict[str, Any]:
    """Generate personalized interview summary"""
    
    results = state_manager.export_results()
    user_responses = state_manager.state.user_responses
    
    # Get persona style for personalization
    persona_style = None
    if persona:
        persona_style = PersonaHelper.get_persona_style(persona)
    
    # Build personalization context
    personalization_context = ""
    if name:
        personalization_context += f"\nCandidate Name: {name}\n"
    if pronoun:
        personalization_context += f"Use the pronoun '{pronoun}' when referring to the candidate.\n"
    if career_level:
        personalization_context += f"Career Level: {career_level}\n"
    if industry:
        personalization_context += f"Industry: {industry}\n"
    if persona:
        personalization_context += f"Interview Persona: {persona.value.replace('_', ' ').title()}\n"
    if candidate_persona:
        personalization_context += f"Candidate Type: {candidate_persona.value.title()}\n"
    
    # Build persona-specific tone guidance
    tone_guidance = ""
    if persona_style:
        tone_guidance = f"""
Write the overall assessment in a {persona_style['tone']} manner, with a {persona_style['approach']} approach, using {persona_style['language_style']} language. Make it feel personal and authentic, as if written by a {persona.value.replace('_', ' ')} who genuinely cares about {name if name else 'the candidate'}'s growth and development.
"""
    
    try:
        # Use a personalized approach with persona-specific tone
        summary_prompt = f"""You are an expert interview analyst writing a personalized assessment report. Generate a comprehensive, warm, and engaging summary of the interview results.

{personalization_context}

Interview Results: {json.dumps(results, indent=2)}
User Responses: {json.dumps(user_responses, indent=2)}

{tone_guidance}

Create a detailed summary including:
1. Overall assessment - Write a personalized, engaging overall assessment that:
   - Addresses {name if name else 'the candidate'} directly by name
   - Uses {pronoun if pronoun else 'their'} pronouns appropriately
   - Reflects on their specific journey and context (career level, industry if provided)
   - Incorporates the {persona.value.replace('_', ' ') if persona else 'mentor'} persona tone - {persona_style['tone'] if persona_style else 'warm and supportive'}
   - Makes it feel personal and meaningful, not generic or dry
   - Highlights what makes {name if name else 'them'} unique based on their responses
2. Domain-specific scores and analysis, but don't reveal domain names. Instead make it more humanely.
3. Key strengths identified - Frame these in a way that celebrates {name if name else 'the candidate'}'s unique qualities. Each strength MUST be a full sentence or a descriptive phrase (at least 8-10 words). Do NOT output single domain or skill names (e.g. not "Leadership", "Empathy", "Creativity"). Instead write what they demonstrated, e.g. "Demonstrated strong leadership by guiding the team through a difficult transition."
4. Areas for improvement - Present these constructively and supportively. Each item MUST be a full sentence or descriptive phrase (at least 8-10 words). Do NOT output single domain names (e.g. not "Emotional Security", "Alignment"). Instead write what they could improve and how, e.g. "Could strengthen how they maintain trust under pressure by sharing more concrete examples."
5. Specific recommendations for growth - Tailor these to {name if name else 'their'} career level and industry context. Each recommendation must be a full sentence.
6. Overall impressions and insights - Make this section feel like a genuine reflection on {name if name else 'the candidate'}'s potential
7. The language of summary should be very simple english, and it should be in a way that it is telling a story to the candidate.
Be thorough, {persona_style['tone'] if persona_style else 'warm'}, and constructive in your analysis. Write as if you're speaking directly to {name if name else 'the candidate'} or about {name if name else 'them'} in a way that feels personal and authentic.

Return your response as a JSON object with the following structure:
{{
    "overall_score": <numeric_score>,
    "strengths": ["Full sentence or descriptive phrase for strength 1.", "Full sentence or descriptive phrase for strength 2.", ...],
    "areas_for_improvement": ["Full sentence or descriptive phrase for area 1.", "Full sentence or descriptive phrase for area 2.", ...],
    "recommendations": ["Full sentence recommendation 1.", "Full sentence recommendation 2.", ...],
    "analysis": "detailed, personalized analysis text that addresses the candidate by name and feels warm and engaging"
}}
CRITICAL: Every item in "strengths" and "areas_for_improvement" must be a complete sentence or phrase (minimum 8 words). Never use only a domain or skill name as an item."""

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
    """Build the LangGraph interview flow with checkpointing"""
    
    workflow = StateGraph(InterviewState)
    
    workflow.add_node("start_interview", start_interview)
    workflow.add_node("evaluate_response", evaluate_response)
    workflow.add_node("generate_question", generate_question)
    
    workflow.set_entry_point("start_interview")
    
    workflow.add_conditional_edges(
        "start_interview",
        should_start_interview,
        {
            "start": END,
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
    
    workflow.add_edge("generate_question", END)
    
    conn_string = DATABASE_URL.replace("+psycopg2", "")
    pool = ConnectionPool(conninfo=conn_string)
    checkpoint = PostgresSaver(pool)
    checkpoint.setup()
    
    return workflow.compile(checkpointer=checkpoint)

from typing import Dict, List, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
import json
import time
from datetime import datetime

from utils.state_manager import StateManager, InterviewState
from utils.graph_3_llm_helper import (
    topic_selector_llm, 
    question_generator_llm, 
    evaluation_llm,
    summarizer_llm
)
from utils.graph_1_interview_domains import INTERVIEW_DOMAINS

# Define the state structure for the graph
class InterviewGraphState(TypedDict):
    state_manager: StateManager
    current_question: str
    user_response: str
    topic_selection: Dict[str, Any]
    question_data: Dict[str, Any]
    evaluation: Dict[str, Any]
    interview_complete: bool
    messages: List[Any]
    session_id: str

def create_interviewer_graph() -> StateGraph:
    """Create the LangGraph for the automated interviewer"""
    
    # Initialize the graph
    workflow = StateGraph(InterviewGraphState)
    
    # Add nodes
    workflow.add_node("select_topic", select_next_topic)
    workflow.add_node("generate_question", generate_interview_question)
    workflow.add_node("evaluate_response", evaluate_user_response)
    workflow.add_node("update_state", update_interview_state)
    workflow.add_node("check_completion", check_interview_completion)
    workflow.add_node("generate_summary", generate_interview_summary)
    
    # Define the flow
    workflow.set_entry_point("select_topic")
    
    # Main flow
    workflow.add_edge("select_topic", "generate_question")
    workflow.add_edge("generate_question", "evaluate_response")
    workflow.add_edge("evaluate_response", "update_state")
    workflow.add_edge("update_state", "check_completion")
    
    # Conditional edges
    workflow.add_conditional_edges(
        "check_completion",
        should_continue_interview,
        {
            "continue": "select_topic",
            "complete": "generate_summary"
        }
    )
    
    workflow.add_edge("generate_summary", END)
    
    return workflow.compile()

def select_next_topic(state: InterviewGraphState) -> InterviewGraphState:
    """Select the next topic to cover based on uncovered skills"""
    
    state_manager = state["state_manager"]
    uncovered_skills = state_manager.get_uncovered_skills()
    covered_skills = state_manager.get_covered_skills()
    progress = state_manager.get_interview_progress()
    
    if not uncovered_skills:
        # All skills covered, interview is complete
        state["interview_complete"] = True
        return state
    
    # Create prompt for topic selection
    topic_selection_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an intelligent interview coordinator. Your job is to select the next topic to assess based on the current interview progress.

Available uncovered skills: {uncovered_skills}

Already covered skills: {covered_skills}

Current progress: {progress_percentage}% complete

Consider the following when selecting:
1. Prioritize skills that haven't been assessed yet
2. Group related skills together when possible to maximize efficiency
3. Consider the difficulty level and logical flow
4. Balance between different domains and subdomains
5. Focus on skills that can be assessed with a single comprehensive question

Select the most appropriate domain, subdomain, and skills to assess next."""),
        ("human", "Please select the next topic to cover in this interview.")
    ])
    
    # Format the data for the prompt
    uncovered_skills_text = json.dumps(uncovered_skills, indent=2)
    covered_skills_text = json.dumps(covered_skills, indent=2)
    
    # Get topic selection from LLM
    topic_selection = topic_selector_llm.invoke(
        topic_selection_prompt.format_messages(
            uncovered_skills=uncovered_skills_text,
            covered_skills=covered_skills_text,
            progress_percentage=progress["progress_percentage"]
        )
    )
    
    state["topic_selection"] = topic_selection.model_dump()
    return state

def generate_interview_question(state: InterviewGraphState) -> InterviewGraphState:
    """Generate an interview question based on the selected topic"""
    
    topic_selection = state["topic_selection"]
    selected_skills = topic_selection["selected_skills"]
    
    # Get skill details for question generation
    skill_details = []
    for skill_name in selected_skills:
        for domain in state["state_manager"].state.domains:
            for subdomain in domain.subdomains:
                for skill in subdomain.core_skills:
                    if skill.name == skill_name:
                        skill_details.append({
                            "name": skill.name,
                            "knowledge_areas": skill.knowledge_areas,
                            "practical_applications": skill.practical_applications,
                            "level": skill.level
                        })
                        break
    
    question_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert interviewer. Generate a comprehensive question that can assess multiple skills simultaneously.

Selected skills to assess: {skill_details}

Guidelines for question generation:
1. Create a behavioral or situational question that naturally covers multiple skills
2. Make the question engaging and realistic
3. Ensure it can reveal the candidate's knowledge and practical application
4. Consider the difficulty level of the skills
5. Ask for specific examples or experiences
6. Make it open-ended enough to allow detailed responses

Generate a question that will effectively assess these skills."""),
        ("human", "Please generate an interview question for these skills.")
    ])
    
    # Generate question
    question_data = question_generator_llm.invoke(
        question_prompt.format_messages(
            skill_details=json.dumps(skill_details, indent=2)
        )
    )
    
    state["question_data"] = question_data.model_dump()
    state["current_question"] = question_data.question_text
    
    return state

def evaluate_user_response(state: InterviewGraphState) -> InterviewGraphState:
    """Evaluate the user's response and assign scores to skills"""
    
    user_response = state["user_response"]
    question_data = state["question_data"]
    target_skills = question_data["target_skills"]
    expected_indicators = question_data["expected_indicators"]
    
    evaluation_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert evaluator. Analyze the user's response and assign scores to the target skills.

Question asked: {question_text}
Target skills: {target_skills}
Expected indicators: {expected_indicators}
User response: {user_response}

Evaluation guidelines:
1. Score each skill on a scale of 0-10
2. 0-3: Poor or no demonstration of the skill
3. 4-6: Basic demonstration with room for improvement
4. 7-8: Good demonstration of the skill
5. 9-10: Excellent demonstration of the skill
6. Consider both knowledge and practical application
7. Look for specific examples and experiences
8. Assess confidence and clarity in the response

IMPORTANT: For skill_scores, return a proper JSON object with skill names as keys and numeric scores as values.
Example: {{"Clarity of Thought": 7.5, "Problem-Solving Confidence": 8.0}}

Provide detailed reasoning for each score and determine if follow-up questions are needed."""),
        ("human", "Please evaluate this response.")
    ])
    
    # Evaluate response
    evaluation = evaluation_llm.invoke(
        evaluation_prompt.format_messages(
            question_text=question_data["question_text"],
            target_skills=target_skills,
            expected_indicators=expected_indicators,
            user_response=user_response
        )
    )
    
    state["evaluation"] = evaluation.model_dump()
    return state

def update_interview_state(state: InterviewGraphState) -> InterviewGraphState:
    """Update the interview state with the evaluation results"""
    
    state_manager = state["state_manager"]
    evaluation = state["evaluation"]
    user_response = state["user_response"]
    
    # Add response to state
    response_data = {
        "question": state["current_question"],
        "response": user_response,
        "evaluation": evaluation,
        "timestamp": datetime.now().isoformat(),
        "session_id": state["session_id"]
    }
    state_manager.add_user_response(response_data)
    
    # Update skill scores
    state_manager.update_skill_scores(
        evaluation["skill_scores"], 
        response_data
    )
    
    return state

def check_interview_completion(state: InterviewGraphState) -> InterviewGraphState:
    """Check if the interview is complete"""
    
    state_manager = state["state_manager"]
    progress = state_manager.get_interview_progress()
    
    # Check if all skills are covered or if we've reached a reasonable stopping point
    if progress["progress_percentage"] >= 95 or progress["covered_skills"] >= progress["total_skills"]:
        state["interview_complete"] = True
        state_manager.state.interview_complete = True
    
    return state

def should_continue_interview(state: InterviewGraphState) -> str:
    """Determine if the interview should continue or end"""
    
    if state["interview_complete"]:
        return "complete"
    else:
        return "continue"

def generate_interview_summary(state: InterviewGraphState) -> InterviewGraphState:
    """Generate a comprehensive summary of the interview"""
    
    state_manager = state["state_manager"]
    results = state_manager.export_results()
    user_responses = state_manager.state.user_responses
    
    summary_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert interview analyst. Generate a comprehensive summary of the interview results.

Interview Results: {results}
User Responses: {user_responses}

Create a detailed summary including:
1. Overall assessment score and interpretation
2. Domain-specific scores and analysis
3. Key strengths identified
4. Areas for improvement
5. Specific recommendations for growth
6. Overall impressions and insights

Be thorough, professional, and constructive in your analysis."""),
        ("human", "Please generate a comprehensive interview summary.")
    ])
    
    # Generate summary
    summary = summarizer_llm.invoke(
        summary_prompt.format_messages(
            results=json.dumps(results, indent=2),
            user_responses=json.dumps(user_responses, indent=2)
        )
    )
    
    state["interview_summary"] = summary.model_dump()
    return state

class AutomatedInterviewer:
    """Main class for the automated interviewer"""
    
    def __init__(self):
        self.graph = create_interviewer_graph()
        self.state_manager = StateManager(INTERVIEW_DOMAINS)
    
    def start_interview(self, session_id: str = None) -> Dict[str, Any]:
        """Start a new interview session"""
        
        if session_id is None:
            session_id = f"interview_{int(time.time())}"
        
        # Initialize the graph state
        initial_state = InterviewGraphState(
            state_manager=self.state_manager,
            current_question="",
            user_response="",
            topic_selection={},
            question_data={},
            evaluation={},
            interview_complete=False,
            messages=[],
            session_id=session_id
        )
        
        # Run the graph to get the first question
        config = {"configurable": {"thread_id": session_id}}
        result = self.graph.invoke(initial_state, config)
        
        return {
            "session_id": session_id,
            "current_question": result["current_question"],
            "target_skills": result["question_data"]["target_skills"],
            "question_type": result["question_data"]["question_type"],
            "progress": self.state_manager.get_interview_progress()
        }
    
    def submit_response(self, user_response: str, session_id: str) -> Dict[str, Any]:
        """Submit a user response and get the next question or results"""
        
        # Create state with user response
        current_state = InterviewGraphState(
            state_manager=self.state_manager,
            current_question="",
            user_response=user_response,
            topic_selection={},
            question_data={},
            evaluation={},
            interview_complete=False,
            messages=[],
            session_id=session_id
        )
        
        # Run the graph
        config = {"configurable": {"thread_id": session_id}}
        result = self.graph.invoke(current_state, config)
        
        if result["interview_complete"]:
            return {
                "interview_complete": True,
                "summary": result["interview_summary"],
                "final_results": self.state_manager.export_results()
            }
        else:
            return {
                "interview_complete": False,
                "current_question": result["current_question"],
                "target_skills": result["question_data"]["target_skills"],
                "question_type": result["question_data"]["question_type"],
                "progress": self.state_manager.get_interview_progress(),
                "last_evaluation": result["evaluation"]
            }
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current interview progress"""
        return self.state_manager.get_interview_progress()
    
    def get_results(self) -> Dict[str, Any]:
        """Get current interview results"""
        return self.state_manager.export_results()
    
    def reset_interview(self):
        """Reset the interview state"""
        self.state_manager = StateManager(INTERVIEW_DOMAINS)

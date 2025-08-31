# #!/usr/bin/env python3
# """
# Simple Automated Interviewer without LangGraph
# """

# import json
# import time
# from datetime import datetime
# from typing import Dict, List, Any, Optional

# from utils.state_manager import StateManager
# from utils.graph_3_llm_helper import (
#     question_generator_llm, 
#     evaluation_llm,
#     summarizer_llm
# )
# from utils.graph_1_interview_domains import INTERVIEW_DOMAINS
# from utils.database import InterviewDatabase
# from langchain_core.prompts import ChatPromptTemplate

# class SimpleAutomatedInterviewer:
#     """Simplified automated interviewer without LangGraph"""
    
#     def __init__(self, max_questions: int = 3):
#         self.state_manager = StateManager(INTERVIEW_DOMAINS)
#         self.current_session_id = None
#         self.interview_started = False  # Track if introduction is complete
#         self.last_response = None  # Store the last user response for context
#         self.max_questions = max_questions  # Maximum number of questions allowed
#         self.question_count = 0  # Track number of questions asked
#         self.database = InterviewDatabase()  # Database for storing responses
    
#     def start_interview(self, session_id: str = None) -> Dict[str, Any]:
#         """Start a new interview session with a fixed introduction question"""
        
#         if session_id is None:
#             session_id = f"interview_{int(time.time())}"
        
#         self.current_session_id = session_id
#         self.interview_started = False
#         self.last_response = None
#         self.question_count = 0  # Reset question count for new interview
        
#         # Save session start to database
#         self.database.save_session_start(session_id, self.max_questions)
        
#         # Always start with the introduction question
#         return {
#             "session_id": session_id,
#             "current_question": "Please give us a brief introduction about yourself. Tell us about your background, experiences, and what brings you here today. This will help us understand your perspective and tailor the interview to your specific situation.",
#             "target_skills": [],  # Introduction question doesn't target specific skills
#             "question_type": "introduction",
#             "progress": self.state_manager.get_interview_progress()
#         }
    
#     def submit_response(self, user_response: str, session_id: str) -> Dict[str, Any]:
#         """Submit a user response and get the next question or results"""
        
#         if session_id != self.current_session_id:
#             raise ValueError("Session ID mismatch")
        
#         # Store the response for context
#         self.last_response = user_response
        
#         # Evaluate the response for ALL skills it might cover
#         evaluation = self._evaluate_response_comprehensive(user_response)
        
#         # Add hierarchical skill scores to evaluation
#         if "skill_scores" in evaluation:
#             evaluation["hierarchical_skill_scores"] = self.state_manager.convert_flat_scores_to_hierarchical(evaluation["skill_scores"])
        
#         # Update state
#         self._update_state(user_response, evaluation)
        
#         # Store the current question text for database
#         self.current_question_text = self._get_current_question_text()
        
#         # If this was the introduction, mark interview as started
#         if not self.interview_started:
#             self.interview_started = True
        
#         # Increment question count first
#         self.question_count += 1
        
#         # Save response to database
#         response_id = self.database.save_response(
#             session_id=self.current_session_id,
#             question_number=self.question_count,
#             question_text=self.current_question_text,
#             user_response=user_response,
#             question_type=self._get_question_type(),
#             target_skills=self._get_target_skills()
#         )
        
#         # Save evaluation to database
#         self.database.save_evaluation(
#             session_id=self.current_session_id,
#             response_id=response_id,
#             evaluation=evaluation
#         )
        
#         # Check if interview is complete
#         progress = self.state_manager.get_interview_progress()
        
#         # Check completion conditions: progress, skills covered, or max questions reached
#         if (progress["progress_percentage"] >= 99 or 
#             progress["covered_skills"] >= progress["total_skills"] or
#             self.question_count >= self.max_questions):
            
#             # Generate summary
#             summary = self._generate_summary()
#             final_results = self.state_manager.export_results()
#             completion_reason = self._get_completion_reason(progress)
            
#             # Save session completion to database
#             self.database.save_session_completion(
#                 session_id=self.current_session_id,
#                 final_results=final_results,
#                 completion_reason=completion_reason
#             )
            
#             return {
#                 "interview_complete": True,
#                 "summary": summary,
#                 "final_results": final_results,
#                 "completion_reason": completion_reason
#             }
#         else:
#             # Get next question based on previous response
#             result = self._get_next_question_contextual()
#             return {
#                 "interview_complete": False,
#                 "current_question": result["question"],
#                 "target_skills": result["target_skills"],
#                 "question_type": result["question_type"],
#                 "progress": self.state_manager.get_interview_progress(),
#                 "last_evaluation": evaluation,
#                 "question_number": self.question_count,
#                 "max_questions": self.max_questions
#             }
    
#     def _get_next_question_contextual(self) -> Dict[str, Any]:
#         """Get the next question based on previous response and remaining skills"""
        
#         # Get uncovered skills
#         uncovered_skills = self.state_manager.get_uncovered_skills()
#         covered_skills = self.state_manager.get_covered_skills()
#         progress = self.state_manager.get_interview_progress()
        
#         if not uncovered_skills:
#             # All skills covered
#             return {
#                 "question": "Interview complete! Thank you for your responses.",
#                 "target_skills": [],
#                 "question_type": "completion"
#             }
        
#         # Get the last evaluation to understand what was covered
#         last_evaluation = None
#         if self.state_manager.state.user_responses:
#             last_response_data = self.state_manager.state.user_responses[-1]
#             last_evaluation = last_response_data.get("evaluation", {})
        
#         # Select skills to target based on context
#         target_skills = self._select_target_skills_contextual(uncovered_skills, last_evaluation)
        
#         # Generate contextual question
#         skill_details = []
#         for skill_info in target_skills:
#             skill_details.append({
#                 "name": skill_info["skill"],
#                 "knowledge_areas": skill_info["knowledge_areas"],
#                 "practical_applications": skill_info["practical_applications"],
#                 "level": skill_info["level"]
#             })
        
#         try:
#             question_prompt = ChatPromptTemplate.from_messages([
#                 ("system", """You are an expert interviewer. Generate a contextual question that builds upon the user's previous response and assesses the target skills.

# Previous user response: {previous_response}
# Skills to assess: {skill_details}
# Last evaluation: {last_evaluation}

# Guidelines for question generation:
# 1. Build upon what the user shared in their previous response
# 2. Create a natural follow-up question that flows from their experience
# 3. Target the specific skills that still need assessment
# 4. Make the question engaging and relevant to their background
# 5. Ask for specific examples or experiences related to the target skills
# 6. Make it open-ended enough to allow detailed responses
# 7. Connect to their previous response when possible

# Generate a question that naturally follows from their previous response and assesses the target skills."""),
#                 ("human", "Please generate a contextual interview question.")
#             ])
            
#             question_data = question_generator_llm.invoke(
#                 question_prompt.format_messages(
#                     previous_response=self.last_response or "No previous response",
#                     skill_details=json.dumps(skill_details, indent=2),
#                     last_evaluation=json.dumps(last_evaluation, indent=2) if last_evaluation else "No previous evaluation"
#                 )
#             )
            
#             return {
#                 "question": question_data.question_text,
#                 "target_skills": question_data.target_skills,
#                 "question_type": question_data.question_type
#             }
#         except Exception as e:
#             # Fallback question if LLM fails
#             print(f"Warning: LLM question generation failed: {e}")
#             return {
#                 "question": f"Based on what you shared, could you tell me more about a time when you demonstrated {skill_details[0]['name']} and {skill_details[1]['name'] if len(skill_details) > 1 else 'your skills'}? What was the context, what actions did you take, and what was the outcome?",
#                 "target_skills": [skill["name"] for skill in skill_details],
#                 "question_type": "behavioral"
#             }
    
#     def _select_target_skills_contextual(self, uncovered_skills: List[Dict], last_evaluation: Dict) -> List[Dict]:
#         """Select target skills based on context and previous response"""
        
#         # If this is the first question after introduction, prioritize skills that weren't covered
#         if not last_evaluation or not last_evaluation.get("skill_scores"):
#             # Take first 2-3 uncovered skills
#             return uncovered_skills[:3]
        
#         # Get skills that were scored in the last response
#         last_skills_covered = last_evaluation.get("skill_scores", {}).keys()
        
#         # Find skills that are related to the previously covered skills
#         related_skills = []
#         unrelated_skills = []
        
#         for skill_info in uncovered_skills:
#             skill_name = skill_info["skill"]
            
#             # Check if this skill is related to previously covered skills
#             # (same domain or subdomain)
#             is_related = False
#             for covered_skill in last_skills_covered:
#                 # Check if they're in the same domain/subdomain
#                 for domain in self.state_manager.state.domains:
#                     for subdomain in domain.subdomains:
#                         skill_names = [s.name for s in subdomain.core_skills]
#                         if skill_name in skill_names and covered_skill in skill_names:
#                             is_related = True
#                             break
#                     if is_related:
#                         break
#                 if is_related:
#                     break
            
#             if is_related:
#                 related_skills.append(skill_info)
#             else:
#                 unrelated_skills.append(skill_info)
        
#         # Prioritize related skills first, then add some unrelated ones for diversity
#         target_skills = []
        
#         # Add 1-2 related skills if available
#         if related_skills:
#             target_skills.extend(related_skills[:2])
        
#         # Add 1-2 unrelated skills for diversity
#         if unrelated_skills and len(target_skills) < 3:
#             target_skills.extend(unrelated_skills[:3-len(target_skills)])
        
#         # If we don't have enough skills, add more from uncovered
#         if len(target_skills) < 2:
#             remaining = [s for s in uncovered_skills if s not in target_skills]
#             target_skills.extend(remaining[:2-len(target_skills)])
        
#         return target_skills[:3]  # Limit to 3 skills max
    
#     def _get_next_question(self) -> Dict[str, Any]:
#         """Legacy method - kept for compatibility"""
#         return self._get_next_question_contextual()
    
#     def _evaluate_response_comprehensive(self, user_response: str) -> Dict[str, Any]:
#         """Evaluate a user response for ALL skills it might cover"""
        
#         # Get ALL skills from the domains
#         all_skills = []
#         for domain in self.state_manager.state.domains:
#             for subdomain in domain.subdomains:
#                 for skill in subdomain.core_skills:
#                     all_skills.append({
#                         "name": skill.name,
#                         "knowledge_areas": skill.knowledge_areas,
#                         "practical_applications": skill.practical_applications,
#                         "level": skill.level
#                     })
        
#         try:
#             # Use the custom evaluation function
#             from utils.graph_3_llm_helper import evaluate_response_with_llm
#             evaluation = evaluate_response_with_llm(user_response, all_skills)
#             return evaluation
#         except Exception as e:
#             # Fallback evaluation if LLM fails
#             print(f"Warning: LLM evaluation failed: {e}")
#             # For fallback, just score a few basic skills
#             fallback_skills = ["Clarity of Thought", "Problem-Solving Confidence"]
#             return {
#                 "skill_scores": {skill: 5.0 for skill in fallback_skills},
#                 "confidence_level": 0.5,
#                 "reasoning": "Fallback evaluation due to LLM error",
#                 "follow_up_needed": False,
#                 "skills_covered": fallback_skills
#             }
    
#     def _update_state(self, user_response: str, evaluation: Dict[str, Any]):
#         """Update the interview state"""
        
#         # Add response to state
#         response_data = {
#             "response": user_response,
#             "evaluation": evaluation,
#             "timestamp": datetime.now().isoformat(),
#             "session_id": self.current_session_id
#         }
#         self.state_manager.add_user_response(response_data)
        
#         # Update skill scores
#         skill_scores = evaluation.get("skill_scores", {})
#         if isinstance(skill_scores, str):
#             try:
#                 skill_scores = json.loads(skill_scores)
#             except (json.JSONDecodeError, TypeError):
#                 skill_scores = {}
        
#         if isinstance(skill_scores, dict):
#             self.state_manager.update_skill_scores(skill_scores, response_data)
    
#     def _get_completion_reason(self, progress: Dict[str, Any]) -> str:
#         """Determine why the interview completed"""
#         if progress["progress_percentage"] >= 95:
#             return "Progress threshold reached (95%+)"
#         elif progress["covered_skills"] >= progress["total_skills"]:
#             return "All skills covered"
#         elif self.question_count >= self.max_questions:
#             return f"Maximum questions reached ({self.max_questions})"
#         else:
#             return "Unknown completion reason"
    
#     def _generate_summary(self) -> Dict[str, Any]:
#         """Generate interview summary"""
        
#         results = self.state_manager.export_results()
#         user_responses = self.state_manager.state.user_responses
        
#         try:
#             summary_prompt = ChatPromptTemplate.from_messages([
#                 ("system", """You are an expert interview analyst. Generate a comprehensive summary of the interview results.

# Interview Results: {results}
# User Responses: {user_responses}

# Create a detailed summary including:
# 1. Overall assessment score and interpretation
# 2. Domain-specific scores and analysis
# 3. Key strengths identified
# 4. Areas for improvement
# 5. Specific recommendations for growth
# 6. Overall impressions and insights

# Be thorough, professional, and constructive in your analysis."""),
#                 ("human", "Please generate a comprehensive interview summary.")
#             ])
            
#             summary = summarizer_llm.invoke(
#                 summary_prompt.format_messages(
#                     results=json.dumps(results, indent=2),
#                     user_responses=json.dumps(user_responses, indent=2)
#                 )
#             )
            
#             return summary.model_dump()
#         except Exception as e:
#             # Fallback summary if LLM fails
#             print(f"Warning: LLM summary generation failed: {e}")
#             return {
#                 "overall_score": results.get("overall_score", 0),
#                 "strengths": ["Good communication skills", "Problem-solving ability"],
#                 "areas_for_improvement": ["Could provide more specific examples"],
#                 "recommendations": ["Continue developing skills through practice"]
#             }
    
#     def get_progress(self) -> Dict[str, Any]:
#         """Get current interview progress"""
#         return self.state_manager.get_interview_progress()
    
#     def get_results(self) -> Dict[str, Any]:
#         """Get current interview results"""
#         return self.state_manager.export_results()
    
#     def _get_current_question_text(self) -> str:
#         """Get the current question text"""
#         if self.question_count == 0:
#             return "Please give us a brief introduction about yourself. Tell us about your background, experiences, and what brings you here today. This will help us understand your perspective and tailor the interview to your specific situation."
#         else:
#             # Get the last question from the state manager
#             if self.state_manager.state.user_responses:
#                 last_response_data = self.state_manager.state.user_responses[-1]
#                 return last_response_data.get("question_text", "Unknown question")
#             return "Unknown question"
    
#     def _get_question_type(self) -> str:
#         """Get the current question type"""
#         if self.question_count == 0:
#             return "introduction"
#         else:
#             return "behavioral"
    
#     def _get_target_skills(self) -> List[str]:
#         """Get the current target skills"""
#         if self.question_count == 0:
#             return []
#         else:
#             # Get target skills from the last question generation
#             uncovered_skills = self.state_manager.get_uncovered_skills()
#             if uncovered_skills:
#                 return [skill["skill"] for skill in uncovered_skills[:3]]  # Top 3 skills
#             return []
    
#     def reset_interview(self):
#         """Reset the interview state"""
#         self.state_manager = StateManager(INTERVIEW_DOMAINS)
#         self.current_session_id = None
#         self.interview_started = False
#         self.last_response = None

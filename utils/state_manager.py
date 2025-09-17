from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
import json

class SkillLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class Persona(str, Enum):
    THERAPIST = "therapist"
    CLOSE_FRIEND = "close_friend"
    FAMILY_MEMBER = "family_member"
    MENTOR = "mentor"
    COLLEAGUE = "colleague"
    COACH = "coach"
    PROFESSOR = "professor"
    MANAGER = "manager"

class CandidatePersona(str, Enum):
    STUDENT = "student"
    PROFESSIONAL = "professional"

class CoreSkill(BaseModel):
    name: str
    score: float = Field(default=0.0, ge=0.0, le=10.0)
    covered: bool = Field(default=False)
    knowledge_areas: List[str] = Field(default_factory=list)
    practical_applications: List[str] = Field(default_factory=list)
    level: SkillLevel = Field(default=SkillLevel.MEDIUM)
    assessment_history: List[Dict[str, Any]] = Field(default_factory=list)
    asked_in_question: bool = Field(default=False)

class Subdomain(BaseModel):
    name: str
    core_skills: List[CoreSkill] = Field(default_factory=list)
    covered: bool = Field(default=False)

class Domain(BaseModel):
    name: str
    subdomains: List[Subdomain] = Field(default_factory=list)
    covered: bool = Field(default=False)

class InterviewState(BaseModel):
    domains: List[Domain] = Field(default_factory=list)
    current_domain: Optional[str] = None
    current_subdomain: Optional[str] = None
    current_question: Optional[str] = None
    interview_progress: float = Field(default=0.0, ge=0.0, le=100.0)
    total_skills: int = Field(default=0)
    covered_skills: int = Field(default=0)
    session_id: Optional[str] = None
    user_responses: List[Dict[str, Any]] = Field(default_factory=list)
    interview_complete: bool = Field(default=False)
    persona: Persona = Field(default=Persona.MENTOR)
    candidate_persona: CandidatePersona = Field(default=CandidatePersona.PROFESSIONAL)



class Question(BaseModel):
    """Model for generating interview questions"""
    question_text: str = Field(description="The interview question to ask")
    target_skills: List[str] = Field(description="Core skills this question assesses")
    question_type: str = Field(description="Type of question: behavioral, situational, technical, etc.")
    difficulty_level: str = Field(description="Easy, Medium, or Hard")
    expected_indicators: List[str] = Field(description="What to look for in the response")



class InterviewSummary(BaseModel):
    """Model for summarizing the complete interview"""
    overall_score: float = Field(description="Overall assessment score (0-10)")
    domain_scores: Dict[str, float] = Field(description="Scores for each domain")
    skill_scores: Dict[str, float] = Field(description="Final scores for each core skill")
    strengths: List[str] = Field(description="Identified strengths")
    areas_for_improvement: List[str] = Field(description="Areas that need improvement")
    recommendations: List[str] = Field(description="Specific recommendations for growth")
    interview_duration: Optional[float] = Field(description="Duration of interview in minutes")

class StateManager:
    """Manages the interview state and provides utility methods"""
    
    def __init__(self, interview_domains: Dict[str, Any], persona: Persona = Persona.MENTOR, candidate_persona: CandidatePersona = CandidatePersona.PROFESSIONAL):
        self.state = self._initialize_state(interview_domains, persona, candidate_persona)
    
    def _initialize_state(self, interview_domains: Dict[str, Any], persona: Persona, candidate_persona: CandidatePersona) -> InterviewState:
        """Initialize the interview state from the domains data"""
        domains = []
        total_skills = 0
        
        for domain_data in interview_domains.get("domains", []):
            subdomains = []
            
            for subdomain_data in domain_data.get("subdomains", []):
                core_skills = []
                
                for skill_data in subdomain_data.get("core_skills", []):
                    skill = CoreSkill(
                        name=skill_data["name"],
                        knowledge_areas=skill_data.get("knowledge_areas", []),
                        practical_applications=skill_data.get("practical_applications", []),
                        level=SkillLevel(skill_data.get("level", "Medium"))
                    )
                    core_skills.append(skill)
                    total_skills += 1
                
                subdomain = Subdomain(
                    name=subdomain_data["name"],
                    core_skills=core_skills
                )
                subdomains.append(subdomain)
            
            domain = Domain(
                name=domain_data["name"],
                subdomains=subdomains
            )
            domains.append(domain)
        
        return InterviewState(
            domains=domains,
            total_skills=total_skills,
            persona=persona,
            candidate_persona=candidate_persona
        )
    
    def get_uncovered_skills(self) -> List[Dict[str, Any]]:
        """Get all skills that haven't been covered yet"""
        uncovered_skills = []
        
        for domain in self.state.domains:
            for subdomain in domain.subdomains:
                for skill in subdomain.core_skills:
                    if not skill.covered:
                        uncovered_skills.append({
                            "domain": domain.name,
                            "subdomain": subdomain.name,
                            "skill": skill.name,
                            "level": skill.level,
                            "knowledge_areas": skill.knowledge_areas,
                            "practical_applications": skill.practical_applications
                        })
        
        return uncovered_skills
    
    def get_skills_never_asked_in_questions(self) -> List[Dict[str, Any]]:
        """Get skills that have never been asked about in questions (only covered in answers)"""
        never_asked_skills = []
        
        for domain in self.state.domains:
            for subdomain in domain.subdomains:
                for skill in subdomain.core_skills:
                    if skill.covered and not skill.asked_in_question:
                        never_asked_skills.append({
                            "domain": domain.name,
                            "subdomain": subdomain.name,
                            "skill": skill.name,
                            "level": skill.level,
                            "knowledge_areas": skill.knowledge_areas,
                            "practical_applications": skill.practical_applications,
                            "score": skill.score,
                            "covered": skill.covered,
                            "asked_in_question": skill.asked_in_question
                        })
        
        return never_asked_skills
    
    def get_skills_needing_direct_questions(self) -> List[Dict[str, Any]]:
        """Get skills that need direct questions based on low scores or never being asked"""
        skills_needing_questions = []
        
        for domain in self.state.domains:
            for subdomain in domain.subdomains:
                for skill in subdomain.core_skills:
                    # Skills that need direct questions:
                    # 1. Never asked about in questions (highest priority)
                    # 2. Uncovered skills
                    # 3. Low scores (below 5.0) but only if not already asked about
                    needs_question = (
                        not skill.asked_in_question or 
                        not skill.covered
                    )
                    
                    if needs_question:
                        skills_needing_questions.append({
                            "domain": domain.name,
                            "subdomain": subdomain.name,
                            "skill": skill.name,
                            "level": skill.level,
                            "knowledge_areas": skill.knowledge_areas,
                            "practical_applications": skill.practical_applications,
                            "score": skill.score,
                            "covered": skill.covered,
                            "asked_in_question": skill.asked_in_question,
                            "priority_score": self._calculate_question_priority(skill)
                        })
        
        # Sort by priority score (higher priority first)
        skills_needing_questions.sort(key=lambda x: x["priority_score"], reverse=True)
        return skills_needing_questions
    
    def _calculate_question_priority(self, skill) -> float:
        """Calculate priority score for asking a question about a skill"""
        priority = 0.0
        
        # Highest priority: never asked about in questions
        if not skill.asked_in_question:
            priority += 1000.0  # Much higher priority to ensure these are asked first
        
        # High priority: low scores
        if skill.score < 3.0:
            priority += 50.0
        elif skill.score < 5.0:
            priority += 30.0
        elif skill.score < 7.0:
            priority += 15.0
        
        # Medium priority: uncovered skills
        if not skill.covered:
            priority += 25.0
        
        # Lower priority: higher difficulty levels
        if skill.level == SkillLevel.HARD:
            priority += 10.0
        elif skill.level == SkillLevel.MEDIUM:
            priority += 5.0
        
        return priority
    
    def mark_skill_asked_in_question(self, skill_name: str):
        """Mark a skill as having been asked about in a question"""
        for domain in self.state.domains:
            for subdomain in domain.subdomains:
                for skill in subdomain.core_skills:
                    if skill.name == skill_name:
                        skill.asked_in_question = True
                        return
    
    def get_covered_skills(self) -> List[Dict[str, Any]]:
        """Get all skills that have been covered"""
        covered_skills = []
        
        for domain in self.state.domains:
            for subdomain in domain.subdomains:
                for skill in subdomain.core_skills:
                    if skill.covered:
                        covered_skills.append({
                            "domain": domain.name,
                            "subdomain": subdomain.name,
                            "skill": skill.name,
                            "score": skill.score,
                            "level": skill.level
                        })
        
        return covered_skills
    
    def update_skill_scores(self, skill_scores: Dict[str, float], response_data: Dict[str, Any]):
        """Update skill scores based on response evaluation"""
        # Handle case where skill_scores might be a string representation
        if isinstance(skill_scores, str):
            try:
                import json
                skill_scores = json.loads(skill_scores)
            except (json.JSONDecodeError, TypeError):
                print(f"Warning: Could not parse skill_scores: {skill_scores}")
                return
        
        # Ensure skill_scores is a dictionary
        if not isinstance(skill_scores, dict):
            print(f"Warning: skill_scores is not a dictionary: {type(skill_scores)}")
            return
        
        # Track which skills were actually assessed in this response
        skills_assessed = []
        
        for skill_name, score in skill_scores.items():
            # Ensure score is a number
            try:
                score = float(score)
            except (ValueError, TypeError):
                print(f"Warning: Invalid score for {skill_name}: {score}")
                continue
                
            for domain in self.state.domains:
                for subdomain in domain.subdomains:
                    for skill in subdomain.core_skills:
                        if skill.name == skill_name:
                            # Add assessment history
                            assessment_record = {
                                "score": score,
                                "response_data": response_data,
                                "timestamp": response_data.get("timestamp")
                            }
                            skill.assessment_history.append(assessment_record)
                            
                            # Update score (can increase or decrease based on new evidence)
                            if skill.covered:
                                # If already covered, update based on new evidence
                                # Use weighted average: 70% previous score, 30% new score
                                skill.score = (skill.score * 0.7) + (score * 0.3)
                            else:
                                # First assessment
                                skill.score = score
                                skill.covered = True
                                self.state.covered_skills += 1
                            
                            skills_assessed.append(skill_name)
                            
                            # Mark subdomain and domain as covered if all skills are covered
                            self._update_coverage_status(domain, subdomain)
                            break
        
        # Update overall progress
        self.state.interview_progress = (self.state.covered_skills / self.state.total_skills) * 100
        
        print(f"Updated {len(skills_assessed)} skills: {skills_assessed}")
        print(f"Progress: {self.state.covered_skills}/{self.state.total_skills} skills covered ({self.state.interview_progress:.1f}%)")
    
    def _update_coverage_status(self, domain: Domain, subdomain: Subdomain):
        """Update coverage status for subdomains and domains"""
        # Check if all skills in subdomain are covered
        if all(skill.covered for skill in subdomain.core_skills):
            subdomain.covered = True
        
        # Check if all subdomains in domain are covered
        if all(sub.covered for sub in domain.subdomains):
            domain.covered = True
        
        # Update overall progress
        self.state.interview_progress = (self.state.covered_skills / self.state.total_skills) * 100
    
    def get_interview_progress(self) -> Dict[str, Any]:
        """Get current interview progress"""
        return {
            "progress_percentage": self.state.interview_progress,
            "covered_skills": self.state.covered_skills,
            "total_skills": self.state.total_skills,
            "domains_progress": [
                {
                    "name": domain.name,
                    "covered": domain.covered,
                    "subdomains_progress": [
                        {
                            "name": subdomain.name,
                            "covered": subdomain.covered,
                            "skills_progress": [
                                {
                                    "name": skill.name,
                                    "covered": skill.covered,
                                    "score": skill.score,
                                    "level": skill.level
                                }
                                for skill in subdomain.core_skills
                            ]
                        }
                        for subdomain in domain.subdomains
                    ]
                }
                for domain in self.state.domains
            ]
        }
    
    def add_user_response(self, response_data: Dict[str, Any]):
        """Add a user response to the state"""
        self.state.user_responses.append(response_data)
    
    def get_state(self) -> InterviewState:
        """Get the current state"""
        return self.state
    
    def export_results(self) -> Dict[str, Any]:
        """Export final interview results with hierarchical structure"""
        domain_scores = {}
        skill_scores = {}
        hierarchical_results = {}
        
        for domain in self.state.domains:
            domain_skill_scores = []
            domain_data = {
                "name": domain.name,
                "covered": domain.covered,
                "subdomains": {}
            }
            
            for subdomain in domain.subdomains:
                subdomain_skill_scores = []
                subdomain_data = {
                    "name": subdomain.name,
                    "covered": subdomain.covered,
                    "skills": {}
                }
                
                for skill in subdomain.core_skills:
                    domain_skill_scores.append(skill.score)
                    subdomain_skill_scores.append(skill.score)
                    skill_scores[skill.name] = skill.score
                    
                    # Add skill data to hierarchical structure
                    subdomain_data["skills"][skill.name] = {
                        "score": skill.score,
                        "covered": skill.covered,
                        "level": skill.level,
                        "assessment_history": [
                            {
                                "score": assessment["score"],
                                "timestamp": assessment["timestamp"]
                            }
                            for assessment in skill.assessment_history
                        ]
                    }
                
                # Calculate subdomain average score
                if subdomain_skill_scores:
                    subdomain_data["average_score"] = sum(subdomain_skill_scores) / len(subdomain_skill_scores)
                
                domain_data["subdomains"][subdomain.name] = subdomain_data
            
            # Calculate domain average score
            if domain_skill_scores:
                domain_scores[domain.name] = sum(domain_skill_scores) / len(domain_skill_scores)
                domain_data["average_score"] = domain_scores[domain.name]
            
            hierarchical_results[domain.name] = domain_data
        
        overall_score = sum(skill_scores.values()) / len(skill_scores) if skill_scores else 0
        
        return {
            "overall_score": overall_score,
            "interview_progress": self.state.interview_progress,
            "total_responses": len(self.state.user_responses),
            "completion_status": "Complete" if self.state.interview_complete else "In Progress",
            "hierarchical_results": hierarchical_results,
            # Keep flat structure for backward compatibility
            "domain_scores": domain_scores,
            "skill_scores": skill_scores
        }
    
    def convert_flat_scores_to_hierarchical(self, flat_scores: Dict[str, float]) -> Dict[str, Any]:
        """Convert flat skill scores to hierarchical structure"""
        hierarchical_scores = {}
        
        for domain in self.state.domains:
            domain_data = {
                "name": domain.name,
                "subdomains": {}
            }
            
            for subdomain in domain.subdomains:
                subdomain_data = {
                    "name": subdomain.name,
                    "skills": {}
                }
                
                for skill in subdomain.core_skills:
                    if skill.name in flat_scores:
                        subdomain_data["skills"][skill.name] = {
                            "score": flat_scores[skill.name],
                            "level": skill.level
                        }
                
                if subdomain_data["skills"]:
                    domain_data["subdomains"][subdomain.name] = subdomain_data
            
            if domain_data["subdomains"]:
                hierarchical_scores[domain.name] = domain_data
        
        return hierarchical_scores

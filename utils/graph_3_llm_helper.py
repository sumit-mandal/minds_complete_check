import os
from dotenv import load_dotenv
import json
from typing import Dict, Any, Optional, List

load_dotenv()
api_key = os.getenv("API_KEY")

from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=api_key
)

# LLM with lower temperature for evaluation tasks
evaluation_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.1,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=api_key
)

# Custom evaluation function that doesn't use structured output
def evaluate_response_with_llm(user_response: str, all_skills: list) -> dict:
    """Evaluate response using LLM without structured output to avoid parsing issues"""
    
    # Categorize skills into core and applied based on practical_applications
    core_skills = []
    applied_skills = []
    
    for skill in all_skills:
        # If skill has practical_applications, it's an applied skill
        # Otherwise, it's a core skill (understanding/self-awareness)
        if skill.get("practical_applications") and len(skill.get("practical_applications", [])) > 0:
            applied_skills.append(skill)
        else:
            core_skills.append(skill)
    
    # Build skill categorization info for the prompt
    skill_categories = {
        "core_skills": [{"name": s["name"], "knowledge_areas": s.get("knowledge_areas", [])} for s in core_skills],
        "applied_skills": [{"name": s["name"], "practical_applications": s.get("practical_applications", [])} for s in applied_skills]
    }
    
    evaluation_prompt = f"""You are a strict expert evaluator. Analyze the user's response and ONLY assign scores to skills that are CLEARLY demonstrated with appropriate evidence based on skill type.

User response: {user_response}

SKILL CATEGORIZATION:
Core Skills (understanding/self-awareness): {json.dumps(skill_categories["core_skills"], separators=(',', ':'))}
Applied Skills (real-world application): {json.dumps(skill_categories["applied_skills"], separators=(',', ':'))}

CRITICAL EVALUATION RULES BY SKILL TYPE:

1. CORE SKILLS (Understanding & Self-Awareness):
   - Evaluate: Understanding of the skill definition and self-awareness/confidence of the skill within themselves
   - Evidence Required: Must demonstrate understanding of what the skill means AND awareness of how it applies to themselves
   - Examples of valid evidence: "I understand that [skill] means...", "I recognize that I have/need [skill] because...", clear self-reflection about the skill
   - Generic statements like "I work with teams" do NOT demonstrate core skill understanding
   - Scoring: 0-3 if no understanding/awareness shown, 4-7 if basic understanding, 8-10 if clear self-awareness

2. APPLIED SKILLS (Real-World Application):
   - Evaluate: Understanding of how they would or have applied the skill in real-world situations with examples and impact
   - Evidence Required: MUST have SPECIFIC examples, concrete actions, or detailed descriptions of application
   - Examples of valid evidence: Specific situations, concrete actions taken, outcomes/impact described
   - Generic statements (e.g., "I work with teams", "I solve problems") do NOT demonstrate applied skills
   - Scoring: 0-3 if no examples, 4-7 if basic example provided, 8-10 if detailed example with impact

3. SKILL SELECTION RULES:
   - ONLY score "applied" skills that are EXPLICITLY demonstrated with concrete evidence (specific examples)
   - Do NOT score core and applied skills based on assumptions or vague connections
   - Be conservative: when in doubt, do NOT score the skill
   - If a response is too vague to evaluate most skills, only score 1-3 skills at most

4. RESPONSE QUALITY ASSESSMENT:
   - Short, vague responses (< 20 words) should typically score 0-3 for most skills
   - Responses without specific examples (for applied skills) or self-awareness (for core skills) should score 0-3
   - Generic statements about teamwork, problem-solving, etc. should score 0-3

5. SCORING SCALE (0-10):
   - 0-2: No demonstration or only vague/generic mention with no evidence
   - 2-3: Weak or tangential mention, no concrete examples/awareness
   - 3-5: Basic demonstration with minimal evidence
   - 5-7: Clear demonstration with specific examples (applied) or self-awareness (core)
   - 7-9: Strong demonstration with detailed examples and clear evidence
   - 9-10: Excellent demonstration with multiple specific examples and strong evidence

6. DECIMAL SCORING:
   - Use decimal scores (e.g., 1.8, 2.1, 3.4, 7.3, 8.5) NOT whole numbers
   - Avoid scores like 5.0, 6.0 - use 4.8, 5.2, 6.3 instead

IMPORTANT: For vague responses like "working with interesting people as we solve those roles together as a team", this is a generic statement with no concrete evidence. Most skills should receive scores of 0-3, and only 1-3 skills at most should be scored if there's any minimal evidence.

Return ONLY a JSON object with skill names as keys and numeric scores as values. Do not include any other text, just the JSON object."""

    try:
        response = evaluation_llm.invoke(evaluation_prompt)
        response_text = response.content.strip()
        
        # Try to extract JSON from the response
        if response_text.startswith('{') and response_text.endswith('}'):
            skill_scores = json.loads(response_text)
        else:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                skill_scores = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")
        
        return {
            "skill_scores": skill_scores,
            "confidence_level": 0.8,
            "reasoning": "LLM evaluation completed successfully",
            "follow_up_needed": False,
            "skills_covered": list(skill_scores.keys())
        }
        
    except Exception as e:
        print(f"LLM evaluation failed: {e}")
        raise e


def generate_domain_summary(hierarchical_results: Dict[str, Any], domain_scores: Dict[str, float], 
                            conversation_summary: Optional[Dict[str, Any]] = None,
                            name: Optional[str] = None, pronoun: Optional[str] = None,
                            career_level: Optional[str] = None, industry: Optional[str] = None,
                            persona: Optional[str] = None) -> Dict[str, Any]:
    """Generate a comprehensive summary of all domains covered in the interview"""
    
    # Build personalization context
    personalization_context = ""
    if name:
        personalization_context += f"Candidate: {name}. "
    if pronoun:
        personalization_context += f"Use '{pronoun}' pronouns. "
    if career_level:
        personalization_context += f"Level: {career_level}. "
    if industry:
        personalization_context += f"Industry: {industry}. "
    if persona:
        personalization_context += f"Persona: {persona}."
    
    # Prepare simplified domain data - only essential info to reduce token usage
    domain_data_list = []
    for domain_name, domain_data in hierarchical_results.items():
        if isinstance(domain_data, dict):
            domain_score = domain_data.get("average_score", domain_scores.get(domain_name, 0.0))
            
            # Only include top subdomains (max 3 per domain) to reduce data size
            subdomains = domain_data.get("subdomains", {})
            subdomain_list = []
            for subdomain_name, subdomain_data in subdomains.items():
                if isinstance(subdomain_data, dict):
                    subdomain_list.append({
                        "name": subdomain_name,
                        "score": round(subdomain_data.get("average_score", 0.0), 1)
                    })
            
            # Sort by score and take top 3
            subdomain_list.sort(key=lambda x: x["score"], reverse=True)
            top_subdomains = subdomain_list[:3]
            
            domain_info = {
                "domain": domain_name,
                "score": round(domain_score, 1),
                "subdomains": top_subdomains
            }
            domain_data_list.append(domain_info)
    
    # Simplify conversation summary - only extract key points if it's too large
    conversation_text = ""
    if conversation_summary:
        if isinstance(conversation_summary, dict):
            # Extract only key fields, limit text length
            key_points = []
            for key in ["overall_assessment", "key_strengths", "communication_style"]:
                if key in conversation_summary:
                    value = conversation_summary[key]
                    if isinstance(value, str):
                        # Truncate long text
                        if len(value) > 500:
                            value = value[:500] + "..."
                        key_points.append(f"{key}: {value}")
            conversation_text = " | ".join(key_points) if key_points else "Available"
        else:
            # If it's a string, truncate it
            conv_str = str(conversation_summary)
            conversation_text = conv_str[:500] + "..." if len(conv_str) > 500 else conv_str
    
    # Build concise prompt
    domain_summary_prompt = f"""Analyze interview domains and create a summary.

Context: {personalization_context}

Domains (score 0-10): {json.dumps(domain_data_list, separators=(',', ':'))}

Key conversation points: {conversation_text if conversation_text else "Not available"}

Create a JSON summary with:
{{
    "overall_domain_analysis": "Brief overview of performance across domains",
    "domains": [
        {{
            "domain_name": "Domain Name",
            "average_score": 7.5,
            "strengths": ["strength1", "strength2"],
            "areas_for_improvement": ["area1", "area2"],
            "key_insights": "Brief insights",
            "recommendations": ["rec1", "rec2"],
            "subdomain_breakdown": [
                {{"subdomain_name": "Subdomain", "average_score": 8.0, "key_findings": "Brief findings"}}
            ]
        }}
    ],
    "cross_domain_patterns": "Brief pattern analysis",
    "top_performing_domains": ["domain1", "domain2"],
    "domains_needing_attention": ["domain1"],
    "overall_recommendations": "Brief recommendations"
}}

Return ONLY valid JSON."""

    try:
        # Use max_tokens to limit response size and improve speed
        response = evaluation_llm.invoke(domain_summary_prompt)
        response_text = response.content.strip()
        
        # Try to extract JSON from the response
        if response_text.startswith('{') and response_text.endswith('}'):
            summary_data = json.loads(response_text)
        else:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                summary_data = json.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")
        
        return summary_data
        
    except Exception as e:
        print(f"Error generating domain summary: {e}")
        # Return a basic structure if generation fails
        return {
            "overall_domain_analysis": f"Error generating domain summary: {str(e)}",
            "domains": [],
            "cross_domain_patterns": "",
            "top_performing_domains": [],
            "domains_needing_attention": [],
            "overall_recommendations": ""
        }


def _normalize_domain_name(name: str) -> str:
    """Normalize domain name for comparison (case-insensitive, strip whitespace)"""
    return name.strip().lower()


def _find_domain_index(domains: List[Dict[str, Any]], domain_name: str) -> int:
    """Find index of domain by normalized name, returns -1 if not found"""
    normalized_target = _normalize_domain_name(domain_name)
    for i, domain in enumerate(domains):
        if _normalize_domain_name(domain.get("domain_name", "")) == normalized_target:
            return i
    return -1


def organize_domains_by_cog(domain_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Organize domains in the summary by COG relationships.
    Groups related domains together based on persona trait pairs.
    """
    if "domains" not in domain_summary or not isinstance(domain_summary["domains"], list):
        return domain_summary
    
    domains = domain_summary["domains"].copy()
    if not domains:
        return domain_summary
    
    # Define COG relationships as pairs (from PERSONA_DEFINITIONS)
    cog_pairs = [
        ("Empathy", "Relationships"),
        ("Confidence", "Leadership"),
        ("Security", "Stability"),
        ("Adaptability", "Creativity"),
        ("Communication", "Expression"),
        ("Strategic Thinking", "Insight"),
        ("Alignment", "Purpose"),
    ]
    
    # Track which domains have been placed
    placed_indices = set()
    organized_domains = []
    
    # Process each COG pair
    for domain1_name, domain2_name in cog_pairs:
        idx1 = _find_domain_index(domains, domain1_name)
        idx2 = _find_domain_index(domains, domain2_name)
        
        # Add first domain if found and not already placed
        if idx1 != -1 and idx1 not in placed_indices:
            organized_domains.append(domains[idx1])
            placed_indices.add(idx1)
        
        # Add second domain if found and not already placed
        if idx2 != -1 and idx2 not in placed_indices:
            organized_domains.append(domains[idx2])
            placed_indices.add(idx2)
    
    # Add remaining domains that weren't part of any COG pair
    for i, domain in enumerate(domains):
        if i not in placed_indices:
            organized_domains.append(domain)
    
    # Update the domain summary with organized domains
    domain_summary["domains"] = organized_domains
    return domain_summary



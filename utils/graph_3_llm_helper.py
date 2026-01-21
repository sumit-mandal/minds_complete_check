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

# Domain-based categorization for core vs applied skills
APPLIED_DOMAINS = {"Alignment", "Strategic Thinking", "Communication", "Leadership", "Relationship", "Relationships", "Stability", "Adaptability"}
CORE_DOMAINS = {"Purpose", "Insights", "Insight", "Expression", "Confidence", "Creativity", "Security"}

def _normalize_domain_for_categorization(domain_name: str) -> str:
    """Normalize domain name for categorization comparison"""
    return domain_name.strip().lower()

def _is_applied_domain(domain_name: str) -> bool:
    """Check if a domain is an applied domain"""
    normalized = _normalize_domain_for_categorization(domain_name)
    return any(_normalize_domain_for_categorization(applied) == normalized for applied in APPLIED_DOMAINS)

def _is_core_domain(domain_name: str) -> bool:
    """Check if a domain is a core domain"""
    normalized = _normalize_domain_for_categorization(domain_name)
    return any(_normalize_domain_for_categorization(core) == normalized for core in CORE_DOMAINS)

# Custom evaluation function that doesn't use structured output
def evaluate_response_with_llm(user_response: str, all_skills: list) -> dict:
    """Evaluate response using LLM without structured output to avoid parsing issues"""
    
    # Categorize skills into core and applied based on domain name
    core_skills = []
    applied_skills = []
    
    for skill in all_skills:
        domain_name = skill.get("domain", "")
        if _is_applied_domain(domain_name):
            applied_skills.append(skill)
        elif _is_core_domain(domain_name):
            core_skills.append(skill)
        else:
            # Fallback: if domain not recognized, use practical_applications as before
            if skill.get("practical_applications") and len(skill.get("practical_applications", [])) > 0:
                applied_skills.append(skill)
            else:
                core_skills.append(skill)
    
    # Build skill categorization info for the prompt
    skill_categories = {
        "core_skills": [{"name": s["name"], "knowledge_areas": s.get("knowledge_areas", [])} for s in core_skills],
        "applied_skills": [{"name": s["name"], "practical_applications": s.get("practical_applications", [])} for s in applied_skills]
    }
    
    evaluation_prompt = f"""You are a balanced and fair evaluator. Analyze the user's response and assign scores to skills that are demonstrated with reasonable evidence. Be encouraging but maintain evaluation integrity - recognize genuine demonstrations while ensuring the interview provides meaningful assessment.

User response: {user_response}

SKILL CATEGORIZATION:
Core Skills: {json.dumps(skill_categories["core_skills"], separators=(',', ':'))}
Applied Skills: {json.dumps(skill_categories["applied_skills"], separators=(',', ':'))}

DEFINITIONS:

1. CORE SKILLS - A foundational talent/gift that exists within all individuals that may or may not be visible to others. The strength of the foundational core skill varies by individual based on their level of awareness and subsequent development of the talent, as they may or may not be aware that this innate talent exists within themselves.
   - Evaluate: Look for signs of awareness, understanding, or recognition of the foundational talent
   - Evidence can be: Direct statements, implied understanding, indirect references, contextual clues, or responses suggesting familiarity with the concept
   - Scoring approach: Recognize genuine awareness or understanding, even if not fully developed

2. APPLIED SKILLS - This is how the skill is applied or "shows up" in real work through interactions, situations, the environment, and/or opportunity.
   - Evaluate: Look for how the skill manifests in real-world contexts
   - Evidence can be: Specific examples, general scenarios, implied applications, descriptions suggesting practical experience, or contextual indicators
   - Scoring approach: Recognize real-world manifestations, even if not exhaustively detailed

EVALUATION GUIDELINES:

1. BALANCED EVALUATION:
   - Look for reasonable connections between the response and the skills
   - Recognize partial demonstrations and implied understanding when there's genuine evidence
   - Give credit for intent and underlying understanding, but ensure there's actual evidence
   - Be encouraging but maintain evaluation standards - don't inflate scores unnecessarily

2. SKILL SELECTION:
   - Score skills that are demonstrated with reasonable evidence (explicit or implicit)
   - Look for indirect indicators and contextual clues that suggest genuine demonstration
   - When there's reasonable evidence, score the skill appropriately
   - Don't score skills based on very weak or purely speculative connections

3. RESPONSE QUALITY ASSESSMENT:
   - Short responses can demonstrate skills if they contain relevant and meaningful information
   - Responses without explicit examples can still score if they show genuine understanding or implied experience
   - Generic statements can demonstrate skills if they're contextually relevant and show understanding
   - Look for genuine intent and underlying understanding, not just surface-level mentions

4. SCORING SCALE (0-10) - Balanced ranges:
   - 0-2: No demonstration or completely irrelevant
   - 2-3: Very minimal or tangential demonstration, weak connection
   - 3-5: Basic demonstration with some evidence (explicit or implicit)
   - 5-7: Clear demonstration with reasonable evidence or examples
   - 7-8: Strong demonstration with good evidence
   - 8-10: Excellent demonstration with multiple examples or very strong evidence

5. DECIMAL SCORING:
   - Use decimal scores (e.g., 1.8, 2.1, 3.4, 7.3, 8.5) NOT whole numbers
   - Avoid scores like 5.0, 6.0 - use 4.8, 5.2, 6.3 instead

IMPORTANT: Be balanced in your evaluation. Recognize genuine strengths and demonstrations while maintaining evaluation integrity. Look for reasonable connections between the response and the skills. Give credit for partial demonstrations and implied understanding when there's actual evidence, but don't inflate scores unnecessarily. The goal is to provide meaningful assessment that encourages growth while maintaining standards.

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
    
    # Prepare domain data with skill details
    domain_data_list = []
    for domain_name, domain_data in hierarchical_results.items():
        if isinstance(domain_data, dict):
            domain_score = domain_data.get("average_score", domain_scores.get(domain_name, 0.0))
            
            subdomains = domain_data.get("subdomains", {})
            subdomain_list = []
            for subdomain_name, subdomain_data in subdomains.items():
                if isinstance(subdomain_data, dict):
                    skills_data = []
                    skills = subdomain_data.get("skills", {})
                    for skill_name, skill_info in skills.items():
                        if isinstance(skill_info, dict):
                            skills_data.append({
                                "name": skill_name,
                                "score": round(skill_info.get("score", 0.0), 1),
                                "level": skill_info.get("level", "Medium"),
                                "covered": skill_info.get("covered", False)
                            })
                    
                    subdomain_list.append({
                        "name": subdomain_name,
                        "score": round(subdomain_data.get("average_score", 0.0), 1),
                        "skills": skills_data
                    })
            
            # Sort by score and take top 3 subdomains
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
    
    # Build prompt with skill details requirement
    domain_summary_prompt = f"""Analyze interview domains and create a comprehensive summary with detailed skill-level insights.

Context: {personalization_context}

Domains with skill details (score 0-10): {json.dumps(domain_data_list, separators=(',', ':'))}

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
                {{
                    "subdomain_name": "Subdomain",
                    "average_score": 8.0,
                    "key_findings": "Brief findings about the subdomain",
                    "skills": [
                        {{
                            "skill_name": "Skill Name",
                            "score": 7.5,
                            "analysis": "Write 3-4 sentences providing detailed analysis of this specific skill. Describe the candidate's performance naturally without mentioning the numeric score. Include: how the candidate demonstrated this skill during the interview, specific examples or patterns observed, strengths or areas for improvement related to this skill, and how this skill contributes to their overall profile. Make it informative, specific, and written in natural conversational language - avoid generic statements and never explicitly state the score."
                        }}
                    ]
                }}
            ]
        }}
    ],
    "cross_domain_patterns": "Brief pattern analysis",
    "top_performing_domains": ["domain1", "domain2"],
    "domains_needing_attention": ["domain1"],
    "overall_recommendations": "Brief recommendations"
}}

IMPORTANT: For each skill in the subdomain breakdown, provide a detailed "analysis" field with 3-4 sentences that:
- Describes the candidate's performance and demonstration of this specific skill in natural, conversational language
- NEVER explicitly mention the numeric score (e.g., avoid phrases like "A score of X indicates" or "With a score of X")
- Instead, use natural language to describe performance level (e.g., "shows strong understanding", "demonstrates solid grasp", "needs development in")
- Mentions specific examples, patterns, or observations related to this skill from the interview
- Highlights strengths or areas for improvement specific to this skill
- Connects how this skill contributes to their overall profile

Make each skill analysis informative, specific, and meaningful - write as if you're providing feedback to the candidate, not reporting scores. Use natural language that flows conversationally.

CRITICAL JSON FORMATTING REQUIREMENTS:
- Return ONLY valid JSON, no markdown code blocks, no extra text
- Escape all quotes within strings using backslash (e.g., "He said \"hello\"")
- Ensure all strings are properly quoted
- Use double quotes for JSON keys and string values
- Ensure proper comma placement between array elements and object properties
- Do not include trailing commas

Return ONLY valid JSON."""

    try:
        response = evaluation_llm.invoke(domain_summary_prompt)
        response_text = response.content.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            response_text = '\n'.join(lines).strip()
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
        
        # Try to extract JSON from the response
        summary_data = None
        if response_text.startswith('{') and response_text.endswith('}'):
            try:
                summary_data = json.loads(response_text)
            except json.JSONDecodeError:
                pass
        
        if summary_data is None:
            # Try to find JSON in the response using balanced braces
            import re
            brace_count = 0
            start_idx = -1
            for i, char in enumerate(response_text):
                if char == '{':
                    if start_idx == -1:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        json_text = response_text[start_idx:i+1]
                        try:
                            summary_data = json.loads(json_text)
                            break
                        except json.JSONDecodeError:
                            start_idx = -1
                            brace_count = 0
        
        if summary_data is None:
            # Fallback: try regex
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group()
                summary_data = json.loads(json_text)
            else:
                raise ValueError("No valid JSON found in response")
        
        return summary_data
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in domain summary: {e}")
        print(f"Response text (first 500 chars): {response_text[:500] if 'response_text' in locals() else 'N/A'}")
        raise ValueError(f"Invalid JSON format in domain summary response: {str(e)}")
    except Exception as e:
        print(f"Error generating domain summary: {e}")
        raise e


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



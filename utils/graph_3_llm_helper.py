import os
from dotenv import load_dotenv
import json
from typing import Dict, Any, Optional

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
    
    evaluation_prompt = f"""You are an expert evaluator. Analyze the user's response and assign scores to ALL skills that are demonstrated or mentioned in the response.

Available skills to evaluate: {json.dumps(all_skills, indent=2)}
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
9. Only score skills that are actually demonstrated or mentioned in the response
10. If a skill is not mentioned or demonstrated, don't include it in the scores

- Return ONLY a JSON object with skill names as keys and numeric scores as values
- Use decimal scores (e.g., 1.8, 2.1, 7.3, 8.5) NOT whole numbers (avoid 1.0, 2.0, 7.0, 8.0)
- Provide precise decimal scores to reflect nuanced assessment
Example: {{"Clarity of Thought": 7.3, "Problem-Solving Confidence": 8.2, "Technical Knowledge": 6.7}}

Do not include any other text, just the JSON object."""

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
        personalization_context += f"\nCandidate Name: {name}\n"
    if pronoun:
        personalization_context += f"Use the pronoun '{pronoun}' when referring to the candidate.\n"
    if career_level:
        personalization_context += f"Career Level: {career_level}\n"
    if industry:
        personalization_context += f"Industry: {industry}\n"
    if persona:
        personalization_context += f"Interview Persona: {persona}\n"
    
    # Prepare domain data for the prompt
    domain_data_list = []
    for domain_name, domain_data in hierarchical_results.items():
        if isinstance(domain_data, dict):
            domain_info = {
                "domain_name": domain_name,
                "average_score": domain_data.get("average_score", domain_scores.get(domain_name, 0.0)),
                "covered": domain_data.get("covered", False),
                "subdomains": {}
            }
            
            # Extract subdomain information
            subdomains = domain_data.get("subdomains", {})
            for subdomain_name, subdomain_data in subdomains.items():
                if isinstance(subdomain_data, dict):
                    subdomain_info = {
                        "subdomain_name": subdomain_name,
                        "average_score": subdomain_data.get("average_score", 0.0),
                        "covered": subdomain_data.get("covered", False),
                        "skills": {}
                    }
                    
                    # Extract skill information
                    skills = subdomain_data.get("skills", {})
                    for skill_name, skill_data in skills.items():
                        if isinstance(skill_data, dict):
                            subdomain_info["skills"][skill_name] = {
                                "score": skill_data.get("score", 0.0),
                                "covered": skill_data.get("covered", False),
                                "level": skill_data.get("level", "Medium")
                            }
                    
                    domain_info["subdomains"][subdomain_name] = subdomain_info
            
            domain_data_list.append(domain_info)
    
    # Build the prompt
    domain_summary_prompt = f"""You are an expert interview analyst. Analyze all the domains covered in this interview and create a comprehensive summary.

{personalization_context}

Domain Data: {json.dumps(domain_data_list, indent=2, default=str)}

Conversation Summary (if available): {json.dumps(conversation_summary, indent=2, default=str) if conversation_summary else "Not available"}

Your task is to create a detailed summary that:
1. Provides an overview of all domains covered in the interview
2. Highlights the candidate's strengths in each domain
3. Identifies areas for improvement in each domain
4. Provides specific insights about their performance across different domains
5. Compares performance across domains to identify patterns
6. Gives actionable recommendations for each domain
7. Makes it personal and meaningful, addressing {name if name else 'the candidate'} directly
8. Uses {pronoun if pronoun else 'their'} pronouns appropriately

Return a JSON object with the following structure:
{{
    "overall_domain_analysis": "A comprehensive overview of how the candidate performed across all domains",
    "domains": [
        {{
            "domain_name": "Domain Name",
            "average_score": 7.5,
            "strengths": ["List of strengths in this domain"],
            "areas_for_improvement": ["List of areas that need work"],
            "key_insights": "Detailed insights about performance in this domain",
            "recommendations": ["Specific actionable recommendations"],
            "subdomain_breakdown": [
                {{
                    "subdomain_name": "Subdomain Name",
                    "average_score": 8.0,
                    "key_findings": "Insights about this subdomain"
                }}
            ]
        }}
    ],
    "cross_domain_patterns": "Analysis of patterns across different domains",
    "top_performing_domains": ["List of top 2-3 domains"],
    "domains_needing_attention": ["List of domains that need improvement"],
    "overall_recommendations": "High-level recommendations based on all domains"
}}

Return ONLY valid JSON, no other text."""

    try:
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



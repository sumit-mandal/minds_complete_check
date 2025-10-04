import os
from utils.state_manager import Question, InterviewSummary
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv("API_KEY")

from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.7,  # Slightly higher for more creative question generation
    max_tokens=None,
    timeout=None,
    max_retries=2,
    google_api_key=api_key
)

# Specialized LLM instances for different tasks
question_generator_llm = llm.with_structured_output(Question)
summarizer_llm = llm.with_structured_output(InterviewSummary)

# LLM with lower temperature for evaluation tasks
evaluation_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.1,  # Lower temperature for more consistent evaluations
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

IMPORTANT: Return ONLY a JSON object with skill names as keys and numeric scores as values.
Example: {{"Clarity of Thought": 7.5, "Problem-Solving Confidence": 8.0}}

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



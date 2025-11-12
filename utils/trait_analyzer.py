#!/usr/bin/env python3
"""
Persona Ranking Utility

Generates a personalized report ranking different personas based on domain scores
from hierarchical_results. Identifies primary and secondary traits.
"""

# IMMEDIATE TEST - This should print immediately
print("SCRIPT LOADED - trait_analyzer.py is running!")
from re import S
import re
import sys
from utils.graph_3_llm_helper import llm
sys.stdout.flush()

import json
from typing import Dict, Any, List, Optional


class PersonaRankingGenerator:
    """Generates persona rankings from hierarchical results"""
    
    PERSONA_DEFINITIONS = [
        {
            "code": "S-S",
            "name": "The Stabilizer",
            "trait_1": "Security",
            "trait_2": "Stability",
            "full_name": "The Stabilizer (S–S)"
        },
        {
            "code": "C-L",
            "name": "The Direction-Setter",
            "trait_1": "Confidence",
            "trait_2": "Leadership",
            "full_name": "The Direction-Setter (C–L)"
        },
        {
            "code": "C-A",
            "name": "The Adaptive Innovator",
            "trait_1": "Creativity",
            "trait_2": "Adaptability",
            "full_name": "The Adaptive Innovator (C–A)"
        },
        {
            "code": "E-C",
            "name": "The Communicator",
            "trait_1": "Expression",
            "trait_2": "Communication",
            "full_name": "The Communicator (E–C)"
        },
        {
            "code": "E-R",
            "name": "The Culture Builder",
            "trait_1": "Empathy",
            "trait_2": "Relationships",
            "full_name": "The Culture Builder (E–R)"
        },
        {
            "code": "I-S",
            "name": "The Strategist",
            "trait_1": "Insight",
            "trait_2": "Strategic Thinking",
            "full_name": "The Strategist (I–S)"
        },
        {
            "code": "P-A",
            "name": "The Purpose Integrator",
            "trait_1": "Purpose",
            "trait_2": "Alignment",
            "full_name": "The Purpose Integrator (P–A)"
        },
    ]
    
    def _parse_hierarchical_results(self, hierarchical_results: Any) -> Dict[str, Any]:
        """
        Parse hierarchical_results from string or dict format
        
        Args:
            hierarchical_results: Can be JSON string or dict
            
        Returns:
            Parsed hierarchical results as dict
        """
        if isinstance(hierarchical_results, str):
            return json.loads(hierarchical_results)
        elif isinstance(hierarchical_results, dict):
            return hierarchical_results
        else:
            raise ValueError(f"hierarchical_results must be str or dict, got {type(hierarchical_results)}")
    
    def _extract_domain_scores(self, hierarchical_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract average scores for each domain from hierarchical_results
        
        Args:
            hierarchical_results: Parsed hierarchical results dict
            
        Returns:
            Dictionary mapping domain names to their average scores
        """
        domain_scores = {}
        
        for domain_name, domain_data in hierarchical_results.items():
            if isinstance(domain_data, dict) and "average_score" in domain_data:
                domain_scores[domain_name] = domain_data["average_score"]
                print(f"Domain: {domain_name}, Score: {domain_data['average_score']}")
        
        return domain_scores

    def calcuate_persona_scores(self,persona_def: Dict[str,str],domain_scores:Dict[str,float]) -> Optional[Dict[str,Any]]:
        trait_1_score = domain_scores.get(persona_def["trait_1"]) 
        trait_2_score = domain_scores.get(persona_def["trait_2"])

        if trait_1_score is None or trait_2_score is None: 
            return None 

        persona_score = (trait_1_score + trait_2_score) / 2  
        print(f"Persona: {persona_def['name']}, Score: {persona_score:.2f}")
        return { 
        "persona": persona_def,
        "score":persona_score,
        "trait_1_score":trait_1_score,
        "trait_2_score":trait_2_score,
        "rank":0,
        "category":""
        }

    def rank_personas(self,persona_rankings: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
        sorted_ranking = sorted(persona_rankings, key=lambda x: x["score"],reverse=True)
        for rank,persona_ranking in enumerate(sorted_ranking,start=1):
            persona_ranking["rank"] = rank
            print(f"Ranked Persona: {persona_ranking['persona']['name']}, Score: {persona_ranking['score']:.2f}, Rank: {rank}")
        return sorted_ranking
        
    def categorize_personas(self,ranked_personas:List[Dict[str,Any]]) -> List[Dict[str,Any]]: 
        if not ranked_personas:
            return ranked_personas

        for idx,persona_ranking in enumerate(ranked_personas):
            if idx == 0:
                persona_ranking["category"] = "Primary"
            elif idx == 1:
                persona_ranking["category"] = "Secondary"
            else:
                persona_ranking["category"] = "Tertiary"

        return ranked_personas

    def _generate_persona_description(self,persona:Dict[str,Any], conversation_summary: Dict[str,Any]) -> str:

        summary_fields = {
            "key_strengths": conversation_summary.get("key_strengths"),
            "areas_for_improvement": conversation_summary.get("areas_for_improvement"),
            "communication_style": conversation_summary.get("communication_style"),
            "problem_solving_approach": conversation_summary.get("problem_solving_approach"),
            "emotional_intelligence": conversation_summary.get("emotional_intelligence"),
            "professional_maturity": conversation_summary.get("professional_maturity"),
            "specific_examples": conversation_summary.get("specific_examples"),

        }

        prompt = f"""Generate a personalized description of what it means for this person to have the persona "{persona['persona']['full_name']}" based on their interview responses. 
        
        Persona: {persona['persona']['full_name']} 
        Traits: {persona['persona']['trait_1']} and {persona['persona']['trait_2']}
        Score: {persona['score']:.1f} 

        Interview Insights:
        - Key Strengths: {summary_fields['key_strengths']}
        - Areas for Improvement: {summary_fields['areas_for_improvement']}
        - Communication Style: {summary_fields['communication_style']}
        - Problem Solving Approach: {summary_fields['problem_solving_approach']}
        - Emotional Intelligence: {summary_fields['emotional_intelligence']}
        - Professional Maturity: {summary_fields['professional_maturity']}
        - Specific Examples: {summary_fields['specific_examples']}

        Write a personalized 2-3 sentence description explaining what this persona means for this specific individual based on their interview responses. Be specific and reference their actual traits and examples. Return only the description text, no JSON or formatting.
        
        """ 

        response = llm.invoke(prompt) 
        return response.content.strip()
    
    def generate_report(self,hierarchical_results:Any, conversation_summary:Optional [Dict[str,Any]]=None) :
        parsed_results = self._parse_hierarchical_results(hierarchical_results) 
        domain_scores = self._extract_domain_scores(parsed_results) 
        persona_rankings = [] 

        for persona_def in self.PERSONA_DEFINITIONS: 
            ranking = self.calcuate_persona_scores(persona_def,domain_scores) 
            if ranking:
                persona_rankings.append(ranking)

        ranked_personas = self.rank_personas(persona_rankings)
        categorized_personas = self.categorize_personas(ranked_personas)

        primary_trait = categorized_personas[0] if categorized_personas else None 
        secondary_traits = categorized_personas[1:3] if len(categorized_personas) > 1 else [] 


        primary_decription = None  
        secondary_descriptions = [] 

        if conversation_summary and primary_trait: 
            primary_description = self._generate_persona_description(primary_trait, conversation_summary)

        if conversation_summary and secondary_traits: 
            for st in secondary_traits:
                description = self._generate_persona_description(st, conversation_summary)
                secondary_descriptions.append(description)



        return {
            "ranked_personas": [
                {
                    "persona_code": p["persona"]["code"],
                    "persona_name": p["persona"]["full_name"],
                    "score": round(p["score"], 1),
                    "trait_1": {
                        "name": p["persona"]["trait_1"],
                        "score": round(p["trait_1_score"], 1)
                    },
                    "trait_2": {
                        "name": p["persona"]["trait_2"],
                        "score": round(p["trait_2_score"], 1)
                    },
                    "rank": p["rank"],
                    "category": p["category"]
                }
                for p in categorized_personas
            ],
            "primary_trait": {
                "persona_code": primary_trait["persona"]["code"],
                "persona_name": primary_trait["persona"]["full_name"],
                "score": round(primary_trait["score"], 1),
                "trait_1": {
                    "name": primary_trait["persona"]["trait_1"],
                    "score": round(primary_trait["trait_1_score"], 1)
                },
                "trait_2": {
                    "name": primary_trait["persona"]["trait_2"],
                    "score": round(primary_trait["trait_2_score"], 1)
                },
                "description": primary_description
            } if primary_trait else None,
            "secondary_traits": [
                {
                    "persona_code": st["persona"]["code"],
                    "persona_name": st["persona"]["full_name"],
                    "score": round(st["score"], 1),
                    "trait_1": {
                        "name": st["persona"]["trait_1"],
                        "score": round(st["trait_1_score"], 1)
                    },
                    "trait_2": {
                        "name": st["persona"]["trait_2"],
                        "score": round(st["trait_2_score"], 1)
                    },
                    "description": secondary_descriptions[i] if i < len(secondary_descriptions) else None
                }
                for i, st in enumerate(secondary_traits)
            ],
            "domain_scores": {
                domain: round(score, 1)
                for domain, score in domain_scores.items()
            }
        }



def generate_persona_report(hierarchical_results: Any, conversation_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    generator = PersonaRankingGenerator()
    return generator.generate_report(hierarchical_results, conversation_summary)







# # Simple test section
# if __name__ == "__main__":
#     import sys
#     from pathlib import Path
    
#     # Get session_id from command line
#     if len(sys.argv) < 2:
#         print("Usage: python utils/trait_analyzer.py <session_id>")
#         sys.exit(1)
    
#     session_id = sys.argv[1]
#     print(f"Session ID: {session_id}")
    
#     # Import database
#     sys.path.insert(0, str(Path(__file__).parent.parent))
#     from utils.database import InterviewDatabase
    
#     # Get data
#     db = InterviewDatabase()
#     session_data = db.get_session_data(session_id)
    
#     if not session_data:
#         print(f"Session {session_id} not found")
#         sys.exit(1)
    
#     # Get hierarchical_results
#     final_results = session_data.get("final_results", {})
#     hierarchical_results_raw = final_results.get("hierarchical_results")
    
#     if not hierarchical_results_raw:
#         print("No hierarchical_results found")
#         sys.exit(1)
    
#     # Parse and extract
#     generator = PersonaRankingGenerator()
#     hierarchical_results = generator._parse_hierarchical_results(hierarchical_results_raw)
#     # domain_scores = generator._extract_domain_scores(hierarchical_results)
#     # calcuate_persona_scores = generator.calcuate_persona_scores(generator.PERSONA_DEFINITIONS[0],domain_scores)
#     # ranked_personas = generator.rank_personas([calcuate_persona_scores])
#     # categorized_personas = generator.categorize_personas(ranked_personas)
#     report = generator.generate_report(hierarchical_results)
#     print(report)
  
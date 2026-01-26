#!/usr/bin/env python3
"""
Persona Ranking Utility

Generates a personalized report ranking different personas based on domain scores
from hierarchical_results using weighted COG groups.
"""

print("SCRIPT LOADED - trait_analyzer.py is running!")
import re
import sys
from utils.graph_3_llm_helper import llm
sys.stdout.flush()

import json
from typing import Dict, Any, List, Optional


class PersonaRankingGenerator:
    """Generates persona rankings from hierarchical results using weighted COG groups"""
    
    PERSONA_MODEL = {
        "S-S": {
            "highest": ["Security", "Stability"],
            "supporting": ["Expression", "Relationships", "Purpose", "Alignment"],
            "mid": ["Insight", "Communication"],
            "stretch": ["Confidence", "Leadership"]
        },
        "C-L": {
            "highest": ["Confidence", "Leadership"],
            "supporting": ["Purpose", "Alignment", "Insight"],
            "mid": ["Creativity", "Communication"],
            "stretch": ["Security", "Empathy"]
        },
        "C-A": {
            "highest": ["Creativity", "Adaptability"],
            "supporting": ["Insight", "Communication"],
            "mid": ["Confidence", "Purpose"],
            "stretch": ["Security", "Relationships"]
        },
        "E-C": {
            "highest": ["Expression", "Communication"],
            "supporting": ["Purpose", "Empathy"],
            "mid": ["Insight", "Creativity"],
            "stretch": ["Security", "Leadership"]
        },
        "E-R": {
            "highest": ["Empathy", "Relationships"],
            "supporting": ["Security", "Communication"],
            "mid": ["Purpose", "Insight"],
            "stretch": ["Confidence", "Creativity"]
        },
        "I-S": {
            "highest": ["Insight", "Strategic Thinking"],
            "supporting": ["Purpose", "Creativity"],
            "mid": ["Expression", "Security"],
            "stretch": ["Empathy", "Leadership"]
        },
        "P-A": {
            "highest": ["Purpose", "Alignment"],
            "supporting": ["Insight", "Relationships"],
            "mid": ["Communication", "Security"],
            "stretch": ["Creativity", "Leadership"]
        }
    }
    
    WEIGHTS = {
        "highest": 1.0,
        "supporting": 0.7,
        "mid": 0.4,
        "stretch": 0.1
    }
    
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
        """Parse hierarchical_results from string or dict format"""
        if isinstance(hierarchical_results, str):
            return json.loads(hierarchical_results)
        elif isinstance(hierarchical_results, dict):
            return hierarchical_results
        else:
            raise ValueError(f"hierarchical_results must be str or dict, got {type(hierarchical_results)}")
    
    def _extract_domain_scores(self, hierarchical_results: Dict[str, Any]) -> Dict[str, float]:
        """Extract average scores for each domain from hierarchical_results"""
        domain_scores = {}
        
        for domain_name, domain_data in hierarchical_results.items():
            if isinstance(domain_data, dict) and "average_score" in domain_data:
                domain_scores[domain_name] = domain_data["average_score"]
        
        return domain_scores

    def _find_domain_score(self, trait_name: str, domain_scores: Dict[str, float]) -> Optional[float]:
        """Find domain score for a trait name, handling various domain name formats"""
        trait_lower = trait_name.lower()
        
        for domain_name, score in domain_scores.items():
            if domain_name.lower() == trait_lower:
                return score
        
        for domain_name, score in domain_scores.items():
            domain_lower = domain_name.lower()
            pattern = r'\b' + re.escape(trait_lower) + r'\b'
            if re.search(pattern, domain_lower):
                return score
        
        for domain_name, score in domain_scores.items():
            domain_lower = domain_name.lower()
            parts = re.split(r'\s+(?:and|&|,|-)\s+', domain_lower)
            if trait_lower in parts:
                return score
        
        return None

    def _compute_persona_score(self, persona_code: str, domain_scores: Dict[str, float]) -> float:
        """Compute weighted score for a persona based on COG groups"""
        groups = self.PERSONA_MODEL[persona_code]
        total = 0.0
        weight_sum = 0.0
        
        for group_name, traits in groups.items():
            weight = self.WEIGHTS[group_name]
            for trait in traits:
                score = self._find_domain_score(trait, domain_scores)
                if score is not None:
                    total += score * weight
                    weight_sum += weight
        
        return round(total / weight_sum, 2) if weight_sum > 0 else 0.0

    def _get_trait_scores(self, persona_code: str, domain_scores: Dict[str, float]) -> Dict[str, Optional[float]]:
        """Get scores for trait_1 and trait_2 of a persona"""
        persona_def = next(p for p in self.PERSONA_DEFINITIONS if p["code"] == persona_code)
        return {
            "trait_1_score": self._find_domain_score(persona_def["trait_1"], domain_scores),
            "trait_2_score": self._find_domain_score(persona_def["trait_2"], domain_scores)
        }

    def _get_cog_groups(self, persona_code: str, domain_scores: Dict[str, float]) -> Dict[str, List[Dict[str, Any]]]:
        """Get COG groups with their traits and scores"""
        groups = self.PERSONA_MODEL[persona_code]
        cog_groups = {}
        
        for group_name, traits in groups.items():
            if group_name != "highest":
                cog_groups[group_name] = [
                    {
                        "trait": trait,
                        "score": self._find_domain_score(trait, domain_scores)
                    }
                    for trait in traits
                ]
        
        return cog_groups

    def _get_weighted_score_breakdown(self, persona_code: str, domain_scores: Dict[str, float]) -> Dict[str, Any]:
        """Get weighted score breakdown per COG group"""
        groups = self.PERSONA_MODEL[persona_code]
        breakdown = {}
        
        for group_name, traits in groups.items():
            weight = self.WEIGHTS[group_name]
            group_total = 0.0
            group_weight_sum = 0.0
            trait_details = []
            
            for trait in traits:
                score = self._find_domain_score(trait, domain_scores)
                if score is not None:
                    weighted_score = score * weight
                    group_total += weighted_score
                    group_weight_sum += weight
                    trait_details.append({
                        "trait": trait,
                        "raw_score": round(score, 2),
                        "weight": weight,
                        "weighted_score": round(weighted_score, 2)
                    })
            
            breakdown[group_name] = {
                "weight": weight,
                "traits": trait_details,
                "group_weighted_total": round(group_total, 2),
                "group_weight_sum": round(group_weight_sum, 2),
                "group_average": round(group_total / group_weight_sum, 2) if group_weight_sum > 0 else 0.0
            }
        
        return breakdown

    def _generate_persona_description(self, persona: Dict[str, Any], conversation_summary: Dict[str, Any]) -> str:
        """Generate personalized description for a persona"""
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
        Score: {persona['score']:.2f} 

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
    
    def generate_report(self, hierarchical_results: Any, conversation_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate persona ranking report using weighted COG groups"""
        parsed_results = self._parse_hierarchical_results(hierarchical_results) 
        domain_scores = self._extract_domain_scores(parsed_results)
        
        if not domain_scores:
            return {
                "ranked_personas": [],
                "primary_trait": None,
                "secondary_traits": [],
                "domain_scores": {}
            }
        
        persona_scores = {}
        for persona_code in self.PERSONA_MODEL.keys():
            score = self._compute_persona_score(persona_code, domain_scores)
            persona_scores[persona_code] = score

        ranked_personas_list = sorted(persona_scores.items(), key=lambda x: x[1], reverse=True)
        
        persona_rankings = []
        for rank, (persona_code, score) in enumerate(ranked_personas_list, start=1):
            persona_def = next(p for p in self.PERSONA_DEFINITIONS if p["code"] == persona_code)
            trait_scores = self._get_trait_scores(persona_code, domain_scores)
            cog_groups = self._get_cog_groups(persona_code, domain_scores)
            weighted_breakdown = self._get_weighted_score_breakdown(persona_code, domain_scores)
            
            persona_rankings.append({
                "persona": persona_def,
                "score": score,
                "trait_1_score": trait_scores["trait_1_score"],
                "trait_2_score": trait_scores["trait_2_score"],
                "rank": rank,
                "category": "Primary" if rank == 1 else ("Secondary" if rank == 2 else "Tertiary"),
                "cog_groups": cog_groups,
                "weighted_score_breakdown": weighted_breakdown
            })

        primary_trait = persona_rankings[0] if persona_rankings else None
        secondary_traits = persona_rankings[1:3] if len(persona_rankings) > 1 else []

        primary_description = None
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
                    "score": p["score"],
                    "trait_1": {
                        "name": p["persona"]["trait_1"],
                        "score": round(p["trait_1_score"], 2) if p["trait_1_score"] is not None else None
                    },
                    "trait_2": {
                        "name": p["persona"]["trait_2"],
                        "score": round(p["trait_2_score"], 2) if p["trait_2_score"] is not None else None
                    },
                    "rank": p["rank"],
                    "category": p["category"],
                    "cog_groups": p["cog_groups"],
                    "weighted_score_breakdown": p["weighted_score_breakdown"]
                }
                for p in persona_rankings
            ],
            "primary_trait": {
                "persona_code": primary_trait["persona"]["code"],
                "persona_name": primary_trait["persona"]["full_name"],
                "score": primary_trait["score"],
                "trait_1": {
                    "name": primary_trait["persona"]["trait_1"],
                    "score": round(primary_trait["trait_1_score"], 2) if primary_trait["trait_1_score"] is not None else None
                },
                "trait_2": {
                    "name": primary_trait["persona"]["trait_2"],
                    "score": round(primary_trait["trait_2_score"], 2) if primary_trait["trait_2_score"] is not None else None
                },
                "cog_groups": primary_trait["cog_groups"],
                "weighted_score_breakdown": primary_trait["weighted_score_breakdown"],
                "description": primary_description
            } if primary_trait else None,
            "secondary_traits": [
                {
                    "persona_code": st["persona"]["code"],
                    "persona_name": st["persona"]["full_name"],
                    "score": st["score"],
                    "trait_1": {
                        "name": st["persona"]["trait_1"],
                        "score": round(st["trait_1_score"], 2) if st["trait_1_score"] is not None else None
                    },
                    "trait_2": {
                        "name": st["persona"]["trait_2"],
                        "score": round(st["trait_2_score"], 2) if st["trait_2_score"] is not None else None
                    },
                    "cog_groups": st["cog_groups"],
                    "weighted_score_breakdown": st["weighted_score_breakdown"],
                    "description": secondary_descriptions[i] if i < len(secondary_descriptions) else None
                }
                for i, st in enumerate(secondary_traits)
            ],
            "domain_scores": {
                domain: round(score, 2)
                for domain, score in domain_scores.items()
            }
        }


def generate_persona_report(hierarchical_results: Any, conversation_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate persona report from hierarchical results"""
    generator = PersonaRankingGenerator()
    return generator.generate_report(hierarchical_results, conversation_summary)

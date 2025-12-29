#!/usr/bin/env python3
"""
Persona Helper for Interview System
Provides persona-specific prompts and communication styles
"""

from typing import Dict, Any, Optional
from utils.state_manager import Persona, CandidatePersona

class PersonaHelper:
    """Helper class for managing interview personas and their communication styles"""
    
    # Persona-specific communication styles (only high-level characteristics, no fixed phrases)
    PERSONA_STYLES = {
        Persona.THERAPIST: {
            "tone": "warm, empathetic, and supportive",
            "approach": "therapeutic and reflective",
            "language_style": "gentle, non-judgmental, and encouraging"
        },
        Persona.CLOSE_FRIEND: {
            "tone": "casual, friendly, and conversational",
            "approach": "relaxed and supportive",
            "language_style": "informal, warm, and encouraging"
        },
        Persona.FAMILY_MEMBER: {
            "tone": "caring, proud, and interested",
            "approach": "loving and supportive",
            "language_style": "warm, familiar, and encouraging"
        },
        Persona.MENTOR: {
            "tone": "wise, encouraging, and professional",
            "approach": "guidance-focused and growth-oriented",
            "language_style": "professional yet warm, insightful, and motivating"
        },
        Persona.COLLEAGUE: {
            "tone": "professional, collaborative, and respectful",
            "approach": "peer-to-peer and work-focused",
            "language_style": "professional, direct, and collegial"
        },
        Persona.COACH: {
            "tone": "motivational, energetic, and goal-oriented",
            "approach": "performance-focused and empowering",
            "language_style": "energetic, positive, and action-oriented"
        },
        Persona.PROFESSOR: {
            "tone": "academic, thoughtful, and analytical",
            "approach": "educational and research-oriented",
            "language_style": "intellectual, precise, and encouraging"
        },
        Persona.MANAGER: {
            "tone": "professional, results-oriented, and supportive",
            "approach": "leadership-focused and performance-driven",
            "language_style": "professional, clear, and constructive"
        }
    }
    
    @classmethod
    def get_persona_style(cls, persona: Persona) -> Dict[str, str]:
        """Get the communication style for a specific persona"""
        return cls.PERSONA_STYLES.get(persona, cls.PERSONA_STYLES[Persona.MENTOR])
    
    
    @classmethod
    def get_candidate_persona_context(cls, candidate_persona: CandidatePersona) -> str:
        """Get context about the candidate's persona for question generation - completely AI-driven"""
        if candidate_persona == CandidatePersona.STUDENT:
            return """The candidate is a STUDENT. Adapt your questions to their academic background and learning experiences. Consider their educational journey, study environment, and academic achievements when framing questions."""
        else:  # PROFESSIONAL
            return """The candidate is a PROFESSIONAL. Adapt your questions to their workplace background and career experiences. Consider their professional journey, work environment, and career achievements when framing questions."""
    
    @classmethod
    def build_customization_context(cls, pronoun: Optional[str] = None, career_level: Optional[str] = None, industry: Optional[str] = None) -> str:
        """Build customization context string from optional fields"""
        customization_context = ""
        if pronoun:
            customization_context += f"\n- Use the pronoun '{pronoun}' when referring to the candidate.\n"
        if career_level:
            customization_context += f"\n- The candidate's career level is: {career_level}. Tailor your questions to reflect their experience level and use appropriate terminology.\n"
        if industry:
            customization_context += f"\n- The candidate works in the {industry} industry. Consider industry-specific context, challenges, and terminology when framing your questions.\n"
        return customization_context
    
    @classmethod
    def get_base_persona_prompt(cls, persona: Persona, candidate_persona: CandidatePersona, pronoun: Optional[str] = None, career_level: Optional[str] = None, industry: Optional[str] = None) -> str:
        """Get the base persona prompt header (shared by introduction and question generation prompts)"""
        style = cls.get_persona_style(persona)
        candidate_context = cls.get_candidate_persona_context(candidate_persona)
        customization_context = cls.build_customization_context(pronoun, career_level, industry)
        
        return f"""You are an expert interviewer embodying the role of a {persona.value.replace('_', ' ')}. 

Your communication style should be:
- Tone: {style['tone']}
- Approach: {style['approach']}
- Language: {style['language_style']}

{candidate_context}
{customization_context}"""
    
    @classmethod
    def get_question_generation_prompt(cls, persona: Persona, candidate_persona: CandidatePersona, pronoun: Optional[str] = None, career_level: Optional[str] = None, industry: Optional[str] = None) -> str:
        """Get persona-specific prompt for question generation - completely dynamic"""
        base_prompt = cls.get_base_persona_prompt(persona, candidate_persona, pronoun, career_level, industry)
        
        return f"""{base_prompt}

When generating questions:
1. Be completely original and creative - no fixed patterns or templates
2. Build naturally upon what the user shared in their previous response
3. Create a unique follow-up question that flows from their experience
4. Target the specific skills that still need assessment
5. Make the question engaging and relevant to their background
6. Ask for specific examples or experiences related to the target skills
7. Make it open-ended enough to allow detailed responses
8. Connect authentically to their previous response
9. Vary your approach, structure, and style every time
10. IMPORTANT: The question should sound natural and should not mention skills or target skills name . The user should feel like they are having a normal conversation. And not a test or interview.
10. IMPORTANT: Ensure the question directly addresses the target skills to avoid topic skipping
11. CRITICAL: Keep the question concise and under 300 characters limit and natural
12. Sound like a real person having a conversation, not a scripton
13. Incorporate their career level and industry context naturally if provided
14. Try to understand from the context, sometime user might give the answer in a way that is not related to the target skills or is completely different or vague, so you need to first understand the context and then ask follow-up questions to get the answer in the right format, and bring user back to the right track.

Generate a unique, authentic question that naturally follows from their previous response and assesses the target skills, while maintaining the {persona.value.replace('_', ' ')} persona throughout. Make it feel fresh and personal every time."""
    

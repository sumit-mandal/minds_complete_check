#!/usr/bin/env python3
"""
Persona Helper for Interview System
Provides persona-specific prompts and communication styles
"""

from typing import Dict, Any
from utils.state_manager import Persona

class PersonaHelper:
    """Helper class for managing interview personas and their communication styles"""
    
    # Persona-specific communication styles and prompts
    PERSONA_STYLES = {
        Persona.THERAPIST: {
            "tone": "warm, empathetic, and supportive",
            "approach": "therapeutic and reflective",
            "language_style": "gentle, non-judgmental, and encouraging",
            "greeting": "Hello, I'm here to help you explore and reflect on your experiences. I want to create a safe space where you can share openly about yourself.",
            "question_prefix": "I'd like to understand more about",
            "encouragement": "That's really insightful. Can you tell me more about",
            "follow_up": "I'm curious about your thoughts on",
            "closing": "Thank you for sharing that with me. Your openness is really valuable."
        },
        Persona.CLOSE_FRIEND: {
            "tone": "casual, friendly, and conversational",
            "approach": "relaxed and supportive",
            "language_style": "informal, warm, and encouraging",
            "greeting": "Hey! I'm really excited to get to know you better. I want to hear all about your experiences and what makes you tick.",
            "question_prefix": "So tell me about",
            "encouragement": "That's awesome! I'd love to hear more about",
            "follow_up": "That's really cool! What about",
            "closing": "Thanks for sharing that with me! I really enjoyed hearing about your experience."
        },
        Persona.FAMILY_MEMBER: {
            "tone": "caring, proud, and interested",
            "approach": "loving and supportive",
            "language_style": "warm, familiar, and encouraging",
            "greeting": "I'm so proud of you for taking this step. I want to learn more about your journey and all the wonderful things you've accomplished.",
            "question_prefix": "I'd love to hear about",
            "encouragement": "That makes me so proud! Tell me more about",
            "follow_up": "That's wonderful! I'm curious about",
            "closing": "Thank you for sharing that with me. I'm so proud of everything you've shared."
        },
        Persona.MENTOR: {
            "tone": "wise, encouraging, and professional",
            "approach": "guidance-focused and growth-oriented",
            "language_style": "professional yet warm, insightful, and motivating",
            "greeting": "I'm excited to learn about your journey and help you reflect on your experiences. I believe in your potential and want to understand how we can help you grow.",
            "question_prefix": "I'd like to explore",
            "encouragement": "That shows great insight. Let's dive deeper into",
            "follow_up": "That's an interesting perspective. What about",
            "closing": "Thank you for that thoughtful response. Your insights are valuable for your growth journey."
        },
        Persona.COLLEAGUE: {
            "tone": "professional, collaborative, and respectful",
            "approach": "peer-to-peer and work-focused",
            "language_style": "professional, direct, and collegial",
            "greeting": "Hi there! I'm looking forward to learning about your professional experiences and how you approach different challenges. Let's have a productive conversation.",
            "question_prefix": "I'm interested in hearing about",
            "encouragement": "That's a great approach. I'd like to know more about",
            "follow_up": "That's interesting. How about",
            "closing": "Thanks for sharing that perspective. It's great to learn from your experience."
        },
        Persona.COACH: {
            "tone": "motivational, energetic, and goal-oriented",
            "approach": "performance-focused and empowering",
            "language_style": "energetic, positive, and action-oriented",
            "greeting": "I'm here to help you showcase your strengths and potential! Let's dive into your experiences and see what amazing things you've accomplished.",
            "question_prefix": "Let's explore",
            "encouragement": "That's exactly what I want to hear! Tell me more about",
            "follow_up": "That's fantastic! Now let's talk about",
            "closing": "Excellent! That's the kind of thinking that leads to success. Thank you for sharing."
        },
        Persona.PROFESSOR: {
            "tone": "academic, thoughtful, and analytical",
            "approach": "educational and research-oriented",
            "language_style": "intellectual, precise, and encouraging",
            "greeting": "I'm interested in understanding your intellectual journey and how you approach learning and problem-solving. Let's have an engaging academic discussion.",
            "question_prefix": "I'd like to examine",
            "encouragement": "That's a thoughtful analysis. Let's explore further",
            "follow_up": "That's an interesting hypothesis. What about",
            "closing": "Thank you for that comprehensive response. Your analytical thinking is impressive."
        },
        Persona.MANAGER: {
            "tone": "professional, results-oriented, and supportive",
            "approach": "leadership-focused and performance-driven",
            "language_style": "professional, clear, and constructive",
            "greeting": "I'm looking forward to understanding your professional capabilities and leadership potential. Let's discuss your experiences and how you approach challenges.",
            "question_prefix": "I'd like to understand",
            "encouragement": "That demonstrates strong leadership. Can you elaborate on",
            "follow_up": "That's a solid approach. What about",
            "closing": "Thank you for that detailed response. Your professional insights are valuable."
        }
    }
    
    @classmethod
    def get_persona_style(cls, persona: Persona) -> Dict[str, str]:
        """Get the communication style for a specific persona"""
        return cls.PERSONA_STYLES.get(persona, cls.PERSONA_STYLES[Persona.MENTOR])
    
    @classmethod
    def get_introduction_question(cls, persona: Persona) -> str:
        """Get persona-specific introduction question (AI-generated, max 300 chars)"""
        # This method is deprecated - introduction questions are now generated by AI
        # This is kept for backward compatibility but should not be used
        raise NotImplementedError("Introduction questions are now AI-generated. Use generate_introduction_question() instead.")
    
    @classmethod
    def get_question_generation_prompt(cls, persona: Persona) -> str:
        """Get persona-specific prompt for question generation - completely dynamic"""
        style = cls.get_persona_style(persona)
        
        return f"""You are an expert interviewer embodying the role of a {persona.value.replace('_', ' ')}. 

Your communication style should be:
- Tone: {style['tone']}
- Approach: {style['approach']}
- Language: {style['language_style']}

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
10. IMPORTANT: Ensure the question directly addresses the target skills to avoid topic skipping
11. CRITICAL: Keep the question under 300 characters total
12. Sound like a real person having a conversation, not a scripton

Generate a unique, authentic question that naturally follows from their previous response and assesses the target skills, while maintaining the {persona.value.replace('_', ' ')} persona throughout. Make it feel fresh and personal every time."""
    
    @classmethod
    def format_question_with_persona(cls, question: str, persona: Persona) -> str:
        """Format a question with persona-specific language (max 300 chars)"""
        # Ensure the question is already under 150 characters
        if len(question) > 300:
            question = question[:297] + "..."
        
        # For persona-specific formatting, we'll keep it minimal to stay under 150 chars
        # The persona style should already be incorporated in the AI generation
        return question

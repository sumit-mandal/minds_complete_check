import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from dotenv import load_dotenv
import uuid

load_dotenv()

DATABASE_URL = (
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}".format(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", 5432),
        db=os.environ["DB_NAME"],
    )
)

engine = sa.create_engine(DATABASE_URL,pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    session_id = sa.Column(
        pg.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )

    user_id = sa.Column(
        pg.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_interview_sessions_user_id"),
        nullable=False,
        index=True,
    )

    start_time = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    end_time = sa.Column(sa.TIMESTAMP(timezone=True))
    max_questions = sa.Column(sa.Integer)
    total_questions = sa.Column(sa.Integer)
    progress_percentage = sa.Column(sa.Float)
    covered_skills = sa.Column(sa.Integer)
    total_skills = sa.Column(sa.Integer)
    completion_reason = sa.Column(sa.String(255))
    overall_score = sa.Column(sa.Float)
    status = sa.Column(sa.String(50), nullable=False, server_default="in_progress")

    responses = relationship(
        "InterviewResponse", back_populates="session", cascade="all, delete-orphan"
    )
    final_result = relationship(
        "FinalResult",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )


class InterviewResponse(Base):
    __tablename__ = "interview_responses"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    session_id = sa.Column(
        pg.UUID(as_uuid=True),
        sa.ForeignKey("interview_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_number = sa.Column(sa.Integer, nullable=False)
    question_text = sa.Column(sa.Text, nullable=False)
    user_response = sa.Column(sa.Text, nullable=False)
    question_type = sa.Column(sa.String(100))
    target_skills = sa.Column(pg.ARRAY(sa.String))
    timestamp = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now())

    session = relationship("InterviewSession", back_populates="responses")
    evaluations = relationship(
        "SkillEvaluation", back_populates="response", cascade="all, delete-orphan"
    )

class SkillEvaluation(Base):
    __tablename__ = "skill_evaluations"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    session_id = sa.Column(
        pg.UUID(as_uuid=True),
        sa.ForeignKey("interview_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    response_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("interview_responses.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_name = sa.Column(sa.String(255), nullable=False)
    score = sa.Column(sa.Float)
    confidence_level = sa.Column(sa.Float)
    reasoning = sa.Column(sa.Text)
    timestamp = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now())

    response = relationship("InterviewResponse", back_populates="evaluations")


class FinalResult(Base):
    __tablename__ = "final_results"

    session_id = sa.Column(
        pg.UUID(as_uuid=True),
        sa.ForeignKey("interview_sessions.session_id", ondelete="CASCADE"),
        primary_key=True,
    )
    overall_score = sa.Column(sa.Float)
    domain_scores = sa.Column(pg.JSONB, default=dict)
    skill_scores = sa.Column(pg.JSONB, default=dict)
    hierarchical_results = sa.Column(pg.JSONB, default=dict)
    summary = sa.Column(pg.JSONB, default=dict)
    created_at = sa.Column(sa.TIMESTAMP(timezone=True), server_default=sa.func.now())

    session = relationship("InterviewSession", back_populates="final_result")


@contextmanager
def get_db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class InterviewDatabase:
    """ PostgreSQL-backed storage for interview data """
    
    def _to_uuid(self, session_id: Union[str, uuid.UUID]) -> uuid.UUID:
        """Convert session_id to UUID if it's a string"""
        if isinstance(session_id, str):
            # Try to parse as UUID first
            try:
                return uuid.UUID(session_id)
            except ValueError:
                # If it's not a valid UUID string, generate a deterministic UUID from the string
                # This ensures the same string always maps to the same UUID
                return uuid.uuid5(uuid.NAMESPACE_DNS, session_id)
        return session_id
    
    def create_session(self, user_id: str, max_questions: int) -> str:
        """Create a new interview session and return the session_id"""
        if not user_id:
            raise ValueError("user_id cannot be None or empty")
        
        with get_db_session() as db:
            session = InterviewSession(
                user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
                max_questions=max_questions,
            )
            db.add(session)
            db.flush()
            session_id = str(session.session_id)
            return session_id
    
    def save_session_start(self, session_id: str, user_id: str, max_questions: int):
        if not user_id:
            raise ValueError("user_id cannot be None or empty")
        
        with get_db_session() as db:
            db.merge(
                InterviewSession(
                    session_id=self._to_uuid(session_id) if hasattr(self, '_to_uuid') else session_id,
                    user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
                    max_questions=max_questions,
                )
            )
    
    def save_response(
        self,
        session_id:str,
        question_number: int,
        question_text: str,
        user_response: str,
        question_type: str,
        target_skills: List[str],) -> int:
        with get_db_session() as db:
                session_obj = (
                    db.query(InterviewSession).filter_by(session_id=self._to_uuid(session_id)).one()
                )
                response = InterviewResponse(
                    session=session_obj,
                    question_number=question_number,
                    question_text=question_text,
                    user_response=user_response,
                    question_type=question_type,
                    target_skills=target_skills,
                )
                db.add(response)
                session_obj.total_questions = question_number
                db.flush()
                return response.id
    def save_evaluation(
        self, session_id: str, response_id: int, evaluation: Dict[str, Any]
    ):
        with get_db_session() as db:
            entries = [
                SkillEvaluation(
                    session_id=self._to_uuid(session_id),
                    response_id=response_id,
                    skill_name=skill,
                    score=score,
                    confidence_level=evaluation.get("confidence_level", 0.0),
                    reasoning=evaluation.get("reasoning", ""),
                )
                for skill, score in evaluation.get("skill_scores", {}).items()
            ]
            db.add_all(entries)

    def save_session_completion(
        self, session_id: str, final_results: Dict[str, Any], completion_reason: str
    ):
        with get_db_session() as db:
            session_obj = (
                db.query(InterviewSession).filter_by(session_id=self._to_uuid(session_id)).one()
            )
            session_obj.end_time = datetime.now(timezone.utc)
            session_obj.progress_percentage = final_results.get("interview_progress")
            session_obj.covered_skills = final_results.get("covered_skills")
            session_obj.total_skills = final_results.get("total_skills")
            session_obj.completion_reason = completion_reason
            session_obj.overall_score = final_results.get("overall_score")
            session_obj.status = "completed"

            db.merge(
                FinalResult(
                    session_id=self._to_uuid(session_id),
                    overall_score=final_results.get("overall_score"),
                    domain_scores=final_results.get("domain_scores", {}),
                    skill_scores=final_results.get("skill_scores", {}),
                    hierarchical_results=final_results.get("hierarchical_results", {}),
                    summary=final_results.get("summary", {}),
                )
            )

    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        with get_db_session() as db:
            session_obj = (
                db.query(InterviewSession)
                .filter_by(session_id=self._to_uuid(session_id))
                .options(
                    sa.orm.selectinload(InterviewSession.responses).selectinload(
                        InterviewResponse.evaluations
                    ),
                    sa.orm.selectinload(InterviewSession.final_result),
                )
                .first()
            )
            if not session_obj:
                return None

            # Calculate session duration
            duration_seconds = None
            if session_obj.start_time:
                end_time = session_obj.end_time if session_obj.end_time else datetime.now(timezone.utc)
                if end_time:
                    duration_seconds = int((end_time - session_obj.start_time).total_seconds())
            
            data = {
                "session": {
                    "session_id": session_obj.session_id,
                    "user_id": str(session_obj.user_id),
                    "start_time": session_obj.start_time,
                    "end_time": session_obj.end_time,
                    "duration_seconds": duration_seconds,
                    "max_questions": session_obj.max_questions,
                    "total_questions": session_obj.total_questions,
                    "progress_percentage": session_obj.progress_percentage,
                    "covered_skills": session_obj.covered_skills,
                    "total_skills": session_obj.total_skills,
                    "completion_reason": session_obj.completion_reason,
                    "overall_score": session_obj.overall_score,
                    "status": session_obj.status,
                },
                "responses": [],
                "final_results": {},
            }

            for response in sorted(
                session_obj.responses, key=lambda r: r.question_number
            ):
                data["responses"].append(
                    {
                        "id": response.id,
                        "question_number": response.question_number,
                        "question_text": response.question_text,
                        "user_response": response.user_response,
                        "question_type": response.question_type,
                        "target_skills": response.target_skills,
                        "timestamp": response.timestamp,
                        "evaluations": [
                            {
                                "skill_name": ev.skill_name,
                                "score": ev.score,
                                "confidence_level": ev.confidence_level,
                                "reasoning": ev.reasoning,
                                "timestamp": ev.timestamp,
                            }
                            for ev in sorted(
                                response.evaluations, key=lambda e: e.skill_name
                            )
                        ],
                    }
                )

            if session_obj.final_result:
                fr = session_obj.final_result
                data["final_results"] = {
                    "session_id": session_id,
                    "overall_score": fr.overall_score,
                    "domain_scores": fr.domain_scores,
                    "skill_scores": fr.skill_scores,
                    "hierarchical_results": fr.hierarchical_results,
                    "summary": fr.summary,
                    "created_at": fr.created_at,
                }

            return data

    def get_all_sessions(self):
        with get_db_session() as db:
            rows = (
                db.query(InterviewSession)
                .order_by(InterviewSession.start_time.desc())
                .all()
            )
            return [
                {
                    "session_id": row.session_id,
                    "user_id": str(row.user_id),
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "status": row.status,
                    "overall_score": row.overall_score,
                }
                for row in rows
            ]

    def get_session_statistics(self) -> Dict[str, Any]:
        with get_db_session() as db:
            total = db.query(sa.func.count(InterviewSession.session_id)).scalar() or 0
            completed = (
                db.query(sa.func.count(InterviewSession.session_id))
                .filter(InterviewSession.status == "completed")
                .scalar()
                or 0
            )
            avg_score = (
                db.query(sa.func.avg(FinalResult.overall_score))
                .filter(FinalResult.overall_score.isnot(None))
                .scalar()
                or 0.0
            )
            avg_questions = (
                db.query(sa.func.avg(InterviewSession.total_questions))
                .filter(InterviewSession.status == "completed")
                .scalar()
                or 0.0
            )

            return {
                "total_sessions": total,
                "completed_sessions": completed,
                "average_score": round(avg_score, 2),
                "average_questions": round(avg_questions, 1),
                "completion_rate": round((completed / total * 100) if total else 0, 1),
            }

    def get_all_interviews_by_user_id(self,user_id:str) -> List[Dict[str, Any]]:
        with get_db_session() as db:
            sessions = (
            db.query(InterviewSession)
            .filter(InterviewSession.user_id == user_id)
            .options(
                sa.orm.selectinload(InterviewSession.responses).selectinload(
                    InterviewResponse.evaluations
                ),
                sa.orm.selectinload(InterviewSession.final_result),
            )
            .order_by(InterviewSession.start_time.desc())
            .all()
        ) 

        if not sessions: 
            return "No Sessions Found for User"

        all_interviews = [] 
        for session_obj in sessions:
            # Calculate session duration
            duration_seconds = None
            if session_obj.start_time:
                end_time = session_obj.end_time if session_obj.end_time else datetime.now(timezone.utc)
                if end_time:
                    duration_seconds = int((end_time - session_obj.start_time).total_seconds())
            
            session_data = {
                "session": {
                    "session_id": str(session_obj.session_id),
                    "user_id": str(session_obj.user_id),
                    "start_time": session_obj.start_time.isoformat() if session_obj.start_time else None,
                    "end_time": session_obj.end_time.isoformat() if session_obj.end_time else None,
                    "duration_seconds": duration_seconds,
                    "max_questions": session_obj.max_questions,
                    "total_questions": session_obj.total_questions,
                    "progress_percentage": session_obj.progress_percentage,
                    "covered_skills": session_obj.covered_skills,
                    "total_skills": session_obj.total_skills,
                    "completion_reason": session_obj.completion_reason,
                    "overall_score": session_obj.overall_score,
                    "status": session_obj.status,
                },
                "responses": [],
                "final_results": {},
            }

            # Get all responses for the session
            for response in sorted(
                    session_obj.responses, key=lambda r: r.question_number
                ):
                    session_data["responses"].append({
                        "id": response.id,
                        "question_number": response.question_number,
                        "question_text": response.question_text,
                        "user_response": response.user_response,
                        "question_type": response.question_type,
                        "target_skills": response.target_skills,
                        "timestamp": response.timestamp.isoformat() if response.timestamp else None,
                        "evaluations": [
                            {
                                "id": ev.id,
                                "skill_name": ev.skill_name,
                                "score": ev.score,
                                "confidence_level": ev.confidence_level,
                                "reasoning": ev.reasoning,
                                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                            }
                            for ev in sorted(
                                response.evaluations, key=lambda e: e.skill_name
                            )
                        ],
                    })


            # Get final results if available
            if session_obj.final_result:
                fr = session_obj.final_result
                session_data["final_results"] = {
                    "session_id": str(fr.session_id),
                    "overall_score": fr.overall_score,
                    "domain_scores": fr.domain_scores if fr.domain_scores else {},
                    "skill_scores": fr.skill_scores if fr.skill_scores else {},
                    "hierarchical_results": fr.hierarchical_results if fr.hierarchical_results else {},
                    "summary": fr.summary if fr.summary else {},
                    "created_at": fr.created_at.isoformat() if fr.created_at else None,
                }
            
            all_interviews.append(session_data)
        
        return all_interviews

    def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Generate or retrieve an LLM-based summary for a session"""
        from utils.graph_3_llm_helper import evaluation_llm
        from utils.persona_helper import PersonaHelper
        from utils.state_manager import Persona, CandidatePersona
        from utils.langgraph_interviewer import LangGraphInterviewer
        import json
        
        def _json_default(obj):
            if isinstance(obj, uuid.UUID):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"{obj} is not JSON serializable")
        
        
        session_data = self.get_session_data(session_id)
        if not session_data:
            return None
        
        # Try to get candidate info from LangGraph state
        name = None
        persona = None
        candidate_persona = None
        pronoun = None
        career_level = None
        industry = None
        
        try:
            interviewer = LangGraphInterviewer()
            config = {"configurable": {"thread_id": session_id}}
            current_state = interviewer.graph.get_state(config)
            if current_state.values:
                name = current_state.values.get("name")
                persona_value = current_state.values.get("persona")
                candidate_persona_value = current_state.values.get("candidate_persona")
                pronoun = current_state.values.get("pronoun")
                career_level = current_state.values.get("career_level")
                industry = current_state.values.get("industry")
                
                # Convert to enums if needed
                if persona_value:
                    if isinstance(persona_value, str):
                        try:
                            persona = Persona(persona_value)
                        except ValueError:
                            persona = None
                    else:
                        persona = persona_value
                if candidate_persona_value:
                    if isinstance(candidate_persona_value, str):
                        try:
                            candidate_persona = CandidatePersona(candidate_persona_value)
                        except ValueError:
                            candidate_persona = None
                    else:
                        candidate_persona = candidate_persona_value
        except Exception as e:
            print(f"Could not retrieve candidate info from LangGraph state: {e}")
            # Continue without personalization if state is not available
        
        conversation_data = {
            "session_info": session_data["session"],
            "responses": []
        }
        
        for response in session_data["responses"]:
            response_data = {
                "question_number": response["question_number"],
                "question": response["question_text"],
                "user_response": response["user_response"],
                "evaluations": {}
            }
            
            for eval_data in response["evaluations"]:
                skill_name = eval_data["skill_name"]
                response_data["evaluations"][skill_name] = {
                    "score": eval_data["score"],
                    "confidence": eval_data["confidence_level"],
                    "reasoning": eval_data["reasoning"]
                }
            
            conversation_data["responses"].append(response_data)
        
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
            personalization_context += f"Interview Persona: {persona.value.replace('_', ' ').title()}\n"
        if candidate_persona:
            personalization_context += f"Candidate Type: {candidate_persona.value.title()}\n"
        
        # Get persona style for personalization
        persona_style = None
        if persona:
            persona_style = PersonaHelper.get_persona_style(persona)
        
        # Build persona-specific tone guidance
        tone_guidance = ""
        if persona_style:
            tone_guidance = f"""
Write the summary in a {persona_style['tone']} manner, with a {persona_style['approach']} approach, using {persona_style['language_style']} language. Make it feel personal and authentic, as if written by a {persona.value.replace('_', ' ')} who genuinely cares about {name if name else 'the candidate'}'s growth and development.
"""
        
        summary_prompt = f"""You are an expert interview analyst. Analyze the conversation and produce a personalized JSON summary.

{personalization_context}

Conversation Data: {json.dumps(conversation_data, indent=2, default=_json_default)}

{tone_guidance}

When writing the summary:
- Address {name if name else 'the candidate'} directly by name if provided
- Use {pronoun if pronoun else 'their'} pronouns appropriately
- Reflect on their specific journey and context (career level, industry if provided)
- Make it feel personal and meaningful, not generic or dry
- Highlight what makes {name if name else 'them'} unique based on their responses
- Keep the summary detailed and comprehensive, but not too long. And it should not feel dry or generic.

Return JSON like:
{{
    "overall_score": 7.5,
    "key_strengths": ["Clear communication"],
    "areas_for_improvement": ["Provide more specifics"],
    "communication_style": "Professional and articulate",
    "problem_solving_approach": "Systematic and collaborative",
    "emotional_intelligence": "Good self-awareness",
    "professional_maturity": "Shows leadership",
    "specific_examples": ["Handled team conflict well"],
    "recommendations": ["Give concrete numbers"],
    "overall_impression": "Personalized impression that addresses {name if name else 'the candidate'} by name and feels warm and engaging"
}}
Return JSON only."""
        
        try:
            response = evaluation_llm.invoke(summary_prompt)
            response_text = response.content.strip()
            
            if response_text.startswith("{") and response_text.endswith("}"):
                summary_data = json.loads(response_text)
            else:
                import re
                match = re.search(r"\{.*\}", response_text, re.DOTALL)
                summary_data = json.loads(match.group()) if match else {}
            
            return {
                "session_id": session_id,
                "conversation_summary": summary_data,
                "conversation_data": conversation_data
            }
        except Exception as e:
            print(f"Error generating conversation summary: {e}")
            return {
                "session_id": session_id,
                "conversation_summary": {
                    "overall_score": 0.0,
                    "analysis": "Error generating summary",
                    "strengths": [],
                    "improvements": [],
                    "recommendations": []
                },
                "conversation_data": conversation_data
            }

    def save_domain_summary(self, session_id: str, domain_summary: Dict[str, Any]):
        """Save domain summary to the final_results table"""
        with get_db_session() as db:
            final_result = (
                db.query(FinalResult)
                .filter_by(session_id=self._to_uuid(session_id))
                .first()
            )
            
            if final_result:
                # Update existing summary with domain_summary
                current_summary = final_result.summary if final_result.summary else {}
                current_summary["domain_summary"] = domain_summary
                final_result.summary = current_summary
            else:
                # Create new final_result entry with domain_summary
                final_result = FinalResult(
                    session_id=self._to_uuid(session_id),
                    summary={"domain_summary": domain_summary}
                )
                db.add(final_result)

    def get_domain_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve domain summary from the final_results table"""
        with get_db_session() as db:
            final_result = (
                db.query(FinalResult)
                .filter_by(session_id=self._to_uuid(session_id))
                .first()
            )
            
            if final_result and final_result.summary:
                return final_result.summary.get("domain_summary")
            return None

    def get_session_time_info(self, session_id: str) -> Dict[str, Any]:
        """Get session time information (start_time, end_time, duration_seconds) - optimized query"""
        with get_db_session() as db:
            # Only query the time columns we need for better performance
            result = (
                db.query(
                    InterviewSession.start_time,
                    InterviewSession.end_time
                )
                .filter_by(session_id=self._to_uuid(session_id))
                .first()
            )
            if not result:
                return None
            
            start_time, end_time = result
            
            # Calculate session duration
            duration_seconds = None
            if start_time:
                end_time_val = end_time if end_time else datetime.now(timezone.utc)
                if end_time_val:
                    duration_seconds = int((end_time_val - start_time).total_seconds())
            
            return {
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "duration_seconds": duration_seconds,
            }

    def get_previous_questions(self, session_id: str, limit: int = 10) -> List[str]:
        """Get previously asked questions for a session"""
        with get_db_session() as db:
            responses = (
                db.query(InterviewResponse)
                .filter_by(session_id=self._to_uuid(session_id))
                .order_by(InterviewResponse.question_number.desc())
                .limit(limit)
                .all()
            )
            # Return questions in chronological order (oldest first)
            return [r.question_text for r in reversed(responses) if r.question_text]























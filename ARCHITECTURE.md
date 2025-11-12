# System Architecture

## Overview

This document outlines the high-level architecture of our automated interview assessment system, focusing on the core frameworks and decision routing mechanisms that power intelligent, adaptive interviewing.

## Core Technology Stack

### Frameworks & Libraries

1. **LangGraph** - State machine orchestration for interview flow
2. **LangChain** - LLM integration and structured output management
3. **FastAPI** - RESTful API layer with automatic documentation
4. **Pydantic** - Type-safe data validation and state management
5. **Google Gemini 2.0 Flash** - Large Language Model provider
6. **SQLite** - Persistent data storage for interview sessions

## System Architecture Layers

### 1. API Layer (FastAPI)

**Purpose**: HTTP interface for client interactions

**Key Components**:
- RESTful endpoints for interview lifecycle management
- Request/response validation using Pydantic models
- CORS middleware for frontend integration
- Session management and routing

**Decision Points**: Routes requests to appropriate interview handlers based on session state

---

### 2. Orchestration Layer (LangGraph)

**Purpose**: State machine that controls interview flow and routing

**Architecture Pattern**: Graph-based workflow with conditional edges

**Core Nodes**:
- **`start_interview`**: Initializes interview session and generates introduction
- **`evaluate_response`**: Analyzes candidate responses and updates skill assessments
- **`generate_question`**: Creates next question based on uncovered skills and context

**Decision Routing**:
```
Start → Conditional Edge → [Has Response?]
                         ├─ Yes → Evaluate Response
                         └─ No → Show Introduction

Evaluate → Conditional Edge → [Interview Complete?]
                            ├─ Yes → End
                            └─ No → Generate Question

Generate Question → End
```

**State Management**: 
- TypedDict-based state object maintains entire interview context
- Serializable state persists across API calls via session storage
- State includes: progress, skill coverage, persona settings, evaluation history

---

### 3. Intelligence Layer (LangChain + Gemini)

**Purpose**: LLM-powered question generation and evaluation

**Specialized LLM Instances**:

1. **Question Generator** (Temperature: 0.7)
   - Generates contextual, persona-appropriate questions
   - Uses structured output for consistent formatting
   - Considers candidate background (student vs professional)

2. **Response Evaluator** (Temperature: 0.1)
   - Analyzes candidate responses for skill demonstration
   - Assigns scores (0-10) to multiple skills simultaneously
   - Provides reasoning and confidence levels

3. **Summarizer** (Temperature: 0.7)
   - Generates comprehensive interview summaries
   - Identifies strengths, weaknesses, and recommendations

**Decision Routing in LLM Calls**:
- **Skill Selection**: LLM analyzes uncovered skills and selects 2-3 target skills per question
- **Question Context**: Builds upon previous responses for natural conversation flow
- **Persona Adaptation**: Adjusts tone and framing based on interviewer and candidate personas

---

### 4. State Management Layer (StateManager)

**Purpose**: Tracks interview progress and skill assessment

**Key Responsibilities**:
- Maintains hierarchical domain → subdomain → skill structure
- Tracks which skills have been covered vs. uncovered
- Updates scores dynamically as skills are re-assessed
- Calculates progress percentages and completion status

**Decision Routing for Skill Selection**:
```
Priority Algorithm:
1. Skills never asked directly (highest priority: +1000)
2. Uncovered skills (+25)
3. Low-scored skills (below 5.0: +30-50)
4. Related skills (same domain/subdomain: context-based)
5. Unrelated skills (for diversity: +remaining)

Result: Selects top 2-3 skills maximizing coverage and assessment quality
```

**Skill Tracking**:
- Tracks if skill was directly asked about vs. only mentioned in response
- Maintains assessment history for each skill (allows score updates)
- Prevents topic skipping by ensuring all skills get direct questions

---

### 5. Persona System

**Purpose**: Dual-persona framework for personalized interviewing

**Components**:

1. **Interviewer Persona**: Controls communication style
   - Options: Mentor, Colleague, Professor, Coach, Therapist, etc.
   - Influences: Tone, approach, language style

2. **Candidate Persona**: Determines question context
   - Options: Student, Professional
   - Influences: Question framing (academic vs. workplace scenarios)

**Decision Routing**: 
- Persona settings flow through entire interview pipeline
- LLM prompts dynamically include persona-specific instructions
- Questions are generated with appropriate context for candidate background

---

### 6. Data Persistence Layer (SQLite)

**Purpose**: Stores interview sessions, responses, and results

**Tables**:
- `interview_sessions`: Session metadata and progress
- `interview_responses`: Question-answer pairs
- `skill_evaluations`: Detailed skill assessments
- `final_results`: Completed interview summaries

**Decision Points**: 
- Automatically saves responses and evaluations after each interaction
- Enables session resumption and historical analysis
- Supports analytics and reporting endpoints

---

## Decision Flow Architecture

### High-Level Flow

```
┌─────────────┐
│ API Request │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ LangGraph State │
│   Machine       │
└──────┬──────────┘
       │
       ├─► Start Interview
       │   ├─ Initialize StateManager
       │   ├─ Generate Introduction (LLM)
       │   └─ Return Question
       │
       ├─► Evaluate Response
       │   ├─ Parse User Response
       │   ├─ Evaluate Skills (LLM)
       │   ├─ Update StateManager
       │   ├─ Save to Database
       │   └─ Check Completion
       │
       └─► Generate Question
           ├─ Get Uncovered Skills
           ├─ Select Target Skills (Priority Algorithm)
           ├─ Generate Question (LLM with Persona)
           └─ Return Next Question
```

### Skill Selection Decision Tree

```
Are there uncovered skills?
├─ Yes → Apply Priority Algorithm
│         ├─ Never asked? → Highest Priority
│         ├─ Low score? → High Priority
│         ├─ Related to last response? → Context Priority
│         └─ Select Top 2-3 Skills
│
└─ No → Interview Complete → Generate Summary
```

### Interview Completion Criteria

Interview completes when ANY of:
1. **Progress ≥ 99%**: Almost all skills assessed
2. **All Skills Covered**: Every skill has been evaluated
3. **Max Questions Reached**: Configured question limit hit

---

## Key Design Decisions

### 1. State Machine Approach (LangGraph)
**Rationale**: Ensures consistent interview flow, prevents state corruption, enables conditional routing based on interview progress.

### 2. Dual LLM Configuration
**Rationale**: 
- Higher temperature for questions (creativity, variety)
- Lower temperature for evaluation (consistency, accuracy)

### 3. Hierarchical Skill Structure
**Rationale**: Domain → Subdomain → Skill hierarchy enables:
- Organized assessment tracking
- Multi-skill question generation
- Progress calculation at multiple levels

### 4. Persona-Based Question Generation
**Rationale**: 
- Creates personalized, natural interview experience
- Adapts to candidate background automatically
- Maintains conversational flow while assessing skills

### 5. Dynamic Skill Re-Assessment
**Rationale**: 
- Skills can be assessed multiple times
- Scores update based on new evidence
- Prevents premature conclusions

### 6. Priority-Based Topic Selection
**Rationale**: 
- Ensures all topics are covered systematically
- Prevents skill skipping
- Maximizes assessment quality and efficiency

---

## Scalability & Performance

### Current Architecture Supports:
- **Concurrent Sessions**: In-memory state storage per session
- **Persistent Storage**: SQLite database for all interview data
- **API Scalability**: FastAPI async support ready for horizontal scaling
- **LLM Optimization**: Specialized instances reduce token waste


---

## Integration Points

### Configuration:
- **Interview Domains**: Dynamically configured per request (no hardcoding)
- **Max Questions**: Configurable per interview session
- **Personas**: Extensible persona system for different use cases

---

## Security & Reliability

- **Input Validation**: Pydantic models validate all inputs
- **Error Handling**: Try-catch blocks with fallback mechanisms
- **State Validation**: Type checking prevents state corruption
- **Database Transactions**: SQLite transactions ensure data consistency

---

## Summary

Our architecture combines:
- **LangGraph** for intelligent orchestration
- **LLM Intelligence** for adaptive questioning and evaluation
- **State Management** for systematic progress tracking
- **Persona System** for personalized experiences

The result is an automated interview system that makes intelligent decisions at every step, ensuring comprehensive skill assessment while maintaining a natural, conversational flow.


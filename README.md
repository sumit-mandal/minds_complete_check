# Automated Interviewer with LangGraph

A completely automated interview system built with LangGraph that assesses users based on domains, subdomains, and core skills. The system intelligently tracks progress, generates contextual questions, and provides comprehensive scoring.

## Features

- 🤖 **Intelligent Topic Selection**: LLM automatically selects the next topics to cover based on uncovered skills
- 📊 **Smart Progress Tracking**: Tracks which skills have been covered and which remain
- 🎯 **Multi-Skill Assessment**: Single questions can assess multiple skills simultaneously
- 📈 **Dynamic Scoring**: Skills can be re-assessed and scores can increase or decrease based on new evidence
- 🔄 **Adaptive Flow**: The system adapts the interview flow based on user responses
- 📋 **Comprehensive Reporting**: Detailed summaries with strengths, areas for improvement, and recommendations

## Architecture

The system is built using:
- **LangGraph**: For orchestrating the interview flow
- **LangChain**: For LLM integration and structured outputs
- **FastAPI**: For REST API endpoints
- **Pydantic**: For data validation and state management
- **Google Gemini**: For LLM capabilities

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

```env
API_KEY=your_google_gemini_api_key_here
```

### 3. Project Structure

```
├── main.py                          # FastAPI application entry point
├── cli_interviewer.py               # CLI interface for testing
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── apis/
│   └── interviewer_api.py          # FastAPI endpoints
└── utils/
    ├── graph_1_interview_domains.py # Interview domains and skills
    ├── graph_3_llm_helper.py       # LLM configuration
    ├── state_manager.py            # State management and data models
    └── interviewer_graph.py        # LangGraph implementation
```

## Usage

### CLI Interface (Recommended for Testing)

Run the interactive CLI interface:

```bash
python cli_interviewer.py
```

The CLI provides:
- Interactive question-answer sessions
- Real-time progress tracking
- Command options (`progress`, `quit`, `help`)
- Detailed evaluation feedback

### API Endpoints

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000` with automatic documentation at `http://localhost:8000/docs`.

#### Core Interview Endpoints

##### 1. Start Interview
```http
POST /api/interviewer/start
Content-Type: application/json

{
  "session_id": "optional_custom_session_id",
  "persona": "MENTOR"  // Optional: MENTOR, COLLEAGUE, or FRIEND
}
```

**Response:**
```json
{
  "session_id": "session_abc123",
  "current_question": "Describe a challenging situation where you had to maintain clear thinking under pressure...",
  "target_skills": ["Clarity of Thought", "Problem-Solving Confidence"],
  "question_type": "behavioral",
  "progress": {
    "progress_percentage": 0.0,
    "covered_skills": 0,
    "total_skills": 12
  }
}
```

##### 2. Submit Response
```http
POST /api/interviewer/submit
Content-Type: application/json

{
  "user_response": "Your detailed response here",
  "session_id": "your_session_id"
}
```

**Response (Interview Continuing):**
```json
{
  "interview_complete": false,
  "current_question": "Tell me about a time when you had to build trust with someone new...",
  "target_skills": ["Trust Initiation", "Emotional Adaptability"],
  "question_type": "situational",
  "progress": {
    "progress_percentage": 16.7,
    "covered_skills": 2,
    "total_skills": 12
  },
  "last_evaluation": {
    "skill_scores": {
      "Clarity of Thought": 7.5,
      "Problem-Solving Confidence": 8.0
    },
    "confidence_level": 0.85,
    "reasoning": "Strong demonstration of maintaining focus under pressure...",
    "skills_covered": ["Clarity of Thought", "Problem-Solving Confidence"]
  },
  "question_number": 2,
  "max_questions": 7
}
```

**Response (Interview Complete):**
```json
{
  "interview_complete": true,
  "summary": {
    "total_skills_assessed": 12,
    "average_score": 7.2,
    "strengths": ["Problem-Solving Confidence", "Emotional Adaptability"],
    "areas_for_improvement": ["Trust Maintenance", "Mood Consistency"],
    "recommendations": ["Focus on building long-term relationships..."]
  },
  "final_results": {
    "skill_scores": {
      "Clarity of Thought": 7.5,
      "Problem-Solving Confidence": 8.0,
      "Trust Initiation": 6.5
    },
    "overall_assessment": "Strong candidate with room for growth in relational skills"
  },
  "completion_reason": "All skills assessed"
}
```

##### 3. Get Progress
```http
GET /api/interviewer/progress/{session_id}
```

**Response:**
```json
{
  "progress": {
    "progress_percentage": 50.0,
    "covered_skills": 6,
    "total_skills": 12,
    "current_question_number": 4,
    "max_questions": 7
  }
}
```

##### 4. Get Results
```http
GET /api/interviewer/results/{session_id}
```

**Response:**
```json
{
  "results": {
    "skill_scores": {
      "Clarity of Thought": 7.5,
      "Problem-Solving Confidence": 8.0
    },
    "assessment_history": [
      {
        "skill": "Clarity of Thought",
        "score": 7.5,
        "question_number": 1,
        "reasoning": "Demonstrated clear thinking under pressure"
      }
    ]
  }
}
```

##### 5. Reset Interview
```http
POST /api/interviewer/reset
```

**Response:**
```json
{
  "message": "Interview reset successfully"
}
```

##### 6. Health Check
```http
GET /api/interviewer/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### Database & Analytics Endpoints

##### 7. Get All Sessions
```http
GET /api/interviewer/sessions
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "session_abc123",
      "created_at": "2024-01-15T10:00:00.000Z",
      "status": "completed",
      "total_questions": 5,
      "final_score": 7.2
    }
  ]
}
```

##### 8. Get Session Data
```http
GET /api/interviewer/sessions/{session_id}
```

**Response:**
```json
{
  "session": {
    "session_id": "session_abc123",
    "created_at": "2024-01-15T10:00:00.000Z",
    "status": "completed",
    "total_questions": 5,
    "final_score": 7.2
  },
  "responses": [
    {
      "question_number": 1,
      "question": "Describe a challenging situation...",
      "user_response": "In my previous role...",
      "evaluation": {
        "skill_scores": {"Clarity of Thought": 7.5},
        "reasoning": "Strong demonstration..."
      }
    }
  ],
  "final_results": {
    "skill_scores": {"Clarity of Thought": 7.5},
    "overall_assessment": "Strong candidate..."
  },
  "conversation_summary": "The candidate demonstrated strong problem-solving skills..."
}
```

##### 9. Get Statistics
```http
GET /api/interviewer/statistics
```

**Response:**
```json
{
  "statistics": {
    "total_sessions": 25,
    "completed_sessions": 23,
    "average_completion_time": "12.5 minutes",
    "average_final_score": 7.1,
    "most_assessed_skills": ["Problem-Solving Confidence", "Clarity of Thought"],
    "completion_rate": 0.92
  }
}
```

#### Error Handling

The API returns standard HTTP status codes:

- **200**: Success
- **400**: Bad Request (e.g., empty user response)
- **404**: Not Found (e.g., session not found)
- **500**: Internal Server Error

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

#### CORS Configuration

The API is configured with CORS middleware to allow frontend integration:

```javascript
// CORS is enabled for all origins
// Frontend can make requests from any domain
// Credentials are allowed
// All HTTP methods and headers are permitted
```

#### Frontend Integration Example

```javascript
// Start an interview
const startInterview = async () => {
  const response = await fetch('http://localhost:8000/api/interviewer/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: 'my-custom-session-id',
      persona: 'MENTOR'
    })
  });
  return await response.json();
};

// Submit a response
const submitResponse = async (sessionId, userResponse) => {
  const response = await fetch('http://localhost:8000/api/interviewer/submit', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      user_response: userResponse
    })
  });
  return await response.json();
};

// Get progress
const getProgress = async (sessionId) => {
  const response = await fetch(`http://localhost:8000/api/interviewer/progress/${sessionId}`);
  return await response.json();
};
```

## Interview Domains

The system assesses skills across multiple domains:

### Security Domain
- **Cognitive Security**
  - Clarity of Thought
  - Problem-Solving Confidence
- **Emotional Security**
  - Self-Soothing Capacity
  - Emotional Adaptability
- **Relational Security**
  - Trust Initiation
  - Trust Maintenance

### Stability Domain
- **Cognitive Stability**
  - Adaptive Consistency
  - Decision-Making Consistency
- **Emotional Stability**
  - Mood Consistency
  - Recovery Consistency
- **Relational Stability**
  - Interactional Reliability
  - Connection Consistency

## How It Works

### 1. Topic Selection
The LLM analyzes uncovered skills and selects the most appropriate topics to assess next, considering:
- Skills that haven't been assessed
- Logical grouping of related skills
- Difficulty levels and flow
- Efficiency in covering multiple skills per question

### 2. Question Generation
For selected skills, the system generates comprehensive questions that:
- Assess multiple skills simultaneously
- Are behavioral or situational in nature
- Request specific examples and experiences
- Are open-ended for detailed responses

### 3. Response Evaluation
Each response is evaluated to:
- Score each target skill (0-10 scale)
- Provide detailed reasoning
- Determine if follow-up questions are needed
- Track which skills were adequately covered

### 4. State Management
The system maintains detailed state including:
- Skill coverage status
- Current scores and assessment history
- Interview progress
- User response history

### 5. Dynamic Scoring
Skills can be re-assessed throughout the interview:
- Initial assessments set baseline scores
- Subsequent assessments can increase or decrease scores
- Scores are averaged when skills are assessed multiple times
- Assessment history is maintained for transparency

## Example Interview Flow

1. **Start**: System selects initial skills to assess
2. **Question**: "Describe a time when you had to adapt to a major change at work while maintaining your emotional balance."
3. **Assessment**: Evaluates Adaptive Consistency, Mood Consistency, and Emotional Adaptability
4. **Progress**: Updates scores and marks skills as covered
5. **Next**: System selects remaining uncovered skills
6. **Continue**: Process repeats until all skills are assessed
7. **Summary**: Comprehensive report with scores, strengths, and recommendations

## API Response Examples

### Start Interview Response
```json
{
  "session_id": "session_abc123",
  "current_question": "Describe a challenging situation where you had to maintain clear thinking under pressure...",
  "target_skills": ["Clarity of Thought", "Problem-Solving Confidence"],
  "question_type": "behavioral",
  "progress": {
    "progress_percentage": 0.0,
    "covered_skills": 0,
    "total_skills": 12
  }
}
```

### Submit Response Response
```json
{
  "interview_complete": false,
  "current_question": "Tell me about a time when you had to build trust with someone new...",
  "target_skills": ["Trust Initiation", "Emotional Adaptability"],
  "question_type": "situational",
  "progress": {
    "progress_percentage": 16.7,
    "covered_skills": 2,
    "total_skills": 12
  },
  "last_evaluation": {
    "skill_scores": {
      "Clarity of Thought": 7.5,
      "Problem-Solving Confidence": 8.0
    },
    "confidence_level": 0.85,
    "reasoning": "Strong demonstration of maintaining focus under pressure...",
    "skills_covered": ["Clarity of Thought", "Problem-Solving Confidence"]
  }
}
```

## Customization

### Adding New Domains/Skills

Edit `utils/graph_1_interview_domains.py` to add new domains, subdomains, or skills:

```python
INTERVIEW_DOMAINS = {
    "domains": [
        {
            "name": "New Domain",
            "subdomains": [
                {
                    "name": "New Subdomain",
                    "core_skills": [
                        {
                            "name": "New Skill",
                            "knowledge_areas": ["Area 1", "Area 2"],
                            "practical_applications": ["App 1", "App 2"],
                            "level": "Medium"
                        }
                    ]
                }
            ]
        }
    ]
}
```

### Modifying Evaluation Criteria

Update the evaluation prompts in `utils/interviewer_graph.py` to change how responses are scored.

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your Google Gemini API key is set in the `.env` file
2. **Import Errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`
3. **LLM Timeout**: The system includes retry logic, but network issues may cause delays

### Debug Mode

For debugging, you can add logging to the LangGraph nodes in `utils/interviewer_graph.py`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

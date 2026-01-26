# API Documentation

## Base URL
**Base URL**: `https://api.mirrorminds.ai`

All endpoints are prefixed with `/interviewer`

**Example**: `POST https://api.mirrorminds.ai/interviewer/start`

---

## Table of Contents
1. [Interview Lifecycle](#interview-lifecycle)
2. [Session Management](#session-management)
3. [Results & Reports](#results--reports)
4. [User Data](#user-data)
5. [WebSocket Streaming](#websocket-streaming)
6. [Utility Endpoints](#utility-endpoints)

---

## Interview Lifecycle

### 1. Start Interview
**Endpoint**: `POST https://api.mirrorminds.ai/interviewer/start`

**Purpose**: Creates a new interview session and returns the first question.

**Request Body**:
```json
{
  "session_id": "optional-uuid-string",  // Optional: reuse existing session
  "user_id": "user123",                  // Required: unique user identifier
  "name": "John Doe",                    // Required: candidate name
  "persona": "MENTOR",                   // Optional: interviewer style (default: "MENTOR")
                                         // Options: MENTOR, COLLEAGUE, PROFESSOR, COACH, THERAPIST
  "candidate_persona": "PROFESSIONAL",  // Optional: candidate type (default: "PROFESSIONAL")
                                         // Options: STUDENT, PROFESSIONAL
  "interview_domains": {                 // Required: skills to assess
    "Python": {
      "Data Structures": ["Lists", "Dictionaries", "Sets"],
      "OOP": ["Classes", "Inheritance"]
    },
    "JavaScript": {
      "Async": ["Promises", "Async/Await"]
    }
  },
  "max_questions": 10,                   // Required: maximum questions in interview
  "pronoun": "he",                       // Optional: candidate pronoun
  "career_level": "Senior",              // Optional: career level
  "industry": "Tech"                     // Optional: industry
}
```

**Response** (200 OK):
```json
{
  "session_id": "uuid-string",
  "current_question": "Tell me about your experience with Python...",
  "target_skills": ["Lists", "Dictionaries"],
  "question_type": "technical",
  "progress": {
    "total_skills": 5,
    "covered_skills": 0,
    "progress_percentage": 0.0
  },
  "max_questions": 10,
  "persona": "MENTOR",
  "industry": "Tech",
  "name": "John Doe",
  "pronoun": "he",
  "start_time": "2024-01-15T10:30:00Z",
  "duration_seconds": 0
}
```

**Use Case**: Call this when user clicks "Start Interview" button. Store the `session_id` for subsequent API calls.

---

### 2. Submit Response
**Endpoint**: `POST https://api.mirrorminds.ai/interviewer/submit`

**Purpose**: Submits candidate's answer and gets the next question or final results if interview is complete.

**Request Body**:
```json
{
  "user_response": "I have worked with Python lists extensively...",  // Required: candidate's answer
  "session_id": "uuid-string"                                         // Required: session from start_interview
}
```

**Response - Interview In Progress** (200 OK):
```json
{
  "interview_complete": false,
  "current_question": "Can you explain how dictionaries work in Python?",
  "target_skills": ["Dictionaries", "Hash Tables"],
  "question_type": "technical",
  "progress": {
    "total_skills": 5,
    "covered_skills": 2,
    "progress_percentage": 40.0
  },
  "last_evaluation": {
    "scores": {
      "Lists": 8.5,
      "Dictionaries": 7.0
    },
    "reasoning": "Strong understanding of lists..."
  },
  "question_number": 2,
  "max_questions": 10,
  "start_time": "2024-01-15T10:30:00Z",
  "end_time": null,
  "duration_seconds": 45
}
```

**Response - Interview Complete** (200 OK):
```json
{
  "interview_complete": true,
  "summary": {
    "overall_assessment": "Strong candidate...",
    "strengths": ["Python", "Data Structures"],
    "weaknesses": ["Async Programming"]
  },
  "final_results": {
    "domain_scores": {
      "Python": 8.5,
      "JavaScript": 6.0
    },
    "hierarchical_results": {
      "Python": {
        "Data Structures": {
          "Lists": 8.5,
          "Dictionaries": 7.0
        }
      }
    }
  },
  "completion_reason": "max_questions_reached",
  "start_time": "2024-01-15T10:30:00Z",
  "end_time": "2024-01-15T10:45:00Z",
  "duration_seconds": 900
}
```

**Use Case**: Call this after user submits each answer. Check `interview_complete` to determine if you should show next question or results page.

**Error Handling**:
- `400 Bad Request`: If `user_response` is empty or missing
- `500 Internal Server Error`: If session processing fails

---

## Session Management

### 3. Get Progress
**Endpoint**: `GET https://api.mirrorminds.ai/interviewer/progress/{session_id}`

**Purpose**: Get current interview progress without submitting a response.

**Path Parameters**:
- `session_id` (string): The interview session ID

**Response** (200 OK):
```json
{
  "progress": {
    "total_skills": 5,
    "covered_skills": 2,
    "progress_percentage": 40.0,
    "questions_asked": 2,
    "max_questions": 10
  }
}
```

**Use Case**: Useful for displaying progress bars or checking interview status.

**Error Handling**:
- `500 Internal Server Error`: If session not found or processing fails

---

### 4. Get Results
**Endpoint**: `GET https://api.mirrorminds.ai/interviewer/results/{session_id}`

**Purpose**: Get current interview results (works even if interview is in progress).

**Path Parameters**:
- `session_id` (string): The interview session ID

**Response** (200 OK):
```json
{
  "results": {
    "domain_scores": {
      "Python": 8.5,
      "JavaScript": 6.0
    },
    "hierarchical_results": {
      "Python": {
        "Data Structures": {
          "Lists": 8.5
        }
      }
    }
  }
}
```

**Use Case**: Display interim results or final results after interview completion.

**Error Handling**:
- `500 Internal Server Error`: If session not found or processing fails

---

### 5. Get Session Data
**Endpoint**: `GET https://api.mirrorminds.ai/interviewer/sessions/{session_id}`

**Purpose**: Get complete session data including all responses, evaluations, and final results.

**Path Parameters**:
- `session_id` (string): The interview session ID

**Response** (200 OK):
```json
{
  "session": {
    "session_id": "uuid-string",
    "user_id": "user123",
    "max_questions": 10,
    "start_time": "2024-01-15T10:30:00Z",
    "end_time": "2024-01-15T10:45:00Z",
    "status": "completed"
  },
  "responses": [
    {
      "question": "Tell me about Python lists...",
      "user_response": "I have worked with Python lists...",
      "evaluation": {
        "scores": {"Lists": 8.5},
        "reasoning": "Strong understanding..."
      },
      "timestamp": "2024-01-15T10:30:15Z"
    }
  ],
  "final_results": {
    "domain_scores": {...},
    "hierarchical_results": {...}
  },
  "conversation_summary": "The interview covered..."
}
```

**Use Case**: Load full interview history for review pages or detailed analysis.

**Error Handling**:
- `404 Not Found`: If session doesn't exist
- `500 Internal Server Error`: If database query fails

---

### 6. Get All Sessions
**Endpoint**: `GET https://api.mirrorminds.ai/interviewer/sessions`

**Purpose**: Get list of all interview sessions (useful for admin dashboards).

**Response** (200 OK):
```json
{
  "sessions": [
    {
      "session_id": "uuid-1",
      "user_id": "user123",
      "max_questions": 10,
      "start_time": "2024-01-15T10:30:00Z",
      "status": "completed"
    },
    {
      "session_id": "uuid-2",
      "user_id": "user456",
      "max_questions": 15,
      "start_time": "2024-01-15T11:00:00Z",
      "status": "in_progress"
    }
  ]
}
```

**Use Case**: Display list of all interviews in admin panel or user dashboard.

**Error Handling**:
- `500 Internal Server Error`: If database query fails

---

## Results & Reports

### 7. Get Persona Trait Report
**Endpoint**: `GET https://api.mirrorminds.ai/interviewer/persona-trait/{session_id}`

**Purpose**: Get a detailed personality/trait analysis report based on interview responses.

**Path Parameters**:
- `session_id` (string): The interview session ID

**Response** (200 OK):
```json
{
  "personality_traits": {
    "communication_style": "clear and concise",
    "problem_solving_approach": "analytical",
    "confidence_level": "high"
  },
  "strengths": ["Technical knowledge", "Communication"],
  "recommendations": ["Work on async programming concepts"]
}
```

**Use Case**: Display personality insights and trait analysis on results page.

**Error Handling**:
- `404 Not Found`: If session doesn't exist or has no results
- `500 Internal Server Error`: If report generation fails

---

### 8. Get Domains Summary
**Endpoint**: `GET https://api.mirrorminds.ai/interviewer/domains-summary/{session_id}`

**Purpose**: Get a comprehensive summary of all domains covered in the interview with detailed analysis.

**Path Parameters**:
- `session_id` (string): The interview session ID

**Response** (200 OK):
```json
{
  "session_id": "uuid-string",
  "domain_summary": {
    "Python": {
      "overall_score": 8.5,
      "summary": "Strong understanding of Python fundamentals...",
      "subdomains": {
        "Data Structures": {
          "score": 8.0,
          "summary": "Good grasp of lists and dictionaries..."
        }
      }
    }
  },
  "cached": false  // true if summary was retrieved from cache
}
```

**Use Case**: Display detailed domain-by-domain breakdown on results page.

**Error Handling**:
- `404 Not Found`: If session doesn't exist or interview not completed
- `500 Internal Server Error`: If summary generation fails

---

### 9. Get Statistics
**Endpoint**: `GET https://api.mirrorminds.ai/interviewer/statistics`

**Purpose**: Get overall statistics across all interview sessions.

**Response** (200 OK):
```json
{
  "statistics": {
    "total_sessions": 150,
    "completed_sessions": 120,
    "average_duration_seconds": 900,
    "average_score": 7.5,
    "top_domains": ["Python", "JavaScript", "React"]
  }
}
```

**Use Case**: Display analytics dashboard or system-wide statistics.

**Error Handling**:
- `500 Internal Server Error`: If statistics calculation fails

---

## User Data

### 10. Get User Interviews
**Endpoint**: `GET https://api.mirrorminds.ai/interviewer/user/{user_id}/interviews`

**Purpose**: Get all interview sessions for a specific user.

**Path Parameters**:
- `user_id` (string): The user identifier

**Response** (200 OK):
```json
{
  "user_id": "user123",
  "total_sessions": 5,
  "interviews": [
    {
      "session_id": "uuid-1",
      "start_time": "2024-01-15T10:30:00Z",
      "end_time": "2024-01-15T10:45:00Z",
      "status": "completed",
      "max_questions": 10,
      "final_score": 8.5
    },
    {
      "session_id": "uuid-2",
      "start_time": "2024-01-16T14:00:00Z",
      "status": "in_progress",
      "max_questions": 15
    }
  ]
}
```

**Use Case**: Display user's interview history on their profile page.

**Error Handling**:
- Returns empty array if user has no interviews
- `500 Internal Server Error`: If database query fails

---

## WebSocket Streaming

### 11. Submit Response Stream
**Endpoint**: `WS wss://api.mirrorminds.ai/interviewer/submit/stream`

**Purpose**: WebSocket endpoint for real-time streaming of interview responses (evaluation, questions, summaries).

**Connection**: Connect to WebSocket endpoint

**Initial Message** (JSON):
```json
{
  "user_response": "I have worked with Python lists...",
  "session_id": "uuid-string"
}
```

**Stream Messages** (received as JSON):
```json
// Evaluation streaming
{
  "type": "evaluation",
  "content": "Strong understanding of..."
}

// Question streaming
{
  "type": "question",
  "content": "Can you explain..."
}

// Summary streaming (when complete)
{
  "type": "summary",
  "content": "Overall assessment..."
}

// Final results
{
  "type": "final_results",
  "data": {
    "domain_scores": {...},
    "hierarchical_results": {...}
  }
}

// Error
{
  "type": "error",
  "message": "Session not found"
}
```

**Use Case**: Use this for real-time UI updates as the AI processes responses. Better UX than polling the REST endpoint.

**Error Handling**:
- Connection closes with error message if `user_response` or `session_id` missing
- Connection closes if session not found
- Connection closes if `user_response` is empty

---

## Utility Endpoints

### 12. Reset Interview
**Endpoint**: `POST https://api.mirrorminds.ai/interviewer/reset`

**Purpose**: Reset the interview state (clears all in-memory state). **Note**: This is a global reset, use with caution.

**Request Body**: None

**Response** (200 OK):
```json
{
  "message": "Interview reset successfully"
}
```

**Use Case**: Admin/debugging endpoint. Not typically used by frontend.

**Error Handling**:
- `500 Internal Server Error`: If reset fails

---

### 13. Health Check
**Endpoint**: `GET https://api.mirrorminds.ai/interviewer/health`

**Purpose**: Check if the API is running and healthy.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Use Case**: Health monitoring, load balancer checks, or frontend initialization checks.

---

### 14. Calculate Duration
**Endpoint**: `POST https://api.mirrorminds.ai/interviewer/calculate-duration`

**Purpose**: Calculate actual assessment duration by subtracting pause times from the total assessment duration.

**Request Body**:
```json
{
  "assessment_start_time": "2024-01-15T10:30:00Z",  // Required: ISO format datetime string
  "assessment_end_time": "2024-01-15T10:45:00Z",    // Required: ISO format datetime string
  "pauses": [                                        // Required: List of pause periods
    {
      "pause_start_time": "2024-01-15T10:35:00Z",  // ISO format datetime string
      "pause_end_time": "2024-01-15T10:37:00Z"     // ISO format datetime string
    },
    {
      "pause_start_time": "2024-01-15T10:40:00Z",
      "pause_end_time": "2024-01-15T10:42:00Z"
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "assessment_start_time": "2024-01-15T10:30:00Z",
  "assessment_end_time": "2024-01-15T10:45:00Z",
  "total_duration_seconds": 900,        // Total time from start to end
  "pause_duration_seconds": 240,         // Sum of all pause durations
  "actual_duration_seconds": 660,        // Total duration minus pauses
  "number_of_pauses": 2                  // Count of pause periods
}
```

**Use Case**: Calculate the actual time spent on an assessment by excluding periods when the user was paused (e.g., bathroom breaks, technical issues). Useful for accurate time tracking and reporting.

**Error Handling**:
- `400 Bad Request`: 
  - If assessment end time is not after start time
  - If pause end time is not after pause start time
  - If pause periods are outside the assessment time range
  - If total pause duration exceeds assessment duration
  - If datetime format is invalid (must be ISO format)
- `500 Internal Server Error`: If calculation fails

**Notes**:
- All datetime strings must be in ISO 8601 format (e.g., `"2024-01-15T10:30:00Z"` or `"2024-01-15T10:30:00+00:00"`)
- Pause periods must be completely within the assessment time range
- The `actual_duration_seconds` will always be non-negative (total duration minus pauses)

---

## Common Response Patterns

### Success Response
All successful responses return `200 OK` with JSON body matching the response model.

### Error Response Format
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes
- `200 OK`: Request successful
- `400 Bad Request`: Invalid request data (missing fields, empty values)
- `404 Not Found`: Resource (session, user) not found
- `500 Internal Server Error`: Server-side error

---

## Frontend Integration Tips

### 1. Session Management
- Store `session_id` from `/start` response in local storage or state
- Use `session_id` for all subsequent API calls
- Handle session expiration gracefully

### 2. Polling vs WebSocket
- Use REST endpoints (`https://api.mirrorminds.ai/interviewer/submit`) for simple request-response flow
- Use WebSocket (`wss://api.mirrorminds.ai/interviewer/submit/stream`) for real-time streaming updates
- WebSocket provides better UX for long-running evaluations

### 3. Error Handling
- Always check `interview_complete` flag in `https://api.mirrorminds.ai/interviewer/submit` response
- Handle `404` errors by redirecting to start page
- Show user-friendly error messages from `detail` field

### 4. Progress Tracking
- Use `https://api.mirrorminds.ai/interviewer/progress/{session_id}` to update progress bars
- Poll this endpoint periodically if needed (or use WebSocket)
- Display `progress_percentage` and `question_number` to users

### 5. Results Display
- Use `https://api.mirrorminds.ai/interviewer/results/{session_id}` for current results
- Use `https://api.mirrorminds.ai/interviewer/domains-summary/{session_id}` for detailed breakdown
- Use `https://api.mirrorminds.ai/interviewer/persona-trait/{session_id}` for personality insights
- Cache results to avoid unnecessary API calls

### 6. User History
- Use `https://api.mirrorminds.ai/interviewer/user/{user_id}/interviews` to show interview history
- Link each interview to `https://api.mirrorminds.ai/interviewer/sessions/{session_id}` for details
- Display status badges (completed, in_progress)

---

## Example Frontend Flow

```javascript
// 1. Start Interview
const startResponse = await fetch('https://api.mirrorminds.ai/interviewer/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user123',
    name: 'John Doe',
    interview_domains: { /* domains */ },
    max_questions: 10
  })
});
const { session_id, current_question } = await startResponse.json();

// 2. Display first question
displayQuestion(current_question);

// 3. Submit response
const submitResponse = await fetch('https://api.mirrorminds.ai/interviewer/submit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: session_id,
    user_response: userAnswer
  })
});
const result = await submitResponse.json();

// 4. Handle response
if (result.interview_complete) {
  // Show results page
  displayResults(result.final_results);
} else {
  // Show next question
  displayQuestion(result.current_question);
  updateProgress(result.progress);
}
```

---

## Notes for Frontend Developers

1. **Session IDs**: Always use UUIDs returned from the API. Don't generate your own.

2. **Persona Options**: 
   - Interviewer: `MENTOR`, `COLLEAGUE`, `PROFESSOR`, `COACH`, `THERAPIST`
   - Candidate: `STUDENT`, `PROFESSIONAL`

3. **Interview Domains Structure**: 
   - Nested object: `Domain → Subdomain → Array of Skills`
   - Example: `{"Python": {"Data Structures": ["Lists", "Dictionaries"]}}`

4. **Progress Calculation**: 
   - `progress_percentage` is calculated automatically
   - Based on skills covered vs total skills

5. **Completion Reasons**:
   - `"max_questions_reached"`: Hit question limit
   - `"progress_complete"`: All skills assessed
   - `"user_terminated"`: User ended early (if implemented)

6. **Caching**: 
   - Domain summaries are cached after first generation
   - Check `cached: true` in response to know if it's fresh

7. **Timestamps**: 
   - All timestamps are ISO 8601 format in UTC
   - Format: `"2024-01-15T10:30:00Z"`

---

## Support

For questions or issues, refer to the main `ARCHITECTURE.md` file for system design details.

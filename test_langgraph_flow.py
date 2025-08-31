#!/usr/bin/env python3
"""
Test script to demonstrate the LangGraph interview flow
"""

import json
from utils.langgraph_interviewer import LangGraphInterviewer

def test_langgraph_interview():
    """Test the LangGraph interview flow"""
    
    print("=== LangGraph Interview Flow Test ===\n")
    
    # Create interviewer
    interviewer = LangGraphInterviewer(max_questions=2)
    
    # Start interview
    print("1. Starting interview...")
    result = interviewer.start_interview("test_session_001")
    print(f"Session ID: {result['session_id']}")
    print(f"Question: {result['current_question']}")
    print(f"Question Type: {result['question_type']}")
    print(f"Target Skills: {result['target_skills']}")
    print(f"Progress: {result['progress']['progress_percentage']:.1f}%")
    print()
    
    # Submit first response
    print("2. Submitting first response...")
    response1 = "Hi, I'm a software engineer with 5 years of experience in Python development. I've worked on various projects including web applications, data analysis, and machine learning systems. I'm passionate about clean code and solving complex problems."
    
    result = interviewer.submit_response(response1, result['session_id'])
    print(f"Interview Complete: {result['interview_complete']}")
    
    if not result['interview_complete']:
        print(f"Next Question: {result['current_question']}")
        print(f"Question Type: {result['question_type']}")
        print(f"Target Skills: {result['target_skills']}")
        print(f"Progress: {result['progress']['progress_percentage']:.1f}%")
        print(f"Question Number: {result['question_number']}/{result['max_questions']}")
        print()
        
        # Submit second response
        print("3. Submitting second response...")
        response2 = "In my previous role, I led a team of 3 developers to build a real-time analytics dashboard. We used React for the frontend and Python Flask for the backend. I implemented the data processing pipeline using pandas and numpy, and we achieved 99.9% uptime. The project was delivered on time and under budget."
        
        result = interviewer.submit_response(response2, "test_session_001")
        print(f"Interview Complete: {result['interview_complete']}")
    
    # Show final results
    if result['interview_complete']:
        print("=== Interview Complete ===")
        print(f"Completion Reason: {result['completion_reason']}")
        print(f"Final Results: {json.dumps(result['final_results'], indent=2)}")
        print(f"Summary: {json.dumps(result['summary'], indent=2)}")

if __name__ == "__main__":
    test_langgraph_interview()

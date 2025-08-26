#!/usr/bin/env python3
"""
Example usage of the automated interviewer
"""

import asyncio
from utils.interviewer_graph import AutomatedInterviewer

def example_interview():
    """Example of a complete interview session"""
    
    print("🚀 Starting Example Interview Session")
    print("=" * 50)
    
    # Initialize the interviewer
    interviewer = AutomatedInterviewer()
    
    # Start the interview
    result = interviewer.start_interview("example_session_123")
    
    print(f"📋 Session ID: {result['session_id']}")
    print(f"🤔 First Question: {result['current_question']}")
    print(f"🎯 Target Skills: {', '.join(result['target_skills'])}")
    
    # Example responses for demonstration
    example_responses = [
        "I remember a time when I was leading a project and we had a major deadline approaching. The team was stressed and there were multiple conflicting priorities. I stayed calm and organized by breaking down the problem into smaller, manageable tasks. I communicated clearly with each team member about their responsibilities and created a timeline that everyone could follow. When unexpected issues arose, I maintained my composure and helped the team adapt our approach. We ended up delivering the project on time and with high quality. This experience taught me the importance of staying focused under pressure and the value of clear communication.",
        
        "Building trust with new people is something I've learned to do effectively. I start by being genuinely interested in their perspective and showing that I'm listening. I share appropriate information about myself to create a foundation of mutual understanding. I'm consistent in my actions and follow through on commitments. For example, when I joined a new team last year, I made sure to attend all meetings on time, contribute meaningfully to discussions, and offer help to colleagues when they needed it. Over time, this consistency helped establish trust and strong working relationships.",
        
        "I've learned to manage my emotions effectively, especially in professional settings. When I feel stressed or frustrated, I take a moment to pause and breathe deeply. I remind myself that emotions are temporary and that I can choose how to respond. I also practice reframing situations to see them from different perspectives. For instance, when I receive critical feedback, I try to view it as an opportunity for growth rather than a personal attack. This mindset shift helps me stay calm and constructive even in challenging situations."
    ]
    
    # Process each response
    for i, response in enumerate(example_responses, 1):
        print(f"\n📝 Response {i}: {response[:100]}...")
        
        # Submit the response
        result = interviewer.submit_response(response, result['session_id'])
        
        if result["interview_complete"]:
            print("\n🎉 Interview Complete!")
            print("=" * 50)
            
            # Display final results
            final_results = result["final_results"]
            summary = result["summary"]
            
            print(f"🏆 Overall Score: {final_results['overall_score']:.1f}/10")
            print(f"📊 Total Responses: {final_results['total_responses']}")
            print(f"📈 Progress: {final_results['interview_progress']:.1f}%")
            
            print("\n🎯 Skill Scores:")
            for skill, score in final_results["skill_scores"].items():
                print(f"  {skill}: {score:.1f}/10")
            
            if summary.get("strengths"):
                print(f"\n✅ Key Strengths:")
                for strength in summary["strengths"][:3]:  # Show top 3
                    print(f"  • {strength}")
            
            if summary.get("recommendations"):
                print(f"\n💡 Recommendations:")
                for rec in summary["recommendations"][:3]:  # Show top 3
                    print(f"  • {rec}")
            
            break
        else:
            print(f"📊 Progress: {result['progress']['progress_percentage']:.1f}%")
            print(f"🎯 Next Target Skills: {', '.join(result['target_skills'])}")
            print(f"🤔 Next Question: {result['current_question']}")
            
            # Show evaluation
            if result.get("last_evaluation"):
                eval_data = result["last_evaluation"]
                print(f"📊 Last Evaluation:")
                for skill, score in eval_data["skill_scores"].items():
                    print(f"  {skill}: {score}/10")

def example_api_usage():
    """Example of how to use the API endpoints"""
    
    print("\n🌐 API Usage Example")
    print("=" * 50)
    
    print("""
To use the API endpoints:

1. Start the server:
   uvicorn main:app --reload

2. Start an interview:
   curl -X POST "http://localhost:8000/api/interviewer/start" \\
        -H "Content-Type: application/json" \\
        -d '{"session_id": "my_session"}'

3. Submit a response:
   curl -X POST "http://localhost:8000/api/interviewer/submit" \\
        -H "Content-Type: application/json" \\
        -d '{"user_response": "Your response here", "session_id": "my_session"}'

4. Get progress:
   curl "http://localhost:8000/api/interviewer/progress/my_session"

5. Get results:
   curl "http://localhost:8000/api/interviewer/results/my_session"
    """)

def main():
    """Main function"""
    print("📚 Automated Interviewer - Example Usage")
    print("=" * 50)
    
    # Run the example interview
    example_interview()
    
    # Show API usage
    example_api_usage()
    
    print("\n✨ Example completed!")
    print("Try running 'python cli_interviewer.py' for interactive testing.")

if __name__ == "__main__":
    main()

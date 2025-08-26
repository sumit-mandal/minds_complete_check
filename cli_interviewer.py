#!/usr/bin/env python3
"""
CLI interface for the automated interviewer
"""

import asyncio
import json
from utils.simple_interviewer import SimpleAutomatedInterviewer

class CLIInterviewer:
    def __init__(self):
        self.interviewer = SimpleAutomatedInterviewer()
        self.session_id = None
    
    def start_interview(self):
        """Start a new interview session"""
        print("🤖 Welcome to the Automated Interviewer!")
        print("=" * 50)
        
        # Start the interview
        result = self.interviewer.start_interview()
        self.session_id = result["session_id"]
        
        print(f"📋 Session ID: {self.session_id}")
        print(f"📊 Progress: {result['progress']['progress_percentage']:.1f}% complete")
        print(f"❓ Question Type: {result['question_type']}")
        print("\n" + "=" * 50)
        print(f"🤔 Question: {result['current_question']}")
        print("=" * 50)
        
        return result
    
    def submit_response(self, user_response: str):
        """Submit a user response"""
        if not self.session_id:
            print("❌ No active interview session. Please start an interview first.")
            return None
        
        print(f"\n📝 Your Response: {user_response}")
        print("🔄 Processing...")
        
        result = self.interviewer.submit_response(user_response, self.session_id)
        
        if result["interview_complete"]:
            print("\n🎉 Interview Complete!")
            print("=" * 50)
            self.display_summary(result)
            return None
        else:
            print(f"\n📊 Progress: {result['progress']['progress_percentage']:.1f}% complete")
            print(f"🎯 Target Skills: {', '.join(result['target_skills'])}")
            print(f"❓ Question Type: {result['question_type']}")
            print("\n" + "=" * 50)
            print(f"🤔 Question: {result['current_question']}")
            print("=" * 50)
            
            # Show evaluation if available
            if result.get("last_evaluation"):
                self.display_evaluation(result["last_evaluation"])
            
            return result
    
    def display_evaluation(self, evaluation: dict):
        """Display the evaluation results"""
        print("\n📊 Last Response Evaluation:")
        print("-" * 30)
        for skill, score in evaluation["skill_scores"].items():
            print(f"  {skill}: {score}/10")
        print(f"  Confidence: {evaluation['confidence_level']:.2f}")
        if evaluation.get("reasoning"):
            print(f"  Reasoning: {evaluation['reasoning'][:100]}...")
    
    def display_summary(self, result: dict):
        """Display the final interview summary"""
        summary = result["summary"]
        final_results = result["final_results"]
        
        print(f"🏆 Overall Score: {final_results['overall_score']:.1f}/10")
        print("\n📈 Domain Scores:")
        for domain, score in final_results["domain_scores"].items():
            print(f"  {domain}: {score:.1f}/10")
        
        print("\n🎯 Skill Scores:")
        for skill, score in final_results["skill_scores"].items():
            print(f"  {skill}: {score:.1f}/10")
        
        if summary.get("strengths"):
            print(f"\n✅ Strengths:")
            for strength in summary["strengths"]:
                print(f"  • {strength}")
        
        if summary.get("areas_for_improvement"):
            print(f"\n🔧 Areas for Improvement:")
            for area in summary["areas_for_improvement"]:
                print(f"  • {area}")
        
        if summary.get("recommendations"):
            print(f"\n💡 Recommendations:")
            for rec in summary["recommendations"]:
                print(f"  • {rec}")
    
    def show_progress(self):
        """Show current interview progress"""
        if not self.session_id:
            print("❌ No active interview session.")
            return
        
        progress = self.interviewer.get_progress()
        print(f"\n📊 Interview Progress: {progress['progress_percentage']:.1f}%")
        print(f"✅ Covered Skills: {progress['covered_skills']}/{progress['total_skills']}")
        
        print("\n📋 Domain Progress:")
        for domain in progress["domains_progress"]:
            print(f"  {domain['name']}: {'✅' if domain['covered'] else '⏳'}")
            for subdomain in domain["subdomains_progress"]:
                print(f"    {subdomain['name']}: {'✅' if subdomain['covered'] else '⏳'}")
                for skill in subdomain["skills_progress"]:
                    status = "✅" if skill["covered"] else "⏳"
                    score = f"({skill['score']:.1f})" if skill["covered"] else ""
                    print(f"      {skill['name']}: {status} {score}")
    
    def run_interactive(self):
        """Run the interactive interview"""
        try:
            # Start the interview
            self.start_interview()
            
            while True:
                print("\n💬 Enter your response (or type 'progress', 'quit', 'help'):")
                user_input = input("> ").strip()
                
                if user_input.lower() == 'quit':
                    print("👋 Goodbye!")
                    break
                elif user_input.lower() == 'progress':
                    self.show_progress()
                    continue
                elif user_input.lower() == 'help':
                    print("\n📖 Available commands:")
                    print("  - Type your response to answer the question")
                    print("  - 'progress': Show current interview progress")
                    print("  - 'quit': End the interview")
                    print("  - 'help': Show this help message")
                    continue
                elif not user_input:
                    print("❌ Please provide a response.")
                    continue
                
                # Submit the response
                result = self.submit_response(user_input)
                if result is None:  # Interview complete
                    break
                
        except KeyboardInterrupt:
            print("\n\n👋 Interview interrupted. Goodbye!")
        except Exception as e:
            print(f"\n❌ An error occurred: {str(e)}")

def main():
    """Main function"""
    print("🚀 Starting Automated Interviewer CLI...")
    
    cli = CLIInterviewer()
    cli.run_interactive()

if __name__ == "__main__":
    main()

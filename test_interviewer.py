#!/usr/bin/env python3
"""
Test script for the automated interviewer
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_imports():
    """Test that all modules can be imported"""
    try:
        from utils.state_manager import StateManager
        from utils.interviewer_graph import AutomatedInterviewer
        from utils.graph_1_interview_domains import INTERVIEW_DOMAINS
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_state_manager():
    """Test the state manager functionality"""
    try:
        from utils.state_manager import StateManager
        from utils.graph_1_interview_domains import INTERVIEW_DOMAINS
        
        # Initialize state manager
        state_manager = StateManager(INTERVIEW_DOMAINS)
        
        # Test getting uncovered skills
        uncovered_skills = state_manager.get_uncovered_skills()
        print(f"✅ State manager initialized with {len(uncovered_skills)} uncovered skills")
        
        # Test getting progress
        progress = state_manager.get_interview_progress()
        print(f"✅ Progress tracking working: {progress['progress_percentage']}% complete")
        
        return True
    except Exception as e:
        print(f"❌ State manager test failed: {e}")
        return False

def test_interviewer_initialization():
    """Test interviewer initialization"""
    try:
        from utils.interviewer_graph import AutomatedInterviewer
        
        # Initialize interviewer
        interviewer = AutomatedInterviewer()
        print("✅ Interviewer initialized successfully")
        
        # Test getting progress
        progress = interviewer.get_progress()
        print(f"✅ Interviewer progress: {progress['progress_percentage']}% complete")
        
        return True
    except Exception as e:
        print(f"❌ Interviewer initialization failed: {e}")
        return False

def test_api_key():
    """Test if API key is configured"""
    api_key = os.getenv("API_KEY")
    if api_key:
        print("✅ API key found")
        return True
    else:
        print("❌ API key not found. Please set API_KEY in your .env file")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Automated Interviewer System")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("API Key Test", test_api_key),
        ("State Manager Test", test_state_manager),
        ("Interviewer Initialization Test", test_interviewer_initialization),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
        print("\nNext steps:")
        print("1. Run 'python cli_interviewer.py' for interactive testing")
        print("2. Run 'uvicorn main:app --reload' to start the API server")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for Job Application Assistant agents.
This script tests the functionality of the specialized agents.
"""

import os
import json
from pathlib import Path
from agents.job_analyzer_agent import JobAnalyzerAgent
from agents.ats_optimization_agent import ATSOptimizationAgent
from agents.company_researcher_agent import CompanyResearcherAgent
from agents.resume_reviewer_agent import ResumeReviewerAgent

def read_file(file_path):
    """Read a file and return its contents."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def save_json(data, file_path):
    """Save data as a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def test_job_analyzer_agent():
    """Test the Job Analyzer Agent."""
    print("\n=== Testing Job Analyzer Agent ===")
    
    # Create the agent
    agent = JobAnalyzerAgent()
    
    # Read the sample job description
    job_description = read_file("sample_job.html")
    
    # Analyze the job posting
    print("Analyzing job posting...")
    result = agent.analyze_job_posting(job_description)
    
    # Save the result
    output_path = "test_results/job_analyzer_result.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    save_json(result, output_path)
    
    print(f"Job analysis complete. Results saved to {output_path}")
    
    # Print a summary
    print("\nJob Analysis Summary:")
    print(f"Job Title: {result.get('job_title', 'N/A')}")
    print(f"Company: {result.get('company_name', 'N/A')}")
    print(f"Required Skills: {', '.join(result.get('required_skills', []))[:100]}...")
    print(f"ATS Keywords: {', '.join(result.get('ats_keywords', []))[:100]}...")

def test_ats_optimization_agent():
    """Test the ATS Optimization Agent."""
    print("\n=== Testing ATS Optimization Agent ===")
    
    # Create the agent
    agent = ATSOptimizationAgent()
    
    # Read the sample job description and resume
    job_description = read_file("sample_job.html")
    resume = read_file("brian_resume.txt")
    
    # Optimize for ATS
    print("Optimizing resume for ATS...")
    result = agent.optimize_for_ats(job_description, resume)
    
    # Save the result
    output_path = "test_results/ats_optimization_result.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    save_json(result, output_path)
    
    print(f"ATS optimization complete. Results saved to {output_path}")
    
    # Print a summary
    print("\nATS Optimization Summary:")
    print(f"ATS Score: {result.get('ats_score', 'N/A')}")
    print(f"Keyword Matches: {', '.join(result.get('keyword_matches', []))[:100]}...")
    print(f"Keyword Gaps: {', '.join(result.get('keyword_gaps', []))[:100]}...")

def test_company_researcher_agent():
    """Test the Company Researcher Agent."""
    print("\n=== Testing Company Researcher Agent ===")
    
    # Create the agent
    agent = CompanyResearcherAgent()
    
    # Read the sample job description
    job_description = read_file("sample_job.html")
    
    # Extract company name from job description (simplified)
    company_name = "Example Company"  # Replace with actual extraction logic
    
    # Research the company
    print(f"Researching company: {company_name}...")
    result = agent.research_company(company_name, job_description)
    
    # Save the result
    output_path = "test_results/company_researcher_result.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    save_json(result, output_path)
    
    print(f"Company research complete. Results saved to {output_path}")
    
    # Print a summary
    print("\nCompany Research Summary:")
    print(f"Company Background: {result.get('company_background', 'N/A')[:150]}...")
    print(f"Strategic Talking Points: {', '.join(result.get('strategic_talking_points', []))[:100]}...")

def test_resume_reviewer_agent():
    """Test the Resume Reviewer Agent."""
    print("\n=== Testing Resume Reviewer Agent ===")
    
    # Create the agent
    agent = ResumeReviewerAgent()
    
    # Read the sample resume and job description
    resume = read_file("brian_resume.txt")
    job_description = read_file("sample_job.html")
    
    # Review the resume
    print("Reviewing resume...")
    result = agent.review_resume(resume, job_description)
    
    # Save the result
    output_path = "test_results/resume_reviewer_result.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    save_json(result, output_path)
    
    print(f"Resume review complete. Results saved to {output_path}")
    
    # Print a summary
    print("\nResume Review Summary:")
    print(f"Overall Rating: {result.get('overall_rating', 'N/A')}/10")
    print(f"Strengths: {', '.join(result.get('strengths', []))[:100]}...")
    print(f"Weaknesses: {', '.join(result.get('weaknesses', []))[:100]}...")

def main():
    """Run all agent tests."""
    print("Starting agent tests...")
    
    # Create test results directory
    os.makedirs("test_results", exist_ok=True)
    
    # Test each agent
    test_job_analyzer_agent()
    test_ats_optimization_agent()
    test_company_researcher_agent()
    test_resume_reviewer_agent()
    
    print("\nAll agent tests completed. Results saved to the test_results directory.")

if __name__ == "__main__":
    main()

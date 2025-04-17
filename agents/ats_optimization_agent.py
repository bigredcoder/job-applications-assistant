#!/usr/bin/env python3
"""
ATS Optimization Agent for Job Application Assistant.
This agent helps optimize resumes for Applicant Tracking Systems.
"""

from typing import Dict, Any
from .base_agent import BaseAgent

class ATSOptimizationAgent(BaseAgent):
    """
    Agent that helps optimize resumes for Applicant Tracking Systems.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize the ATS Optimization Agent."""
        super().__init__(
            name="ATS Optimization Agent",
            description="Helps optimize resumes to pass through Applicant Tracking Systems",
            model=model
        )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the ATS Optimization Agent."""
        return """
        You are the ATS Optimization Agent, an expert at helping job applicants optimize their resumes to pass through Applicant Tracking Systems (ATS).
        
        Your task is to analyze the job description and the applicant's resume to provide recommendations for ATS optimization.
        
        Focus on the following aspects:
        
        1. Keyword Analysis: Identify important keywords and phrases from the job description that should be included in the resume.
        
        2. Keyword Gaps: Identify keywords from the job description that are missing from the resume.
        
        3. Format Optimization: Check if the resume format is ATS-friendly and provide recommendations if needed.
        
        4. Section Recommendations: Suggest improvements to resume sections to better match the job requirements.
        
        5. ATS Score Prediction: Provide an estimated ATS match score (0-100%) based on keyword matching and format.
        
        6. Specific Improvement Suggestions: Provide specific suggestions for improving the resume to increase ATS match.
        
        Provide your analysis in a structured JSON format with the following keys:
        - key_keywords: Array of the most important keywords from the job description
        - keyword_matches: Array of keywords that are already in the resume
        - keyword_gaps: Array of important keywords missing from the resume
        - format_issues: Array of any formatting issues that might affect ATS scanning
        - section_recommendations: Object with recommendations for each resume section
        - ats_score: Estimated ATS match score as a percentage
        - improvement_suggestions: Array of specific suggestions to improve ATS match
        - priority_actions: Array of high-priority actions to take for maximum impact
        
        Be thorough and practical in your recommendations. Focus on actionable advice that will help the applicant improve their ATS match score.
        """
    
    def optimize_for_ats(self, job_description: str, resume: str) -> Dict[str, Any]:
        """
        Analyze a resume against a job description for ATS optimization.
        
        Args:
            job_description: The text of the job posting
            resume: The text of the applicant's resume
            
        Returns:
            Dictionary containing ATS optimization recommendations
        """
        input_data = {
            "job_description": job_description,
            "resume": resume
        }
        
        return self.run(input_data)

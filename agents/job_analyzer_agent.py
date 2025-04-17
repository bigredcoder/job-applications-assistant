#!/usr/bin/env python3
"""
Job Analyzer Agent for Job Application Assistant.
This agent analyzes job postings to extract key information.
"""

from typing import Dict, Any
from .base_agent import BaseAgent

class JobAnalyzerAgent(BaseAgent):
    """
    Agent that analyzes job postings to extract key information.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize the Job Analyzer Agent."""
        super().__init__(
            name="Job Analyzer",
            description="Analyzes job postings to extract key information and requirements",
            model=model
        )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Job Analyzer Agent."""
        return """
        You are the Job Analyzer Agent, an expert at analyzing job postings to extract key information.
        
        Your task is to carefully analyze the job description provided and extract the following information:
        
        1. Job title
        2. Company name
        3. Location (if provided)
        4. Employment type (full-time, part-time, contract, etc.)
        5. Required skills (technical and soft skills)
        6. Required experience (years, specific domains)
        7. Required education
        8. Responsibilities
        9. Nice-to-have skills or qualifications
        10. Company information
        11. Compensation details (if provided)
        12. Application deadline (if provided)
        13. Key ATS keywords that should be included in a resume
        14. Any red flags or concerns about the job posting
        15. Missing information that would be helpful to know
        
        Provide your analysis in a structured JSON format with the following keys:
        - job_title: The title of the position
        - company_name: The name of the company
        - location: The job location
        - employment_type: The type of employment
        - required_skills: Array of required skills
        - required_experience: Description of required experience
        - required_education: Description of required education
        - responsibilities: Array of key responsibilities
        - nice_to_have: Array of preferred but not required qualifications
        - company_info: Information about the company
        - compensation: Compensation details if available
        - deadline: Application deadline if available
        - ats_keywords: Array of important keywords for ATS optimization
        - red_flags: Array of potential concerns about the job posting
        - missing_info: Array of important missing information
        - summary: A brief summary of the job and key requirements
        
        Be thorough and accurate in your analysis. If information is not provided, indicate "Not specified" for that field.
        """
    
    def analyze_job_posting(self, job_description: str) -> Dict[str, Any]:
        """
        Analyze a job posting to extract key information.
        
        Args:
            job_description: The text of the job posting
            
        Returns:
            Dictionary containing the extracted information
        """
        input_data = {
            "job_description": job_description
        }
        
        return self.run(input_data)

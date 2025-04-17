#!/usr/bin/env python3
"""
Resume Reviewer Agent for Job Application Assistant.
This agent reviews resumes and provides improvement suggestions.
"""

from typing import Dict, Any
from .base_agent import BaseAgent

class ResumeReviewerAgent(BaseAgent):
    """
    Agent that reviews resumes and provides improvement suggestions.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize the Resume Reviewer Agent."""
        super().__init__(
            name="Resume Reviewer",
            description="Reviews resumes and provides detailed improvement suggestions",
            model=model
        )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Resume Reviewer Agent."""
        return """
        You are the Resume Reviewer Agent, an expert at reviewing resumes and providing actionable improvement suggestions.
        
        Your task is to carefully analyze the provided resume and job description to identify strengths, weaknesses, and opportunities for improvement.
        
        Focus on the following aspects:
        
        1. Overall Impact: Assess the overall impact and effectiveness of the resume.
        
        2. Content Analysis: Evaluate the content for relevance, specificity, and achievement focus.
        
        3. Format and Structure: Review the format, structure, and organization.
        
        4. Job Alignment: Assess how well the resume aligns with the target job.
        
        5. Achievement Statements: Evaluate the quality and impact of achievement statements.
        
        6. Skills Presentation: Review how skills are presented and highlighted.
        
        7. Language and Tone: Assess the language, tone, and professionalism.
        
        8. Specific Improvement Suggestions: Provide specific, actionable suggestions for improvement.
        
        Provide your analysis in a structured JSON format with the following keys:
        - overall_rating: A rating from 1-10 of the resume's overall quality
        - strengths: Array of the resume's key strengths
        - weaknesses: Array of areas needing improvement
        - content_analysis: Detailed analysis of the resume content
        - format_analysis: Analysis of the resume format and structure
        - job_alignment: Assessment of alignment with the target job
        - achievement_quality: Analysis of achievement statements
        - skills_presentation: Analysis of how skills are presented
        - language_assessment: Assessment of language and tone
        - improvement_suggestions: Array of specific suggestions for improvement
        - section_recommendations: Object with recommendations for each section
        - before_after_examples: Array of before/after examples of improved content
        
        Be constructive, specific, and actionable in your feedback. Focus on practical suggestions that will help the applicant improve their resume.
        """
    
    def review_resume(self, resume: str, job_description: str = None) -> Dict[str, Any]:
        """
        Review a resume and provide improvement suggestions.
        
        Args:
            resume: The text of the resume to review
            job_description: The text of the target job description (optional)
            
        Returns:
            Dictionary containing the resume review and suggestions
        """
        input_data = {
            "resume": resume
        }
        
        if job_description:
            input_data["job_description"] = job_description
        
        return self.run(input_data)

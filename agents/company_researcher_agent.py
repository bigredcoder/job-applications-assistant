#!/usr/bin/env python3
"""
Company Researcher Agent for Job Application Assistant.
This agent researches companies to find strategic information.
"""

from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent

class CompanyResearcherAgent(BaseAgent):
    """
    Agent that researches companies to find strategic information.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize the Company Researcher Agent."""
        super().__init__(
            name="Company Researcher",
            description="Researches companies to find strategic information for job applications",
            model=model
        )
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Company Researcher Agent."""
        return """
        You are the Company Researcher Agent, an expert at finding and analyzing strategic information about companies for job applications.
        
        Your task is to analyze the provided information about a company and job position to identify strategic insights that can give the applicant an advantage.
        
        Focus on the following aspects:
        
        1. Company Background: Key facts about the company's history, mission, and values.
        
        2. Recent News: Recent announcements, product launches, or initiatives that could be relevant.
        
        3. Company Culture: Insights about the company's culture, work environment, and values.
        
        4. Pain Points: Potential challenges or problems the company might be facing that the applicant could help solve.
        
        5. Growth Areas: Areas where the company is expanding or investing.
        
        6. Competitive Landscape: Key competitors and the company's position in the market.
        
        7. Strategic Talking Points: Specific points the applicant could mention in their cover letter or interview.
        
        8. Connection Opportunities: Ways the applicant's background aligns with the company's needs.
        
        Provide your analysis in a structured JSON format with the following keys:
        - company_background: Key facts about the company
        - recent_news: Array of recent relevant news items
        - company_culture: Insights about the company culture
        - pain_points: Array of potential challenges the company faces
        - growth_areas: Array of areas where the company is growing
        - competitive_landscape: Brief analysis of the competitive landscape
        - strategic_talking_points: Array of points to mention in application materials
        - connection_opportunities: Array of ways the applicant can connect their experience to company needs
        - cover_letter_suggestions: Specific suggestions for the cover letter
        - interview_talking_points: Points to bring up in an interview
        
        Be strategic and focus on information that will give the applicant a competitive advantage. If you don't have enough information about certain aspects, indicate what additional research would be helpful.
        """
    
    def research_company(self, company_name: str, job_description: str, additional_info: Optional[str] = None) -> Dict[str, Any]:
        """
        Research a company to find strategic information.
        
        Args:
            company_name: The name of the company
            job_description: The text of the job posting
            additional_info: Any additional information about the company (optional)
            
        Returns:
            Dictionary containing strategic company information
        """
        input_data = {
            "company_name": company_name,
            "job_description": job_description
        }
        
        if additional_info:
            input_data["additional_info"] = additional_info
        
        return self.run(input_data)

#!/usr/bin/env python3
"""
Agent Manager for Job Application Assistant.
This module provides a unified interface for working with all agents.
"""

from typing import Dict, Any, List, Optional
from .job_analyzer_agent import JobAnalyzerAgent
from .ats_optimization_agent import ATSOptimizationAgent
from .company_researcher_agent import CompanyResearcherAgent
from .resume_reviewer_agent import ResumeReviewerAgent

class AgentManager:
    """
    Manager class for all Job Application Assistant agents.
    Provides a unified interface for working with agents.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the Agent Manager.
        
        Args:
            model: The default OpenAI model to use for agents
        """
        self.model = model
        self._agents = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all available agents."""
        self._agents = {
            "job_analyzer": JobAnalyzerAgent(model=self.model),
            "ats_optimization": ATSOptimizationAgent(model=self.model),
            "company_researcher": CompanyResearcherAgent(model=self.model),
            "resume_reviewer": ResumeReviewerAgent(model=self.model)
        }
    
    def get_agent(self, agent_name: str):
        """
        Get an agent by name.
        
        Args:
            agent_name: The name of the agent to get
            
        Returns:
            The requested agent instance
            
        Raises:
            ValueError: If the agent name is not recognized
        """
        if agent_name not in self._agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        return self._agents[agent_name]
    
    def get_available_agents(self) -> List[Dict[str, str]]:
        """
        Get information about all available agents.
        
        Returns:
            List of dictionaries with agent information
        """
        return [agent.get_info() for agent in self._agents.values()]
    
    def analyze_job(self, job_description: str) -> Dict[str, Any]:
        """
        Analyze a job posting using the Job Analyzer Agent.
        
        Args:
            job_description: The text of the job posting
            
        Returns:
            Dictionary containing the job analysis
        """
        return self._agents["job_analyzer"].analyze_job_posting(job_description)
    
    def optimize_for_ats(self, job_description: str, resume: str) -> Dict[str, Any]:
        """
        Optimize a resume for ATS using the ATS Optimization Agent.
        
        Args:
            job_description: The text of the job posting
            resume: The text of the resume
            
        Returns:
            Dictionary containing ATS optimization recommendations
        """
        return self._agents["ats_optimization"].optimize_for_ats(job_description, resume)
    
    def research_company(self, company_name: str, job_description: str, additional_info: Optional[str] = None) -> Dict[str, Any]:
        """
        Research a company using the Company Researcher Agent.
        
        Args:
            company_name: The name of the company
            job_description: The text of the job posting
            additional_info: Any additional information about the company (optional)
            
        Returns:
            Dictionary containing company research information
        """
        return self._agents["company_researcher"].research_company(company_name, job_description, additional_info)
    
    def review_resume(self, resume: str, job_description: str = None) -> Dict[str, Any]:
        """
        Review a resume using the Resume Reviewer Agent.
        
        Args:
            resume: The text of the resume
            job_description: The text of the job posting (optional)
            
        Returns:
            Dictionary containing resume review and suggestions
        """
        return self._agents["resume_reviewer"].review_resume(resume, job_description)

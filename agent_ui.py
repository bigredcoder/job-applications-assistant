#!/usr/bin/env python3
"""
Agent UI Integration for Job Application Assistant.
This module provides UI components for interacting with the specialized agents.
"""

import streamlit as st
import json
from typing import Dict, Any, List, Optional
from agents.agent_manager import AgentManager

def initialize_agent_manager():
    """
    Initialize the Agent Manager.
    
    Returns:
        An instance of the AgentManager
    """
    # Use the model specified in session state or default to gpt-4o-mini
    model = st.session_state.get("agent_model", "gpt-4o-mini")
    return AgentManager(model=model)

def display_agent_selector():
    """
    Display a selector for choosing an agent.
    
    Returns:
        The name of the selected agent
    """
    # Initialize agent manager
    agent_manager = initialize_agent_manager()
    
    # Get available agents
    available_agents = agent_manager.get_available_agents()
    agent_options = {agent["name"]: agent["description"] for agent in available_agents}
    
    # Create a selectbox for choosing an agent
    selected_agent = st.selectbox(
        "Select an Agent",
        options=list(agent_options.keys()),
        format_func=lambda x: f"{x} - {agent_options[x]}"
    )
    
    return selected_agent

def display_job_analyzer_ui(job_description: str):
    """
    Display the Job Analyzer Agent UI.
    
    Args:
        job_description: The text of the job posting
    """
    st.subheader("Job Analyzer")
    
    with st.spinner("Analyzing job posting..."):
        # Initialize agent manager
        agent_manager = initialize_agent_manager()
        
        # Analyze the job posting
        result = agent_manager.analyze_job(job_description)
        
        # Store the result in session state
        st.session_state.job_analysis = result
    
    # Display the results
    st.success("Job analysis complete!")
    
    # Job details
    st.markdown("### Job Details")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Job Title:** {result.get('job_title', 'Not specified')}")
        st.markdown(f"**Company:** {result.get('company_name', 'Not specified')}")
        st.markdown(f"**Location:** {result.get('location', 'Not specified')}")
    with col2:
        st.markdown(f"**Employment Type:** {result.get('employment_type', 'Not specified')}")
        st.markdown(f"**Compensation:** {result.get('compensation', 'Not specified')}")
        st.markdown(f"**Deadline:** {result.get('deadline', 'Not specified')}")
    
    # Required skills
    st.markdown("### Required Skills")
    if result.get('required_skills'):
        for skill in result.get('required_skills'):
            st.markdown(f"- {skill}")
    else:
        st.markdown("No specific skills listed.")
    
    # Required experience and education
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Required Experience")
        st.markdown(result.get('required_experience', 'Not specified'))
    with col2:
        st.markdown("### Required Education")
        st.markdown(result.get('required_education', 'Not specified'))
    
    # Responsibilities
    st.markdown("### Key Responsibilities")
    if result.get('responsibilities'):
        for resp in result.get('responsibilities'):
            st.markdown(f"- {resp}")
    else:
        st.markdown("No specific responsibilities listed.")
    
    # Nice to have
    st.markdown("### Nice to Have")
    if result.get('nice_to_have'):
        for item in result.get('nice_to_have'):
            st.markdown(f"- {item}")
    else:
        st.markdown("No 'nice to have' qualifications listed.")
    
    # ATS Keywords
    st.markdown("### Important ATS Keywords")
    if result.get('ats_keywords'):
        keyword_html = ""
        for keyword in result.get('ats_keywords'):
            keyword_html += f'<span style="background-color: #e6f3ff; padding: 3px 8px; margin: 2px; border-radius: 10px; display: inline-block;">{keyword}</span>'
        st.markdown(keyword_html, unsafe_allow_html=True)
    else:
        st.markdown("No specific ATS keywords identified.")
    
    # Red flags and missing info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Potential Red Flags")
        if result.get('red_flags'):
            for flag in result.get('red_flags'):
                st.markdown(f"- {flag}")
        else:
            st.markdown("No red flags identified.")
    
    with col2:
        st.markdown("### Missing Information")
        if result.get('missing_info'):
            for info in result.get('missing_info'):
                st.markdown(f"- {info}")
        else:
            st.markdown("No important missing information identified.")
    
    # Summary
    st.markdown("### Summary")
    st.markdown(result.get('summary', 'No summary available.'))

def display_ats_optimization_ui(job_description: str, resume: str):
    """
    Display the ATS Optimization Agent UI.
    
    Args:
        job_description: The text of the job posting
        resume: The text of the resume
    """
    st.subheader("ATS Optimization")
    
    with st.spinner("Optimizing resume for ATS..."):
        # Initialize agent manager
        agent_manager = initialize_agent_manager()
        
        # Optimize for ATS
        result = agent_manager.optimize_for_ats(job_description, resume)
        
        # Store the result in session state
        st.session_state.ats_optimization = result
    
    # Display the results
    st.success("ATS optimization analysis complete!")
    
    # ATS Score
    score = result.get('ats_score', 'N/A')
    score_color = "#d4edda" if score >= 70 else "#fff3cd" if score >= 50 else "#f8d7da"
    st.markdown(
        f"""
        <div style="background-color: {score_color}; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <h3 style="margin-top: 0;">ATS Match Score: {score}</h3>
            <p>This is an estimate of how well your resume matches the job description according to an ATS.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Keyword Analysis
    st.markdown("### Keyword Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Keyword Matches")
        if result.get('keyword_matches'):
            match_html = ""
            for keyword in result.get('keyword_matches'):
                match_html += f'<span style="background-color: #d4edda; padding: 3px 8px; margin: 2px; border-radius: 10px; display: inline-block;">{keyword}</span>'
            st.markdown(match_html, unsafe_allow_html=True)
        else:
            st.markdown("No keyword matches found.")
    
    with col2:
        st.markdown("#### Keyword Gaps")
        if result.get('keyword_gaps'):
            gap_html = ""
            for keyword in result.get('keyword_gaps'):
                gap_html += f'<span style="background-color: #f8d7da; padding: 3px 8px; margin: 2px; border-radius: 10px; display: inline-block;">{keyword}</span>'
            st.markdown(gap_html, unsafe_allow_html=True)
        else:
            st.markdown("No keyword gaps identified.")
    
    # Format Issues
    st.markdown("### Format Issues")
    if result.get('format_issues'):
        for issue in result.get('format_issues'):
            st.markdown(f"- {issue}")
    else:
        st.markdown("No format issues identified.")
    
    # Improvement Suggestions
    st.markdown("### Improvement Suggestions")
    if result.get('improvement_suggestions'):
        for suggestion in result.get('improvement_suggestions'):
            st.markdown(f"- {suggestion}")
    else:
        st.markdown("No specific improvement suggestions.")
    
    # Priority Actions
    st.markdown("### Priority Actions")
    if result.get('priority_actions'):
        for i, action in enumerate(result.get('priority_actions')):
            st.markdown(f"**{i+1}.** {action}")
    else:
        st.markdown("No priority actions identified.")

def display_company_researcher_ui(company_name: str, job_description: str):
    """
    Display the Company Researcher Agent UI.
    
    Args:
        company_name: The name of the company
        job_description: The text of the job posting
    """
    st.subheader("Company Research")
    
    # Additional information input
    additional_info = st.text_area(
        "Additional Information (Optional)",
        placeholder="Enter any additional information you have about the company...",
        height=100
    )
    
    if st.button("Research Company"):
        with st.spinner("Researching company..."):
            # Initialize agent manager
            agent_manager = initialize_agent_manager()
            
            # Research the company
            result = agent_manager.research_company(company_name, job_description, additional_info if additional_info else None)
            
            # Store the result in session state
            st.session_state.company_research = result
        
        # Display the results
        st.success(f"Research on {company_name} complete!")
        
        # Company Background
        st.markdown("### Company Background")
        st.markdown(result.get('company_background', 'No background information available.'))
        
        # Recent News
        st.markdown("### Recent News")
        if result.get('recent_news'):
            for news in result.get('recent_news'):
                st.markdown(f"- {news}")
        else:
            st.markdown("No recent news found.")
        
        # Company Culture
        st.markdown("### Company Culture")
        st.markdown(result.get('company_culture', 'No culture information available.'))
        
        # Pain Points and Growth Areas
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Potential Pain Points")
            if result.get('pain_points'):
                for point in result.get('pain_points'):
                    st.markdown(f"- {point}")
            else:
                st.markdown("No specific pain points identified.")
        
        with col2:
            st.markdown("### Growth Areas")
            if result.get('growth_areas'):
                for area in result.get('growth_areas'):
                    st.markdown(f"- {area}")
            else:
                st.markdown("No specific growth areas identified.")
        
        # Competitive Landscape
        st.markdown("### Competitive Landscape")
        st.markdown(result.get('competitive_landscape', 'No competitive landscape information available.'))
        
        # Strategic Talking Points
        st.markdown("### Strategic Talking Points")
        if result.get('strategic_talking_points'):
            for point in result.get('strategic_talking_points'):
                st.markdown(f"- {point}")
        else:
            st.markdown("No specific talking points identified.")
        
        # Connection Opportunities
        st.markdown("### Connection Opportunities")
        if result.get('connection_opportunities'):
            for opportunity in result.get('connection_opportunities'):
                st.markdown(f"- {opportunity}")
        else:
            st.markdown("No specific connection opportunities identified.")
        
        # Cover Letter and Interview Suggestions
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Cover Letter Suggestions")
            if result.get('cover_letter_suggestions'):
                for suggestion in result.get('cover_letter_suggestions'):
                    st.markdown(f"- {suggestion}")
            else:
                st.markdown("No specific cover letter suggestions.")
        
        with col2:
            st.markdown("### Interview Talking Points")
            if result.get('interview_talking_points'):
                for point in result.get('interview_talking_points'):
                    st.markdown(f"- {point}")
            else:
                st.markdown("No specific interview talking points.")

def display_resume_reviewer_ui(resume: str, job_description: str = None):
    """
    Display the Resume Reviewer Agent UI.
    
    Args:
        resume: The text of the resume
        job_description: The text of the job posting (optional)
    """
    st.subheader("Resume Review")
    
    with st.spinner("Reviewing resume..."):
        # Initialize agent manager
        agent_manager = initialize_agent_manager()
        
        # Review the resume
        result = agent_manager.review_resume(resume, job_description)
        
        # Store the result in session state
        st.session_state.resume_review = result
    
    # Display the results
    st.success("Resume review complete!")
    
    # Overall Rating
    rating = result.get('overall_rating', 'N/A')
    rating_color = "#d4edda" if rating >= 7 else "#fff3cd" if rating >= 5 else "#f8d7da"
    st.markdown(
        f"""
        <div style="background-color: {rating_color}; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <h3 style="margin-top: 0;">Overall Rating: {rating}/10</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Strengths and Weaknesses
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Strengths")
        if result.get('strengths'):
            for strength in result.get('strengths'):
                st.markdown(f"- {strength}")
        else:
            st.markdown("No specific strengths identified.")
    
    with col2:
        st.markdown("### Areas for Improvement")
        if result.get('weaknesses'):
            for weakness in result.get('weaknesses'):
                st.markdown(f"- {weakness}")
        else:
            st.markdown("No specific areas for improvement identified.")
    
    # Content Analysis
    st.markdown("### Content Analysis")
    st.markdown(result.get('content_analysis', 'No content analysis available.'))
    
    # Format Analysis
    st.markdown("### Format Analysis")
    st.markdown(result.get('format_analysis', 'No format analysis available.'))
    
    # Job Alignment
    if job_description:
        st.markdown("### Job Alignment")
        st.markdown(result.get('job_alignment', 'No job alignment analysis available.'))
    
    # Achievement Quality
    st.markdown("### Achievement Statement Quality")
    st.markdown(result.get('achievement_quality', 'No achievement analysis available.'))
    
    # Skills Presentation
    st.markdown("### Skills Presentation")
    st.markdown(result.get('skills_presentation', 'No skills presentation analysis available.'))
    
    # Language Assessment
    st.markdown("### Language Assessment")
    st.markdown(result.get('language_assessment', 'No language assessment available.'))
    
    # Improvement Suggestions
    st.markdown("### Improvement Suggestions")
    if result.get('improvement_suggestions'):
        for suggestion in result.get('improvement_suggestions'):
            st.markdown(f"- {suggestion}")
    else:
        st.markdown("No specific improvement suggestions.")
    
    # Before/After Examples
    st.markdown("### Before/After Examples")
    if result.get('before_after_examples'):
        for example in result.get('before_after_examples'):
            st.markdown("**Before:**")
            st.markdown(f"> {example.get('before', '')}")
            st.markdown("**After:**")
            st.markdown(f"> {example.get('after', '')}")
    else:
        st.markdown("No before/after examples provided.")

def display_agent_ui(agent_name: str, job_description: str, resume: str, company_name: str):
    """
    Display the UI for a specific agent.
    
    Args:
        agent_name: The name of the agent to display
        job_description: The text of the job posting
        resume: The text of the resume
        company_name: The name of the company
    """
    if agent_name == "Job Analyzer":
        display_job_analyzer_ui(job_description)
    elif agent_name == "ATS Optimization Agent":
        display_ats_optimization_ui(job_description, resume)
    elif agent_name == "Company Researcher":
        display_company_researcher_ui(company_name, job_description)
    elif agent_name == "Resume Reviewer":
        display_resume_reviewer_ui(resume, job_description)
    else:
        st.warning(f"UI for agent '{agent_name}' not implemented yet.")

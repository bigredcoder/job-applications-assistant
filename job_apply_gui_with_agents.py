#!/usr/bin/env python3
"""
job_apply_gui_with_agents.py – Streamlit GUI for the Job Application Assistant with AI Agents
==========================================================================================
This is a Streamlit-based GUI for the Job Application Assistant with specialized AI agents.
It allows users to:
1. Enter a job posting URL or paste a job description
2. Upload their resume or use a default one
3. Generate a tailored resume and cover letter
4. Use specialized AI agents for different aspects of the job application process
5. Download the generated documents
"""

import os
import re
import tempfile
import streamlit as st
from pathlib import Path

# Import the job application assistant functions
from job_apply_assistant import (
    generate_documents,
    compute_fit_score,
    _md_to_pdf,
    clean_company_name,
    _strip_html,
    _tokens,
    STOPWORDS,
    TOKEN_RE
)
from file_utils import extract_text_from_file
from pdf_utils import get_pdf_download_link, get_docx_download_link

# Import the agent UI module
import agent_ui

# Define a simplified fetch_job_description function that doesn't use readability
def fetch_job_description(src: str) -> str:
    """Simplified job description fetcher that doesn't use readability."""
    import requests
    from bs4 import BeautifulSoup
    from pathlib import Path
    import re
    
    try:
        if src.startswith("http"):
            try:
                # Special handling for LinkedIn URLs
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/"
                }

                # Make the request
                resp = requests.get(src, headers=headers, timeout=30)
                resp.raise_for_status()
                html = resp.text
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    raise ValueError(f"Access denied (403 Forbidden). The website may be blocking automated access. Try saving the job posting as HTML and uploading it instead.")
                elif e.response.status_code == 404:
                    raise ValueError(f"Job posting not found (404 Not Found). Please check the URL and try again.")
                else:
                    raise ValueError(f"HTTP error when accessing URL: {e}")
            except requests.exceptions.ConnectionError:
                raise ValueError(f"Connection error. Please check your internet connection and the URL.")
            except requests.exceptions.Timeout:
                raise ValueError(f"Request timed out. The server may be slow or unreachable.")
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Error fetching URL: {e}")
        else:
            try:
                html = Path(src).read_text(encoding="utf-8")
            except FileNotFoundError:
                raise ValueError(f"File not found: {src}")
            except Exception as e:
                raise ValueError(f"Error reading file: {e}")

        # Parse the HTML content using BeautifulSoup only
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            # Special handling for LinkedIn
            if "linkedin.com" in src:
                # Try to find the job description section
                for selector in [
                    ".description__text",
                    ".show-more-less-html__markup",
                    "#job-details",
                    ".jobs-description__content",
                    ".jobs-box__html-content"
                ]:
                    elements = soup.select(selector)
                    if elements:
                        return _strip_html(elements[0].get_text("\n", strip=True))
            
            # Get text from the page
            text = soup.get_text("\n", strip=True)
            
            # Look for the largest text block (likely the job description)
            paragraphs = text.split("\n\n")
            if paragraphs:
                largest_paragraph = max(paragraphs, key=len)
                if len(largest_paragraph) > 100:  # Only use if it's substantial
                    return _strip_html(largest_paragraph)
            
            # If we couldn't find a large paragraph, just return all the text
            return _strip_html(text)
            
        except Exception as e:
            raise ValueError(f"Error parsing HTML content: {e}")
    except ValueError as e:
        # Re-raise ValueError to be caught by the caller
        raise
    except Exception as e:
        # Catch any other exceptions and convert to ValueError
        raise ValueError(f"Unexpected error: {e}")

def main():
    # Set page config
    st.set_page_config(
        page_title="Job-Apply Assistant",
        page_icon="📝",
        layout="wide"
    )

    # Initialize session state for storing generated documents
    if 'documents' not in st.session_state:
        st.session_state.documents = None
    if 'fit_score' not in st.session_state:
        st.session_state.fit_score = None
    if 'company_name' not in st.session_state:
        st.session_state.company_name = None
    if 'role_title' not in st.session_state:
        st.session_state.role_title = None
    if 'created_files' not in st.session_state:
        st.session_state.created_files = []
    if 'job_description' not in st.session_state:
        st.session_state.job_description = None
    if 'resume_text' not in st.session_state:
        st.session_state.resume_text = None
    if 'agent_model' not in st.session_state:
        st.session_state.agent_model = "gpt-4o-mini"

    # Title and description
    st.title("Job-Apply Assistant")
    st.markdown("""
    Generate ATS-optimized résumé and cover letter PDFs for job applications.
    The tool analyzes the job description, tailors your résumé, and creates a matching cover letter.
    """)

    # Set default values for hidden fields
    output_dir = "./generated"

    # Use environment variable for OpenAI API key
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")

        # Applicant name
        applicant_name = st.text_input("Your Full Name",
                                      value="Brian Robison",
                                      help="Your name as it should appear on the résumé and cover letter.")

        # Baseline resume
        st.subheader("Baseline Résumé")

        # Option to use default resume
        use_default_resume = st.checkbox("Use Brian's default resume", value=True,
                                       help="Use the pre-loaded resume for Brian Robison")

        if use_default_resume:
            # Create a placeholder for the file uploader but hide it
            resume_upload_container = st.empty()
            # Set resume_upload to None as we'll handle it separately
            resume_upload = None

            # Add option to view and edit the default resume
            edit_default_resume = st.checkbox("View/Edit default resume", value=False,
                                            help="View and edit the default resume content")

            if edit_default_resume:
                # Read the default resume content
                default_resume_path = "brian_resume.txt"
                try:
                    with open(default_resume_path, "r") as f:
                        default_resume_content = f.read()
                except Exception as e:
                    st.error(f"Error reading default resume: {e}")
                    default_resume_content = ""

                # Show a text area to edit the resume
                edited_resume = st.text_area("Edit Default Resume",
                                           value=default_resume_content,
                                           height=400)

                # Add a save button
                if st.button("Save Changes to Default Resume"):
                    try:
                        with open(default_resume_path, "w") as f:
                            f.write(edited_resume)
                        st.success("Default resume updated successfully!")
                    except Exception as e:
                        st.error(f"Error saving default resume: {e}")
            else:
                st.success("Using Brian's default resume from brian_resume.txt")
        else:
            # Show the file uploader if not using default resume
            resume_upload = st.file_uploader("Upload your baseline résumé",
                                            type=["txt", "md", "doc", "docx"],
                                            help="Upload your current résumé in text, markdown, or Word format.")

        # Add a small divider
        st.markdown("---")
        
        # AI Model Selection
        st.subheader("AI Model Settings")
        agent_model = st.selectbox(
            "Select AI Model",
            options=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            index=0,
            help="Select the AI model to use for the agents. GPT-4o is more powerful but may be slower."
        )
        
        # Update the model in session state
        if agent_model != st.session_state.agent_model:
            st.session_state.agent_model = agent_model

    # Main area for job input
    st.header("Job Description Input")

    # Tabs for URL or pasted job description
    tab1, tab2 = st.tabs(["Job URL", "Paste Job Description"])

    with tab1:
        job_url = st.text_input("Job Posting URL",
                               help="Enter the URL of the job posting (LinkedIn, Indeed, etc.)")

    with tab2:
        job_description_text = st.text_area("Paste Job Description",
                                          height=300,
                                          help="Paste the job description text directly from the website.")

        # Add company name field for manual entry
        manual_company_name = st.text_input("Company Name",
                                          help="Enter the company name for the job posting.")

        # Add job title field for manual entry
        manual_job_title = st.text_input("Job Title",
                                       help="Enter the job title for the job posting.")

        # Set job_html_upload to None since we're replacing it with the text area
        job_html_upload = None

    # Check if OpenAI API key is set
    if not openai_key:
        st.warning("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable before running the app.")

    # Process button
    process_button = st.button("Process Job Description",
                               type="primary",
                               disabled=not (
                                   # Either a job URL or pasted job description is required
                                   (job_url or (job_description_text and manual_company_name and manual_job_title)) and
                                   # Either a resume upload or the default resume is required
                                   (resume_upload is not None or use_default_resume) and
                                   # Applicant name and OpenAI API key are required
                                   applicant_name and
                                   openai_key
                               ))

    # Process when process button is clicked
    if process_button:
        try:
            with st.spinner("Processing job description..."):
                # Get job description
                try:
                    if job_url:
                        # We'll set a temporary company name, but the final one will come from the cover letter
                        # This is just a fallback in case we can't extract from the cover letter
                        company_name = "Company"  # Default fallback

                        # Check for common job board domains and extract company name as a fallback
                        if "linkedin.com/jobs" in job_url.lower():
                            # For LinkedIn, we'll extract from the job description later
                            # LinkedIn URLs don't typically contain the company name in a reliable format
                            st.info("LinkedIn job URL detected - will extract company from cover letter")
                        elif "indeed.com" in job_url.lower():
                            # For Indeed, we'll extract from the job description later
                            # Indeed URLs don't typically contain the company name in a reliable format
                            st.info("Indeed job URL detected - will extract company from cover letter")

                        # Fetch job description from URL
                        job_description = fetch_job_description(job_url)
                        job_source = job_url
                    elif job_description_text:
                        # Use manually entered job description
                        job_description = job_description_text
                        company_name = manual_company_name
                        role_title = manual_job_title
                        job_source = "manual entry"
                    else:
                        st.error("Please provide either a job URL or paste a job description.")
                        return
                except ValueError as e:
                    st.error(f"Error processing job description: {e}")
                    return
                except Exception as e:
                    st.error(f"Unexpected error processing job description: {e}")
                    return

                # Get resume text
                try:
                    if use_default_resume:
                        # Use default resume
                        default_resume_path = "brian_resume.txt"
                        try:
                            with open(default_resume_path, "r") as f:
                                resume_text = f.read()
                        except Exception as e:
                            st.error(f"Error reading default resume: {e}")
                            return
                    elif resume_upload is not None:
                        # Use uploaded resume
                        try:
                            resume_text = extract_text_from_file(resume_upload)
                        except Exception as e:
                            st.error(f"Error extracting text from resume: {e}")
                            return
                    else:
                        st.error("Please either upload a resume or use the default resume.")
                        return
                except Exception as e:
                    st.error(f"Unexpected error processing resume: {e}")
                    return
            
            # Store job description and resume in session state
            st.session_state.job_description = job_description
            st.session_state.resume_text = resume_text
            
            # If we're using a URL, we need to extract the role title from the job description
            if job_url:
                # Extract role from first line of job description
                first_line = job_description.split("\n", 1)[0]
                role_title = first_line[:80]  # Limit to 80 chars
            
            # Store company and role in session state
            st.session_state.company_name = company_name
            st.session_state.role_title = role_title
            
            st.success("Job description and resume processed successfully!")

        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return

    # Display agent interface if job description and resume are available
    if st.session_state.job_description and st.session_state.resume_text:
        st.header("AI Agents")
        st.markdown("""
        Use our specialized AI agents to help with different aspects of your job application.
        Each agent has a specific role in helping you create the best possible application.
        """)
        
        # Agent tabs
        agent_tabs = st.tabs([
            "Job Analyzer", 
            "ATS Optimization", 
            "Company Research", 
            "Resume Review",
            "Generate Documents"
        ])
        
        with agent_tabs[0]:
            # Job Analyzer Agent
            agent_ui.display_job_analyzer_ui(st.session_state.job_description)
        
        with agent_tabs[1]:
            # ATS Optimization Agent
            agent_ui.display_ats_optimization_ui(
                st.session_state.job_description, 
                st.session_state.resume_text
            )
        
        with agent_tabs[2]:
            # Company Researcher Agent
            agent_ui.display_company_researcher_ui(
                st.session_state.company_name,
                st.session_state.job_description
            )
        
        with agent_tabs[3]:
            # Resume Reviewer Agent
            agent_ui.display_resume_reviewer_ui(
                st.session_state.resume_text,
                st.session_state.job_description
            )
        
        with agent_tabs[4]:
            # Generate Documents Tab
            st.subheader("Generate Tailored Documents")
            
            if st.button("Generate Résumé & Cover Letter", type="primary"):
                with st.spinner("Generating tailored résumé and cover letter..."):
                    # Generate documents
                    try:
                        # Generate documents
                        resume_md, cover_letter_md = generate_documents(
                            st.session_state.job_description, 
                            st.session_state.resume_text, 
                            applicant_name, 
                            st.session_state.role_title, 
                            st.session_state.company_name
                        )

                        # Store in session state
                        st.session_state.documents = (resume_md, cover_letter_md)

                        # Extract company name from cover letter if we're using a URL
                        if job_url:
                            # Look for company name in the cover letter
                            # Common patterns in cover letters
                            company_patterns = [
                                r"Dear\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+Hiring",  # "Dear [Company] Hiring"
                                r"Dear\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+Team",    # "Dear [Company] Team"
                                r"Dear\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+Recruiter",  # "Dear [Company] Recruiter"
                                r"at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",             # "at [Company]"
                                r"join\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",           # "join [Company]"
                                r"with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",           # "with [Company]"
                            ]

                            for pattern in company_patterns:
                                match = re.search(pattern, cover_letter_md)
                                if match:
                                    st.session_state.company_name = match.group(1).strip()
                                    break

                        # Compute fit score
                        score, details = compute_fit_score(st.session_state.job_description, resume_md)
                        st.session_state.fit_score = (score, details)

                        # Save files to disk
                        try:
                            # Create output directory
                            os.makedirs(output_dir, exist_ok=True)

                            # Clean company name for filenames
                            safe_company = clean_company_name(st.session_state.company_name)

                            # Save markdown files
                            resume_md_path = os.path.join(output_dir, f"resume_{safe_company}.md")
                            cover_md_path = os.path.join(output_dir, f"cover_letter_{safe_company}.md")

                            with open(resume_md_path, "w") as f:
                                f.write(resume_md)
                            with open(cover_md_path, "w") as f:
                                f.write(cover_letter_md)

                            # Save PDF files
                            resume_pdf_path = os.path.join(output_dir, f"robison_resume-{safe_company}.pdf")
                            cover_pdf_path = os.path.join(output_dir, f"robison_coverletter-{safe_company}.pdf")

                            resume_pdf_success = _md_to_pdf(resume_md, Path(resume_pdf_path))
                            cover_pdf_success = _md_to_pdf(cover_letter_md, Path(cover_pdf_path))

                            # Store created files in session state
                            st.session_state.created_files = [
                                (resume_md_path, "Résumé (Markdown)"),
                                (cover_md_path, "Cover Letter (Markdown)"),
                            ]

                            if resume_pdf_success:
                                st.session_state.created_files.append((resume_pdf_path, "Résumé (PDF)"))
                            if cover_pdf_success:
                                st.session_state.created_files.append((cover_pdf_path, "Cover Letter (PDF)"))

                        except Exception as e:
                            st.warning(f"Note: Could not save files to disk: {e}")
                            # Continue anyway since we have the documents in memory

                    except Exception as e:
                        st.error(f"Error generating documents: {e}")
                        return
            
            # Display results if documents have been generated
            if 'documents' in st.session_state and st.session_state.documents:
                resume_md, cover_letter_md = st.session_state.documents
                company_name = st.session_state.company_name
                role_title = st.session_state.role_title
                score, details = st.session_state.fit_score

                st.success(f"✅ Generated documents for {role_title} at {company_name}")

                # Display fit score
                st.subheader("FitScore™")
                score_color = '#d4edda' if score >= 70 else '#fff3cd' if score >= 50 else '#f8d7da'
                text_color = '#333333'  # Dark text for better readability
                
                st.markdown(f"""
                <div style="background-color: {score_color}; color: {text_color};
                            padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #ddd;">
                    <h3 style="margin-top: 0; color: {text_color};">Overall Score: {score}/100</h3>
                    <ul style="color: {text_color};">
                        <li><strong>Keyword coverage:</strong> {details['keyword_coverage']}%</li>
                        <li><strong>Seniority match:</strong> {details['seniority']}%</li>
                        <li><strong>Numeric match:</strong> {details['numeric']}%</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

                # Display documents in tabs
                doc_tab1, doc_tab2 = st.tabs(["Tailored Résumé", "Cover Letter"])

                with doc_tab1:
                    st.markdown("### Tailored Résumé")
                    st.markdown(resume_md)

                    # Download buttons
                    st.markdown("### Download Options")
                    download_container = st.container()
                    with download_container:
                        # Generate download links
                        safe_company = clean_company_name(company_name)
                        resume_md_link = get_pdf_download_link(resume_md, f"robison_resume-{safe_company}.md")
                        resume_pdf_link = get_pdf_download_link(resume_md, f"robison_resume-{safe_company}.pdf")
                        resume_docx_link = get_docx_download_link(resume_md, f"robison_resume-{safe_company}.docx")
                        
                        st.markdown(f"{resume_md_link} {resume_pdf_link} {resume_docx_link}", unsafe_allow_html=True)

                with doc_tab2:
                    st.markdown("### Cover Letter")
                    st.markdown(cover_letter_md)

                    # Download buttons
                    st.markdown("### Download Options")
                    download_container = st.container()
                    with download_container:
                        # Generate download links
                        cover_md_link = get_pdf_download_link(cover_letter_md, f"robison_coverletter-{safe_company}.md")
                        cover_pdf_link = get_pdf_download_link(cover_letter_md, f"robison_coverletter-{safe_company}.pdf")
                        cover_docx_link = get_docx_download_link(cover_letter_md, f"robison_coverletter-{safe_company}.docx")
                        
                        st.markdown(f"{cover_md_link} {cover_pdf_link} {cover_docx_link}", unsafe_allow_html=True)

if __name__ == "__main__":
    main()

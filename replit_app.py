#!/usr/bin/env python3
"""
replit_app.py – Simplified Streamlit GUI for the Job Application Assistant for Replit
====================================================================================
This is a simplified version of the Job Application Assistant that works on Replit.
"""

import os
import re
import json
import datetime
import streamlit as st
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Utility helpers
def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

STOPWORDS = {
    *{"the", "and", "for", "with", "you", "your", "our", "are", "this", "that", "will", "have", "has", "in", "of", "to", "on", "a", "an", "is", "be", "as", "at", "or", "we", "by", "it", "from", "their", "they", "his", "her", "he", "she"},
}

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.#/\-]{1,}")  # keep C++, .NET, etc.

def _tokens(text: str) -> list:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS]

def clean_company_name(company_name: str) -> str:
    """
    Clean up company name for use in filenames.
    """
    # Extract just the company name (not the job title)
    # First, split by common separators
    parts = re.split(r'[\s\-_:;,|]+', company_name)

    # Take just the first 1-3 words, depending on length
    if len(parts) > 0:
        if len(parts[0]) >= 8:  # If first word is long enough, just use that
            clean_name = parts[0]
        elif len(parts) > 1 and len(parts[0]) + len(parts[1]) < 15:
            # Use first two words if they're not too long together
            clean_name = f"{parts[0]}_{parts[1]}"
        else:
            # Otherwise just use the first word
            clean_name = parts[0]
    else:
        clean_name = "Company"

    # Remove any non-alphanumeric characters
    clean_name = re.sub(r'[^a-zA-Z0-9_]', '', clean_name)

    # Ensure it's not too long
    if len(clean_name) > 20:
        clean_name = clean_name[:20]

    return clean_name

# Simplified job description fetch function
def fetch_job_description(src: str) -> str:
    """Fetch and clean job description from URL or local HTML file."""
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

# Extract text from file
def extract_text_from_file(file_path_or_obj):
    """Extract text from various file formats."""
    if hasattr(file_path_or_obj, 'read'):
        # It's a file-like object
        return file_path_or_obj.getvalue().decode('utf-8')
    else:
        # It's a path
        with open(file_path_or_obj, 'r', encoding='utf-8') as f:
            return f.read()

# OpenAI résumé / cover‑letter generation
def generate_documents(job_text: str, resume_text: str, applicant_name: str,
                        role: str, company: str) -> tuple:
    """Generate tailored resume and cover letter."""
    import openai

    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        st.error("❌ OPENAI_API_KEY not set in environment.")
        return None, None

    system_prompt = (
        "You are an elite career coach and technical writer. "
        "Rewrite the applicant's résumé in Markdown format ONLY using their original achievements, "
        "rephrase titles & wording to align with the job description, and weave in ATS keywords. "
        "Then craft a concise cover letter (≤ 300 words) in Markdown format referencing the employer & role. "
        "Return STRICT JSON with keys 'resume' and 'cover_letter', both containing markdown strings."
    )

    user_payload = json.dumps({
        "today": datetime.date.today().isoformat(),
        "applicant_name": applicant_name,
        "company": company,
        "role": role,
        "job_description": job_text[:15000],
        "current_resume": resume_text[:15000]
    })

    try:
        chat = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_payload}],
            temperature=0.15,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )

        data = json.loads(chat.choices[0].message.content)
        if isinstance(data, dict) and "resume" in data and "cover_letter" in data:
            resume = data["resume"]
            cover_letter = data["cover_letter"]

            # Handle different types of content
            if isinstance(resume, list):
                resume = '\n'.join(resume)
            elif isinstance(resume, dict):
                resume = json.dumps(resume, indent=2)
            elif not isinstance(resume, str):
                resume = str(resume)

            if isinstance(cover_letter, list):
                cover_letter = '\n'.join(cover_letter)
            elif isinstance(cover_letter, dict):
                cover_letter = json.dumps(cover_letter, indent=2)
            elif not isinstance(cover_letter, str):
                cover_letter = str(cover_letter)

            return resume, cover_letter
        else:
            st.error(f"❌ Unexpected response format from OpenAI")
            return None, None
    except Exception as e:
        st.error(f"❌ Error generating documents: {e}")
        return None, None

# Simple keyword‑based FitScore
def compute_fit_score(jd_text: str, resume_md: str) -> tuple:
    """Compute how well the resume matches the job description."""
    jd_tokens = set(_tokens(jd_text))
    res_tokens = set(_tokens(resume_md))

    if not jd_tokens:
        return 0, {}

    overlap = jd_tokens & res_tokens
    coverage = len(overlap) / len(jd_tokens)  # 0‑1
    keyword_score = round(coverage * 100)

    # seniority alignment heuristic
    SENIORITY = ["intern", "junior", "associate", "mid", "senior", "lead", "principal", "director", "vp", "chief"]
    jd_sen = [s for s in SENIORITY if s in jd_tokens]
    res_sen = [s for s in SENIORITY if s in res_tokens]
    seniority_match = 100 if (jd_sen and any(s in res_sen for s in jd_sen)) or (not jd_sen) else 40

    # numeric years match
    jd_years = re.findall(r"(\d+)\s+years", jd_text.lower())
    res_years = re.findall(r"(\d+)\s+years", resume_md.lower())
    numeric_match = 100 if not jd_years else (80 if res_years else 30)

    # weighted total
    total = round(keyword_score * 0.4 + seniority_match * 0.2 + numeric_match * 0.1 + 0.3 * 100 * (len(overlap) > 0))

    breakdown = {
        "keyword_coverage": keyword_score,
        "seniority": seniority_match,
        "numeric": numeric_match,
        "overall": total,
    }
    return total, breakdown

# Generate download links
def get_download_link(text: str, filename: str, label: str):
    """Generate a download link for text content."""
    import base64
    b64 = base64.b64encode(text.encode()).decode()
    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}">{label}</a>'
    return href

# Main Streamlit app
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

    # Title and description
    st.title("Job-Apply Assistant")
    st.markdown("""
    Generate ATS-optimized résumé and cover letter for job applications.
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

    # Check if OpenAI API key is set
    if not openai_key:
        st.warning("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable before running the app.")

    # Generate button
    generate_button = st.button("Generate Résumé & Cover Letter",
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

    # Process when generate button is clicked
    if generate_button:
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
                        
                        # Extract role from first line of job description
                        first_line = job_description.split("\n", 1)[0]
                        role_title = first_line[:80]  # Limit to 80 chars
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

            with st.spinner("Generating tailored résumé and cover letter..."):
                # Generate documents
                try:
                    # Generate documents
                    resume_md, cover_letter_md = generate_documents(
                        job_description, resume_text, applicant_name, role_title, company_name
                    )
                    
                    if resume_md is None or cover_letter_md is None:
                        st.error("Failed to generate documents. Please try again.")
                        return

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
                                company_name = match.group(1).strip()
                                break

                    # Clean company name for filenames
                    safe_company = clean_company_name(company_name)

                    # Store company and role in session state
                    st.session_state.company_name = company_name
                    st.session_state.role_title = role_title

                    # Compute fit score
                    score, details = compute_fit_score(job_description, resume_md)
                    st.session_state.fit_score = (score, details)

                    # Save files to disk
                    try:
                        # Create output directory
                        os.makedirs(output_dir, exist_ok=True)

                        # Save markdown files
                        resume_md_path = os.path.join(output_dir, f"resume_{safe_company}.md")
                        cover_md_path = os.path.join(output_dir, f"cover_letter_{safe_company}.md")

                        with open(resume_md_path, "w") as f:
                            f.write(resume_md)
                        with open(cover_md_path, "w") as f:
                            f.write(cover_letter_md)

                    except Exception as e:
                        st.warning(f"Note: Could not save files to disk: {e}")
                        # Continue anyway since we have the documents in memory

                except Exception as e:
                    st.error(f"Error generating documents: {e}")
                    return

        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return

    # Display results if documents have been generated
    if st.session_state.documents:
        resume_md, cover_letter_md = st.session_state.documents
        company_name = st.session_state.company_name
        role_title = st.session_state.role_title
        score, details = st.session_state.fit_score

        st.success(f"✅ Generated documents for {role_title} at {company_name}")

        # Display fit score
        st.header("FitScore™")
        st.markdown(f"""
        <div style="background-color: {'#d4edda' if score >= 70 else '#fff3cd' if score >= 50 else '#f8d7da'}; 
                    padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <h3 style="margin-top: 0;">Overall Score: {score}/100</h3>
            <ul>
                <li>Keyword coverage: {details['keyword_coverage']}%</li>
                <li>Seniority match: {details['seniority']}%</li>
                <li>Numeric match: {details['numeric']}%</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # Display documents in tabs
        doc_tab1, doc_tab2 = st.tabs(["Tailored Résumé", "Cover Letter"])

        with doc_tab1:
            st.markdown("### Tailored Résumé")
            st.markdown(resume_md)

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(get_download_link(resume_md, f"robison_resume-{clean_company_name(company_name)}.md", "Download as Markdown"), unsafe_allow_html=True)

        with doc_tab2:
            st.markdown("### Cover Letter")
            st.markdown(cover_letter_md)

            # Download buttons
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(get_download_link(cover_letter_md, f"robison_coverletter-{clean_company_name(company_name)}.md", "Download as Markdown"), unsafe_allow_html=True)

if __name__ == "__main__":
    main()

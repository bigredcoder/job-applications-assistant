#!/usr/bin/env python3
"""
job_apply_gui.py – Streamlit GUI for the Job-Apply Assistant
===========================================================
A web interface for the Job-Apply Assistant that generates ATS-optimized résumé
and cover letter PDFs for a given job post URL and baseline résumé.

Usage:
    export OPENAI_API_KEY="sk-..."
    pip install streamlit
    streamlit run job_apply_gui.py
"""

import os
import re
import tempfile
import streamlit as st
from pathlib import Path
try:
    # Try importing from the wrapper first (for Replit compatibility)
    from job_apply_assistant_wrapper import (
        fetch_job_description,
        generate_documents,
        compute_fit_score,
        _md_to_pdf
    )
except ImportError:
    # Fall back to direct import for local development
    from job_apply_assistant import (
        fetch_job_description,
        generate_documents,
        compute_fit_score,
        _md_to_pdf
    )
from file_utils import extract_text_from_file
from pdf_utils import get_pdf_download_link, get_docx_download_link

def clean_company_name(company_name: str) -> str:
    """
    Clean up company name for use in filenames.

    Args:
        company_name: The raw company name

    Returns:
        A cleaned version suitable for filenames
    """
    # Special case for common phrases that aren't company names
    if company_name.lower() in ["company", "encourages creativity and continuous improvement"]:
        return "Company"

    # For company names extracted from the header, we want to preserve the exact name
    # but make it safe for filenames

    # Just replace spaces with underscores for filename compatibility
    # Keep hyphens as they are (e.g., "Harley-Davidson" should stay as "Harley-Davidson")
    clean_name = company_name.replace(" ", "_")

    # Remove any characters that aren't safe for filenames (but keep hyphens)
    clean_name = re.sub(r'[^a-zA-Z0-9_\-.]', '', clean_name)

    # Ensure it's not too long
    if len(clean_name) > 30:
        clean_name = clean_name[:30]

    return clean_name

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
                    elif "harley-davidson" in job_url.lower():
                        # Special case for Harley-Davidson
                        company_name = "Harley-Davidson"
                        st.info(f"Found company in URL: '{company_name}' (will verify from cover letter)")
                    elif "jobs." in job_url.lower() or "careers." in job_url.lower():
                        # Format: jobs.companyname.com or careers.companyname.com
                        url_match = re.search(r'(?:jobs|careers)\.([\w-]+)', job_url.lower())
                        if url_match:
                            extracted_name = url_match.group(1).replace('-', ' ').title()
                            company_name = extracted_name
                            st.info(f"Extracted from URL: '{company_name}' (will verify from cover letter)")

                    # Fetch job description from URL
                    job_description = fetch_job_description(job_url)
                    source = job_url

                    # Extract role information
                    first_lines = job_description.split("\n", 5)[:5]  # Get more lines for better extraction
                    role_title = first_lines[0][:80]

                    # Pattern 1: "at [Company]" pattern
                    company_match = re.search(r"at\s+([\w &.,-]{2,})(\s+in|\.|$)", " ".join(first_lines).lower())
                    if company_match:
                        company_name = company_match.group(1).strip().title()

                    # Pattern 2: Look for common company indicators
                    if company_name == "Company":
                        company_indicators = ["inc", "llc", "ltd", "corporation", "corp", "company", "co", "group"]
                        for line in first_lines:
                            for indicator in company_indicators:
                                pattern = fr'([\w &.,-]{{2,}}\s+{indicator})(\s|\.|,|$)'
                                match = re.search(pattern, line.lower())
                                if match:
                                    company_name = match.group(1).strip().title()
                                    break
                            if company_name != "Company":
                                break

                    # Pattern 3: Look for capitalized words that might be a company name
                    if company_name == "Company":
                        for line in first_lines:
                            # Look for sequences of capitalized words
                            cap_words_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', line)
                            if cap_words_match:
                                company_name = cap_words_match.group(1).strip()
                                break

                    st.write(f"Extracted company name: {company_name}")
                else:
                    # Use pasted job description
                    job_description = job_description_text
                    source = "pasted text"

                    # Use manually entered company name and job title
                    company_name = manual_company_name
                    role_title = manual_job_title
            except ValueError as e:
                st.error(f"Error fetching job description: {e}")
                st.info("Tip: If you're having trouble with a URL, try pasting the job description text directly.")
                raise

            st.session_state.company_name = company_name
            st.session_state.role_title = role_title

            # Read baseline resume (supports .txt, .md, .doc, .docx)
            try:
                if use_default_resume:
                    # Use the default resume file
                    default_resume_path = "brian_resume.txt"
                    resume_content = extract_text_from_file(default_resume_path)
                else:
                    # Use the uploaded resume file
                    resume_content = extract_text_from_file(resume_upload)
            except Exception as e:
                st.error(f"Error reading resume file: {e}")
                raise

            # Ensure output directory exists
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

        with st.spinner("Generating optimized documents..."):
            # Generate documents
            try:
                tailored_resume_md, cover_letter_md = generate_documents(
                    job_description, resume_content, applicant_name, role_title, company_name
                )
                st.session_state.documents = {
                    "resume": tailored_resume_md,
                    "cover_letter": cover_letter_md
                }

                # PRIMARY METHOD: Extract company name from cover letter
                # This is the most reliable method and takes precedence over any other extraction
                if "cover_letter" in st.session_state.documents:
                    cover_letter = st.session_state.documents["cover_letter"]

                    # Split the cover letter into lines for direct extraction
                    lines = cover_letter.split('\n')

                    # Find the line with "Hiring Manager" and get the next line
                    found_in_header = False
                    for i, line in enumerate(lines):
                        if "Hiring Manager" in line and i+1 < len(lines):
                            # The next line should be the company name
                            company_name = lines[i+1].strip()
                            st.success(f"✅ USING COMPANY NAME FROM COVER LETTER: '{company_name}'")
                            st.session_state.company_name = company_name
                            found_in_header = True
                            break

                    if found_in_header:
                        # Use the company name exactly as is for filenames
                        # Just replace spaces with underscores for filename compatibility
                        safe_company = company_name.replace(" ", "_")
                        st.write(f"Using exact company name: '{company_name}' → '{safe_company}' for filenames")
                    else:
                        # Only try other methods if we didn't find it in the header
                        # Fallback 1: Look for "position at [Company]" pattern
                        direct_match = re.search(r"position at ([A-Z][a-zA-Z0-9\s&.,-]{2,})(\.|\s|$)", cover_letter)
                        if direct_match:
                            extracted_company = direct_match.group(1).strip()
                            st.info(f"✅ Extracted company name from position: {extracted_company}")
                            company_name = extracted_company
                            st.session_state.company_name = company_name
                        else:
                            # Fallback 2: Look for any "at [Company]" in the first few paragraphs
                            paragraphs = cover_letter.split("\n\n")[:3]  # First 3 paragraphs
                            for para in paragraphs:
                                company_match = re.search(r"at\s+([A-Z][a-zA-Z0-9\s&.,-]{2,})(\.|\s|$)", para)
                                if company_match:
                                    extracted_company = company_match.group(1).strip()
                                    st.info(f"✅ Extracted company name from paragraph: {extracted_company}")
                                    company_name = extracted_company
                                    st.session_state.company_name = company_name
                                    break

                    # If still not found, try other patterns
                    if company_name == "Company":
                        # Try to find in the closing paragraph
                        closing_patterns = [
                            r"goals of ([A-Z][a-zA-Z0-9\s&.,-]{2,})(\.|\s|$)",
                            r"objectives of ([A-Z][a-zA-Z0-9\s&.,-]{2,})(\.|\s|$)",
                            r"vision of ([A-Z][a-zA-Z0-9\s&.,-]{2,})(\.|\s|$)",
                            r"mission of ([A-Z][a-zA-Z0-9\s&.,-]{2,})(\.|\s|$)"
                        ]

                        for pattern in closing_patterns:
                            closing_match = re.search(pattern, cover_letter)
                            if closing_match:
                                extracted_company = closing_match.group(1).strip()
                                st.info(f"✅ Extracted company name: {extracted_company}")
                                company_name = extracted_company
                                st.session_state.company_name = company_name
                                break

                    # LAST RESORT: Direct search for specific company names we know are problematic
                    if company_name == "Company":
                        # Check for specific company names in the text
                        specific_companies = ["LPL Financial", "Google", "Microsoft", "Amazon", "Apple", "Meta", "Facebook"]
                        for company in specific_companies:
                            if company in cover_letter:
                                st.info(f"✅ Found specific company name: {company}")
                                company_name = company
                                st.session_state.company_name = company
                                break
            except Exception as e:
                st.error(f"Error generating documents: {e}")
                raise

            # Calculate fit score
            score, details = compute_fit_score(job_description, tailored_resume_md)
            st.session_state.fit_score = details

            # Save documents
            try:
                # Clean up company name for filenames
                safe_company = clean_company_name(company_name)

                # Save markdown files
                resume_md_path = output_path / f"resume_{safe_company}.md"
                cover_md_path = output_path / f"cover_letter_{safe_company}.md"

                resume_md_path.write_text(tailored_resume_md, encoding="utf-8")
                cover_md_path.write_text(cover_letter_md, encoding="utf-8")

                # Create PDFs
                resume_pdf_path = output_path / f"robison_resume-{safe_company}.pdf"
                cover_pdf_path = output_path / f"robison_coverletter-{safe_company}.pdf"

                resume_pdf_success = _md_to_pdf(tailored_resume_md, resume_pdf_path)
                cover_pdf_success = _md_to_pdf(cover_letter_md, cover_pdf_path)

                # Store created files
                created_files = [resume_md_path, cover_md_path]
                if resume_pdf_success:
                    created_files.append(resume_pdf_path)
                else:
                    # If PDF generation failed, we'll use alternative formats
                    pass

                if cover_pdf_success:
                    created_files.append(cover_pdf_path)
                else:
                    # If PDF generation failed, we'll use alternative formats
                    pass

                st.session_state.created_files = created_files
            except Exception as e:
                st.error(f"Error saving files: {e}")
                raise

        st.success(f"Generated résumé and cover letter for {role_title} at {company_name}!")

    except Exception:
        # The specific error messages are already displayed above
        pass

# Display results if available
if st.session_state.documents and st.session_state.fit_score:
    # Create columns for resume and cover letter
    col1, col2 = st.columns(2)

    with col1:
        st.header("Tailored Résumé")
        st.markdown(st.session_state.documents['resume'])

        # Add download buttons for resume files
        resume_files = [f for f in st.session_state.created_files if "resume" in str(f)]
        pdf_found = False

        for file in resume_files:
            if file.exists():
                # Skip markdown files
                if file.suffix.lower() == ".md":
                    continue

                with open(file, 'rb') as f:
                    file_extension = file.suffix
                    st.download_button(
                        label=f"Download Résumé {file_extension}",
                        data=f,
                        file_name=file.name,
                        mime="application/octet-stream"
                    )

                # Check if we found a PDF file
                if file.suffix.lower() == ".pdf":
                    pdf_found = True

        # If no PDF file was found, offer alternative download formats
        if not pdf_found and st.session_state.documents:
            st.markdown("### Download Options")

            # Get company name for the filename
            company_name = st.session_state.company_name if st.session_state.company_name else "Company"
            safe_company = clean_company_name(company_name)

            # Generate the PDF download link using ReportLab
            pdf_link = get_pdf_download_link(
                st.session_state.documents['resume'],
                f"robison_resume-{safe_company}.pdf"
            )

            # Generate the DOCX download link
            docx_link = get_docx_download_link(
                st.session_state.documents['resume'],
                f"robison_resume-{safe_company}.docx"
            )

            # Display the download links
            if pdf_link:
                st.markdown(pdf_link, unsafe_allow_html=True)
            if docx_link:
                st.markdown(docx_link, unsafe_allow_html=True)

    with col2:
        st.header("Cover Letter")
        st.markdown(st.session_state.documents['cover_letter'])

        # Add download buttons for cover letter files
        cover_files = [f for f in st.session_state.created_files if "cover-letter" in str(f)]
        pdf_found = False

        for file in cover_files:
            if file.exists():
                # Skip markdown files
                if file.suffix.lower() == ".md":
                    continue

                with open(file, 'rb') as f:
                    file_extension = file.suffix
                    st.download_button(
                        label=f"Download Cover Letter {file_extension}",
                        data=f,
                        file_name=file.name,
                        mime="application/octet-stream"
                    )

                # Check if we found a PDF file
                if file.suffix.lower() == ".pdf":
                    pdf_found = True

        # If no PDF file was found, offer alternative download formats
        if not pdf_found and st.session_state.documents:
            st.markdown("### Download Options")

            # Get company name for the filename
            company_name = st.session_state.company_name if st.session_state.company_name else "Company"
            safe_company = clean_company_name(company_name)

            # Generate the PDF download link using ReportLab
            pdf_link = get_pdf_download_link(
                st.session_state.documents['cover_letter'],
                f"robison_coverletter-{safe_company}.pdf"
            )

            # Generate the DOCX download link
            docx_link = get_docx_download_link(
                st.session_state.documents['cover_letter'],
                f"robison_coverletter-{safe_company}.docx"
            )

            # Display the download links
            if pdf_link:
                st.markdown(pdf_link, unsafe_allow_html=True)
            if docx_link:
                st.markdown(docx_link, unsafe_allow_html=True)

    # Display fit score
    st.header("FitScore™")

    # Create a gauge-like visualization for the score
    score = st.session_state.fit_score['overall']
    color = "green" if score >= 80 else "orange" if score >= 60 else "red"

    st.markdown(f"""
    <div style="text-align: center;">
        <h1 style="color: {color}; font-size: 4rem;">{score}/100</h1>
    </div>
    """, unsafe_allow_html=True)

    # Score breakdown
    st.subheader("Score Breakdown")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Keyword Coverage", f"{st.session_state.fit_score['keyword_coverage']}%")

    with col2:
        st.metric("Seniority Match", f"{st.session_state.fit_score['seniority']}%")

    with col3:
        st.metric("Numeric Match", f"{st.session_state.fit_score['numeric']}%")

    # Tips based on score
    st.subheader("Improvement Tips")

    if st.session_state.fit_score['keyword_coverage'] < 70:
        st.warning("Consider adding more keywords from the job description to your résumé.")

    if st.session_state.fit_score['seniority'] < 80:
        st.warning("The seniority level in your résumé may not match what the job requires.")

    if st.session_state.fit_score['numeric'] < 60:
        st.warning("Check if your years of experience match what the job requires.")

# Footer
st.markdown("---")
st.markdown("Job-Apply Assistant - Generate ATS-optimized résumés and cover letters")

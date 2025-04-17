#!/usr/bin/env python3
"""
Test script for Job-Apply Assistant
"""

import os
import json
import re
from pathlib import Path
import openai

# Set your API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set")
    exit(1)

openai.api_key = api_key

def read_file(file_path):
    """Read file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        exit(1)

def generate_documents(job_text, resume_text, applicant_name, role, company):
    """Generate tailored resume and cover letter"""
    system_prompt = (
        "You are an elite career coach and technical writer. "
        "Rewrite the applicant's résumé in Markdown format ONLY using their original achievements, "
        "rephrase titles & wording to align with the job description, and weave in ATS keywords. "
        "Then craft a concise cover letter (≤ 300 words) in Markdown format referencing the employer & role. "
        "Return STRICT JSON with keys 'resume' and 'cover_letter', both containing markdown strings."
    )

    user_payload = json.dumps({
        "applicant_name": applicant_name,
        "company": company,
        "role": role,
        "job_description": job_text[:15000],
        "current_resume": resume_text[:15000]
    })

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload}
            ],
            temperature=0.15,
            max_tokens=2048,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        if "resume" in data and "cover_letter" in data:
            return data["resume"], data["cover_letter"]
        else:
            print(f"Error: Unexpected response format: {data}")
            exit(1)

    except Exception as e:
        print(f"Error generating documents: {e}")
        exit(1)

def save_document(content, file_path):
    """Save document to file"""
    try:
        # Handle different types of content
        if isinstance(content, list):
            content = '\n'.join(content)
        elif isinstance(content, dict):
            content = json.dumps(content, indent=2)
        elif not isinstance(content, str):
            content = str(content)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved: {file_path}")
    except Exception as e:
        print(f"Error saving file {file_path}: {e}")

def main():
    # Read job description and resume
    job_text = read_file("sample_job.html")
    resume_text = read_file("baseline.txt")

    # Extract company and role
    role = "Senior Software Engineer"
    company = "TechInnovate Inc."
    safe_company = company.replace(" ", "_").replace("/", "-")

    # Generate documents
    print(f"Generating documents for {role} at {company}...")
    resume_md, cover_letter_md = generate_documents(
        job_text, resume_text, "Brian Robison", role, company
    )

    # Create output directory
    output_dir = Path("./generated")
    output_dir.mkdir(exist_ok=True)

    # Save documents
    save_document(resume_md, output_dir / f"resume_{safe_company}.md")
    save_document(cover_letter_md, output_dir / f"cover_letter_{safe_company}.md")

    print("\nDone! Files created in ./generated")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Simplified version of job_apply_assistant.py for Replit compatibility.
This version doesn't use the readability-lxml package which causes issues on Replit.
"""
import os, sys, argparse, json, re, datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from file_utils import extract_text_from_file

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
    """Fetch and clean job description from URL or local HTML file.
    
    This is a simplified version that doesn't use readability-lxml.
    """
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

# OpenAI résumé / cover‑letter generation
def generate_documents(job_text: str, resume_text: str, applicant_name: str,
                        role: str, company: str) -> tuple:
    import openai

    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        sys.exit("❌ OPENAI_API_KEY not set in environment.")

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
            sys.exit(f"❌ Unexpected response format: {data}")
    except (json.JSONDecodeError, KeyError, Exception) as e:
        sys.exit(f"❌ Error: {e}")

# Simple keyword‑based FitScore
def compute_fit_score(jd_text: str, resume_md: str) -> tuple:
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

# PDF conversion helper
def _md_to_pdf(md_text: str, pdf_path: Path) -> bool:
    try:
        import markdown
        from weasyprint import HTML
    except ImportError:
        print("⚠️  PDF dependencies missing – install 'markdown' and 'weasyprint' to enable PDF export.")
        return False
    
    try:
        html_body = markdown.markdown(md_text, extensions=["extra", "tables"])
        css = """body { font-family: Helvetica, Arial, sans-serif; line-height:1.45; } h1,h2{margin-bottom:6px;} ul{margin-left:14px;} li{margin-bottom:3px;}"""
        HTML(string=f"<style>{css}</style>{html_body}").write_pdf(str(pdf_path))
        return True
    except Exception as e:
        print(f"⚠️  Error creating PDF: {e}")
        return False

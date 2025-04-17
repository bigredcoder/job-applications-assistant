#!/usr/bin/env python3
"""
job_apply_assistant.py – Tailor‑made résumé & cover‑letter generator **with FitScore & PDF export**
==============================================================================================
CLI workflow
-----------
1. `export OPENAI_API_KEY="sk‑..."`
2. `pip install openai requests beautifulsoup4 readability‑lxml markdown weasyprint`
3. `python job_apply_assistant.py --url "<JOB_LINK>" --resume my_resume.txt --name "Brian Robison" --output ./out`

Files created in `./out/`:
    • `resume_<company>.md`
    • `cover_letter_<company>.md`
    • `robison-resume-<company>.pdf`
    • `robison-cover-letter-<company>.pdf`

At the end of the run you'll also see a **FitScore (0–100)** and a short breakdown of which keyword buckets were matched.
"""
from __future__ import annotations
import os, sys, argparse, json, re, datetime
from pathlib import Path
from typing import Tuple, List, Set
import requests, bs4, readability
from file_utils import extract_text_from_file

# Optional PDF deps
_md = None
_HTML = None
try:
    import markdown as _md
    try:
        from weasyprint import HTML as _HTML
    except (ImportError, OSError) as e:
        print(f"Warning: weasyprint not available - {e}")
        _HTML = None
except ImportError:
    print("Warning: markdown not available")

# ──────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

STOPWORDS: Set[str] = {
    *{"the", "and", "for", "with", "you", "your", "our", "are", "this", "that", "will", "have", "has", "in", "of", "to", "on", "a", "an", "is", "be", "as", "at", "or", "we", "by", "it", "from", "their", "they", "his", "her", "he", "she"},
}

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.#/\-]{1,}")  # keep C++, .NET, etc.

def _tokens(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS]

def clean_company_name(company_name: str) -> str:
    """
    Clean up company name for use in filenames.

    Args:
        company_name: The raw company name

    Returns:
        A cleaned version suitable for filenames
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

# ──────────────────────────────────────────────────────────────
# Job description fetch
# ──────────────────────────────────────────────────────────────

def fetch_job_description(src: str) -> str:
    """Fetch and clean job description from URL or local HTML file.

    Args:
        src: URL or path to local HTML file

    Returns:
        Cleaned job description text

    Raises:
        ValueError: If there's an error fetching or parsing the job description
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

                # Add LinkedIn-specific handling
                if "linkedin.com" in src:
                    # For LinkedIn, we need to use a more sophisticated approach
                    print("LinkedIn URL detected. Using enhanced scraping method...")

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

        # Parse the HTML content
        try:
            # Create BeautifulSoup object first for special handling
            soup = bs4.BeautifulSoup(html, "html.parser")

            # Special handling for LinkedIn
            if "linkedin.com" in src:
                # Try to find the job description section
                job_description_section = None

                # Look for common LinkedIn job description containers
                for selector in [
                    ".description__text",
                    ".show-more-less-html__markup",
                    "#job-details",
                    ".jobs-description__content",
                    ".jobs-box__html-content"
                ]:
                    elements = soup.select(selector)
                    if elements:
                        job_description_section = elements[0]
                        break

                if job_description_section:
                    # Found a LinkedIn job description section
                    return _strip_html(job_description_section.get_text("\n", strip=True))

            # If no special handling worked, use readability
            doc = readability.Document(html)
            main_html = doc.summary(html_partial=True)
            soup = bs4.BeautifulSoup(main_html, "html.parser")

            # Look for large text blocks
            candidates = [el for el in soup.find_all(string=True) if len(el) > 100]  # Use string instead of text

            if not candidates:
                # If no long text blocks found, get all text
                return _strip_html(soup.get_text("\n", strip=True))

            best = max(candidates, key=len)
            return _strip_html(str(best))
        except Exception as e:
            raise ValueError(f"Error parsing HTML content: {e}")
    except ValueError as e:
        # Re-raise ValueError to be caught by the caller
        raise
    except Exception as e:
        # Catch any other exceptions and convert to ValueError
        raise ValueError(f"Unexpected error: {e}")

# ──────────────────────────────────────────────────────────────
# OpenAI résumé / cover‑letter generation
# ──────────────────────────────────────────────────────────────

def generate_documents(job_text: str, resume_text: str, applicant_name: str,
                        role: str, company: str) -> Tuple[str, str]:
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

# ──────────────────────────────────────────────────────────────
# Simple keyword‑based FitScore
# ──────────────────────────────────────────────────────────────

def compute_fit_score(jd_text: str, resume_md: str) -> tuple[int, dict[str, float]]:
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

# ──────────────────────────────────────────────────────────────
# PDF conversion helper
# ──────────────────────────────────────────────────────────────

def _md_to_pdf(md_text: str, pdf_path: Path) -> bool:
    if _md is None or _HTML is None:
        print("⚠️  PDF dependencies missing – install 'markdown' and 'weasyprint' to enable PDF export.")
        return False
    try:
        html_body = _md.markdown(md_text, extensions=["extra", "tables"])
        css = """body { font-family: Helvetica, Arial, sans-serif; line-height:1.45; } h1,h2{margin-bottom:6px;} ul{margin-left:14px;} li{margin-bottom:3px;}"""
        _HTML(string=f"<style>{css}</style>{html_body}").write_pdf(str(pdf_path))
        return True
    except Exception as e:
        print(f"⚠️  Error creating PDF: {e}")
        return False

# ──────────────────────────────────────────────────────────────
# Main CLI entry
# ──────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Generate tailored résumé & cover letter (Markdown + PDF) and compute FitScore.")
    ap.add_argument("--url", required=True, help="Job post URL or local HTML file")
    ap.add_argument("--resume", required=True, help="Baseline résumé text/markdown path")
    ap.add_argument("--name", required=True, help="Applicant full name")
    ap.add_argument("--output", default="./generated", help="Output directory")
    args = ap.parse_args()

    try:
        # Fetch job description
        try:
            job_text = fetch_job_description(args.url)
        except ValueError as e:
            print(f"\n❌ Error fetching job description: {e}")
            return

        # Read resume text from file
        try:
            resume_text = extract_text_from_file(args.resume)
        except Exception as e:
            print(f"\n❌ Error reading resume file: {e}")
            return

        # Extract company and role information
        first_lines = job_text.split("\n", 5)[:5]  # Get more lines for better extraction
        role = first_lines[0][:80]

        # Try multiple patterns to extract company name
        company = "Company"  # Default fallback

        # Pattern 1: "at [Company]" pattern
        company_match = re.search(r"at\s+([\w &.,-]{2,})(\s+in|\.|$)", " ".join(first_lines).lower())
        if company_match:
            company = company_match.group(1).strip().title()

        # Pattern 2: Look for common company indicators
        if company == "Company":
            company_indicators = ["inc", "llc", "ltd", "corporation", "corp", "company", "co", "group"]
            for line in first_lines:
                for indicator in company_indicators:
                    pattern = fr'([\w &.,-]{{2,}}\s+{indicator})(\s|\.|,|$)'
                    match = re.search(pattern, line.lower())
                    if match:
                        company = match.group(1).strip().title()
                        break
                if company != "Company":
                    break

        # Pattern 3: Look for capitalized words that might be a company name
        if company == "Company":
            for line in first_lines:
                # Look for sequences of capitalized words
                cap_words_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', line)
                if cap_words_match:
                    company = cap_words_match.group(1).strip()
                    break

        print(f"Extracted company name: {company}")
        safe_company = clean_company_name(company)

        # Generate documents
        try:
            tailored_resume_md, cover_letter_md = generate_documents(job_text, resume_text, args.name, role, company)
        except Exception as e:
            print(f"\n❌ Error generating documents: {e}")
            return

        # Calculate fit score
        score, details = compute_fit_score(job_text, tailored_resume_md)

        # Create output directory and save files
        try:
            out = Path(args.output)
            out.mkdir(parents=True, exist_ok=True)

            resume_md_path = out / f"resume_{safe_company}.md"
            cover_md_path = out / f"cover_letter_{safe_company}.md"

            resume_md_path.write_text(tailored_resume_md, encoding="utf-8")
            cover_md_path.write_text(cover_letter_md, encoding="utf-8")

            # PDFs
            resume_pdf_path = out / f"robison_resume-{safe_company}.pdf"
            cover_pdf_path = out / f"robison_coverletter-{safe_company}.pdf"
            resume_pdf_success = _md_to_pdf(tailored_resume_md, resume_pdf_path)
            cover_pdf_success = _md_to_pdf(cover_letter_md, cover_pdf_path)

            print("\n✅ Files created in", out.resolve())
            print(f"  • {resume_md_path.name}")
            print(f"  • {cover_md_path.name}")
            if resume_pdf_success:
                print(f"  • {resume_pdf_path.name}")
            else:
                print(f"  • [skipped] {resume_pdf_path.name}")
            if cover_pdf_success:
                print(f"  • {cover_pdf_path.name}")
            else:
                print(f"  • [skipped] {cover_pdf_path.name}")

            print("\nℹ️  FitScore:")
            print(f"  Overall: {details['overall']} / 100")
            print(f"    Keyword coverage: {details['keyword_coverage']}%")
            print(f"    Seniority match:  {details['seniority']}%")
            print(f"    Numeric match:    {details['numeric']}%")

        except Exception as e:
            print(f"\n❌ Error saving files: {e}")
            return

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return

if __name__ == "__main__":
    main()

# Job Application Assistant

A Streamlit application that helps generate ATS-optimized résumés and cover letters for job applications.

## Features

- Fetch job descriptions from URLs or paste them directly
- Generate tailored résumés and cover letters using AI
- Calculate a FitScore to evaluate how well your résumé matches the job description
- Export documents as PDF, DOCX, or Markdown

## Running the Application

### On Replit

1. Click the "Run" button at the top of the Replit interface
2. Wait for the dependencies to install
3. The application will automatically start and open in a new tab

### Locally

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set your OpenAI API key:
   ```
   export OPENAI_API_KEY="your-api-key"
   ```

3. Run the application:
   ```
   streamlit run job_apply_gui.py
   ```

## Requirements

- Python 3.7+
- OpenAI API key
- Internet connection for fetching job descriptions from URLs

## License

This project is licensed under the MIT License - see the LICENSE file for details.

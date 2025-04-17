#!/usr/bin/env python3
"""
Wrapper module to ensure compatibility with Replit's file structure.
This file re-exports all the functions from job_apply_assistant.py
"""

# Import all functions from the original module
from job_apply_assistant import (
    fetch_job_description,
    generate_documents,
    compute_fit_score,
    _md_to_pdf,
    clean_company_name,
    _strip_html,
    _tokens,
    STOPWORDS,
    TOKEN_RE
)

# Re-export all functions
__all__ = [
    'fetch_job_description',
    'generate_documents',
    'compute_fit_score',
    '_md_to_pdf',
    'clean_company_name',
    '_strip_html',
    '_tokens',
    'STOPWORDS',
    'TOKEN_RE'
]

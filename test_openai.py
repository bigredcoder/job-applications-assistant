#!/usr/bin/env python3
"""
Test script for OpenAI API
"""

import os
import json
import openai

# Set your API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set")
    exit(1)

openai.api_key = api_key

# Test the API
try:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Generate a JSON with two fields: 'resume' and 'cover_letter', each containing a short sample text."}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    
    # Print the response
    print("Response received:")
    content = response.choices[0].message.content
    print(content)
    
    # Parse the JSON
    data = json.loads(content)
    print("\nParsed JSON:")
    print(f"Resume: {data.get('resume', 'Not found')[:50]}...")
    print(f"Cover Letter: {data.get('cover_letter', 'Not found')[:50]}...")
    
except Exception as e:
    print(f"Error: {e}")

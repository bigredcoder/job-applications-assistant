#!/bin/bash

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create a symlink for Replit compatibility
if [ -d "/home/runner/workspace" ]; then
    echo "Creating symlinks for Replit compatibility..."
    # Create symlinks for all Python files in the current directory
    for file in *.py; do
        if [ -f "$file" ]; then
            echo "Creating symlink for $file"
            ln -sf "$(pwd)/$file" "/home/runner/workspace/$file"
        fi
    done

    # Create symlink for requirements.txt
    ln -sf "$(pwd)/requirements.txt" "/home/runner/workspace/requirements.txt"

    # Create symlink for brian_resume.txt
    ln -sf "$(pwd)/brian_resume.txt" "/home/runner/workspace/brian_resume.txt"
fi

# Run the application
echo "Starting Streamlit application..."
streamlit run job_apply_gui.py

#!/usr/bin/env python3
"""
Base Agent class for Job Application Assistant.
This provides the foundation for all specialized agents.
"""

import os
import json
import openai
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Tuple

class BaseAgent(ABC):
    """Base class for all agents in the Job Application Assistant."""
    
    def __init__(self, name: str, description: str, model: str = "gpt-4o-mini"):
        """
        Initialize the base agent.
        
        Args:
            name: The name of the agent
            description: A brief description of what the agent does
            model: The OpenAI model to use for this agent
        """
        self.name = name
        self.description = description
        self.model = model
        self.system_prompt = self._get_system_prompt()
        
        # Ensure OpenAI API key is set
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Each agent should implement this to define its specialized behavior.
        
        Returns:
            The system prompt string
        """
        pass
    
    def run(self, input_data: Dict[str, Any], temperature: float = 0.2) -> Dict[str, Any]:
        """
        Run the agent with the given input data.
        
        Args:
            input_data: Dictionary containing the input data for the agent
            temperature: Temperature setting for the model (0.0 to 1.0)
            
        Returns:
            Dictionary containing the agent's output
        """
        # Convert input data to JSON string
        user_message = json.dumps(input_data)
        
        # Call the OpenAI API
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            return {
                "error": True,
                "message": f"Error running agent {self.name}: {str(e)}"
            }
    
    def get_info(self) -> Dict[str, str]:
        """
        Get information about this agent.
        
        Returns:
            Dictionary with agent information
        """
        return {
            "name": self.name,
            "description": self.description,
            "model": self.model
        }

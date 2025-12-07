"""
THE KRAKEN DREAMS - LLM Provider Integration
Handles communication with Ollama (local) and Groq (cloud) LLM providers.

This module provides a unified interface for generating text with different
LLM backends, including error handling and rate limit management.
"""

import requests
import time
import json

# =============================================================================
# GROQ AVAILABLE MODELS
# =============================================================================
# Static list of Groq models since they don't have a public list endpoint.
# Update this list when new models become available.
# =============================================================================

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.2-1b-preview",
    "llama-3.2-3b-preview",
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it"
]


class LLMProvider:
    """Base class for LLM providers."""
    
    def generate(self, model, prompt):
        """
        Generate text from a prompt.
        
        Args:
            model (str): The model name to use
            prompt (str): The input prompt
            
        Returns:
            str: The generated text, or empty string on error
        """
        raise NotImplementedError


class OllamaProvider(LLMProvider):
    """
    Ollama local LLM provider.
    
    Requires Ollama to be running locally (default: http://localhost:11434).
    Supports streaming responses and various open-source models.
    """
    
    def __init__(self, base_url="http://localhost:11434"):
        """
        Initialize the Ollama provider.
        
        Args:
            base_url (str): The Ollama API base URL
        """
        self.base_url = base_url.rstrip('/')
    
    def get_models(self):
        """
        Fetch available models from Ollama.
        
        Returns:
            list: List of model names, or empty list on error
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m['name'] for m in data.get('models', [])]
        except requests.RequestException:
            pass
        return []
    
    def is_available(self):
        """
        Check if Ollama is running and accessible.
        
        Returns:
            bool: True if Ollama is available
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def generate(self, model, prompt):
        """
        Generate text using Ollama.
        
        Args:
            model (str): The model name (e.g., 'llama3.1:8b')
            prompt (str): The input prompt
            
        Returns:
            str: The generated text, or empty string on error
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=300  # 5 minute timeout for long generations
            )
            
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                return f"[Ollama Error: {response.status_code}]"
                
        except requests.Timeout:
            return "[Ollama Error: Request timed out]"
        except requests.RequestException as e:
            return f"[Ollama Error: {str(e)}]"


class GroqProvider(LLMProvider):
    """
    Groq cloud LLM provider.
    
    Uses the Groq API for fast cloud-based inference.
    Free tier includes 30 requests/minute and 14,400 requests/day.
    """
    
    def __init__(self, api_key, base_url="https://api.groq.com/openai/v1/chat/completions"):
        """
        Initialize the Groq provider.
        
        Args:
            api_key (str): Your Groq API key (starts with 'gsk_')
            base_url (str): The Groq API endpoint
        """
        self.api_key = api_key
        self.base_url = base_url
    
    @staticmethod
    def get_models():
        """
        Get available Groq models.
        
        Returns:
            list: List of model names
        """
        return GROQ_MODELS.copy()
    
    def is_available(self):
        """
        Check if the Groq API key is configured.
        
        Returns:
            bool: True if API key is set
        """
        return bool(self.api_key)
    
    def generate(self, model, prompt, max_retries=3):
        """
        Generate text using Groq API with rate limit handling.
        
        Automatically retries on rate limit errors with exponential backoff.
        
        Args:
            model (str): The model name
            prompt (str): The input prompt
            max_retries (int): Maximum retry attempts for rate limits
            
        Returns:
            str: The generated text, or empty string on error
        """
        if not self.api_key:
            return "[Groq Error: No API key configured]"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data['choices'][0]['message']['content']
                    
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt * 10  # 10, 20, 40 seconds
                    time.sleep(wait_time)
                    continue
                    
                else:
                    return f"[Groq Error: {response.status_code} - {response.text}]"
                    
            except requests.Timeout:
                return "[Groq Error: Request timed out]"
            except requests.RequestException as e:
                return f"[Groq Error: {str(e)}]"
        
        return "[Groq Error: Rate limit exceeded after retries]"


def create_provider(provider_type, config):
    """
    Factory function to create an LLM provider instance.
    
    Args:
        provider_type (str): 'ollama' or 'groq'
        config (dict): Configuration dictionary with API keys/URLs
        
    Returns:
        LLMProvider: The configured provider instance
    """
    if provider_type.lower() == 'ollama':
        return OllamaProvider(config.get('ollama_url', 'http://localhost:11434'))
    elif provider_type.lower() == 'groq':
        return GroqProvider(
            config.get('groq_api_key', ''),
            config.get('groq_url', 'https://api.groq.com/openai/v1/chat/completions')
        )
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")

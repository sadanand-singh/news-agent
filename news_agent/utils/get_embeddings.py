"""Utility for getting embeddings using various providers."""

import os
from typing import List, Optional

import numpy as np
from dotenv import load_dotenv

try:
    from langchain_ollama import OllamaEmbeddings
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    OllamaEmbeddings = None

try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAIEmbeddings = None

load_dotenv()


def get_embeddings(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs,
):
    """
    Get an embedding model based on environment variables or provided parameters.
    
    Args:
        provider: The provider to use (ollama, openai)
        model_name: The model name for the specified provider
        **kwargs: Additional arguments to pass to the embedding model
        
    Returns:
        Embedding model instance
        
    Raises:
        ValueError: If provider is not supported
        ImportError: If required package is not installed
    """
    provider = provider or os.getenv('EMBEDDING_PROVIDER', 'ollama').lower()
    model_name = model_name or os.getenv('EMBEDDING_MODEL_NAME', 'bge-large')
    
    if provider == 'ollama':
        if not OLLAMA_AVAILABLE:
            raise ImportError(
                'langchain-ollama is not installed. Install with: pip install langchain-ollama'
            )
        return OllamaEmbeddings(model=model_name, **kwargs)
    
    elif provider == 'openai':
        if not OPENAI_AVAILABLE:
            raise ImportError(
                'langchain-openai is not installed. Install with: pip install langchain-openai'
            )
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError('OPENAI_API_KEY environment variable is required')
        return OpenAIEmbeddings(model=model_name, openai_api_key=api_key, **kwargs)
    
    else:
        supported_providers = ['ollama', 'openai']
        raise ValueError(
            f'Unsupported embedding provider: {provider}. Supported providers: {", ".join(supported_providers)}'
        )


def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        float: Cosine similarity score between 0 and 1
    """
    arr1 = np.array(embedding1)
    arr2 = np.array(embedding2)
    
    # Calculate cosine similarity
    dot_product = np.dot(arr1, arr2)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    
    # Convert from [-1, 1] to [0, 1] range
    return (similarity + 1) / 2
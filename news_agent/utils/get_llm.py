import os
from typing import Optional

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

# Import all supported chat models
try:
    from langchain_openai import ChatOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    ChatGoogleGenerativeAI = None

try:
    from langchain_ollama import ChatOllama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ChatOllama = None

try:
    from langchain_aws import ChatBedrock

    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False
    ChatBedrock = None


load_dotenv()


def get_llm(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    model_type: Optional[str] = None,
    **kwargs,
) -> BaseChatModel:
    """
    Get a LangChain chat model based on environment variables or provided parameters.

    Environment variables used:
    - MAIN_MODEL_PROVIDER: The provider to use (anthropic, google, openai, ollama, bedrock)
    - MODEL_NAME: The model name for the specified provider
    - OPENAI_API_KEY: OpenAI API key
    - ANTHROPIC_API_KEY: Anthropic API key
    - GOOGLE_API_KEY: Google API key
    - AWS_ACCESS_KEY_ID: AWS Access Key ID (for Bedrock)
    - AWS_SECRET_ACCESS_KEY: AWS Secret Access Key (for Bedrock)
    - AWS_DEFAULT_REGION: AWS Default Region (for Bedrock)

    Args:
        provider: Override the MAIN_MODEL_PROVIDER env var
        model_name: Override the MODEL_NAME env var
        temperature: Model temperature (default: 0.0)
        max_tokens: Maximum tokens for response
        model_type: The type of model to use (small, main)
        **kwargs: Additional arguments to pass to the chat model

    Returns:
        BaseChatModel: The configured chat model

    Raises:
        ValueError: If provider is not supported or API key is missing
        ImportError: If required package is not installed
    """

    # Get provider and model from env vars if not provided
    if model_type is not None:
        if model_type == 'small':
            provider = os.getenv('SMALL_MODEL_PROVIDER')
            model_name = os.getenv('SMALL_MODEL_NAME')
        elif model_type == 'main':
            provider = os.getenv('MAIN_MODEL_PROVIDER')
            model_name = os.getenv('MAIN_MODEL_NAME')
        elif model_type == 'fix':
            provider = os.getenv('FIX_MODEL_PROVIDER', 'anthropic')
            model_name = os.getenv('FIX_MODEL_NAME', 'claude-3-5-sonnet-20240620')
        else:
            raise ValueError(f'Invalid model type: {model_type}')
    else:
        provider = provider or os.getenv('MAIN_MODEL_PROVIDER', '').lower()
        model_name = model_name or os.getenv('MAIN_MODEL_NAME')

    if not provider:
        raise ValueError(
            'Provider must be specified either as parameter or MAIN_MODEL_PROVIDER env var'
        )

    if not model_name:
        raise ValueError(
            'Model name must be specified either as parameter or MAIN_MODEL_NAME env var'
        )

    # Common parameters
    model_kwargs = {'temperature': temperature, **kwargs}

    if max_tokens:
        model_kwargs['max_tokens'] = max_tokens

    # OpenAI
    if provider == 'openai':
        if not OPENAI_AVAILABLE:
            raise ImportError(
                'langchain-openai is not installed. Install with: pip install langchain-openai'
            )

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError('OPENAI_API_KEY environment variable is required')

        return ChatOpenAI(model=model_name, openai_api_key=api_key, **model_kwargs)

    # Anthropic
    elif provider == 'anthropic':
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                'langchain-anthropic is not installed. Install with: pip install langchain-anthropic'
            )

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError('ANTHROPIC_API_KEY environment variable is required')

        return ChatAnthropic(model=model_name, anthropic_api_key=api_key, **model_kwargs)

    # Google Gemini
    elif provider == 'google':
        if not GOOGLE_AVAILABLE:
            raise ImportError(
                'langchain-google-genai is not installed. Install with: pip install langchain-google-genai'
            )

        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError('GOOGLE_API_KEY environment variable is required')

        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, **model_kwargs)

    # Ollama (local)
    elif provider == 'ollama':
        if not OLLAMA_AVAILABLE:
            raise ImportError(
                'langchain-ollama is not installed. Install with: pip install langchain-ollama'
            )

        # Ollama doesn't require API key, runs locally
        return ChatOllama(model=model_name, **model_kwargs)

    # AWS Bedrock
    elif provider == 'bedrock':
        if not BEDROCK_AVAILABLE:
            raise ImportError(
                'langchain-aws is not installed. Install with: pip install langchain-aws'
            )

        # AWS credentials can be provided via environment variables or AWS profile
        # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
        # or configured via AWS CLI/boto3 default credentials

        # Get region from environment variable or default to us-east-1
        region_name = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

        # Pass region_name to the model
        model_kwargs['region_name'] = region_name

        return ChatBedrock(model_id=model_name, **model_kwargs)

    else:
        supported_providers = ['openai', 'anthropic', 'google', 'ollama', 'bedrock']
        raise ValueError(
            f'Unsupported provider: {provider}. Supported providers: {", ".join(supported_providers)}'
        )


def get_available_providers() -> list[str]:
    """
    Get a list of available providers based on installed packages.

    Returns:
        list[str]: List of available provider names
    """
    available = []

    if OPENAI_AVAILABLE:
        available.append('openai')
    if ANTHROPIC_AVAILABLE:
        available.append('anthropic')
    if GOOGLE_AVAILABLE:
        available.append('google')
    if OLLAMA_AVAILABLE:
        available.append('ollama')
    if BEDROCK_AVAILABLE:
        available.append('bedrock')

    return available


def check_provider_requirements(provider: str) -> dict:
    """
    Check if a provider is available and what environment variables are required.

    Args:
        provider: The provider name to check

    Returns:
        dict: Dictionary with 'available' and 'required_env_vars' keys
    """
    provider_checks = {
        'openai': {
            'available': OPENAI_AVAILABLE,
            'required_env_vars': ['OPENAI_API_KEY'],
            'package': 'langchain-openai',
        },
        'anthropic': {
            'available': ANTHROPIC_AVAILABLE,
            'required_env_vars': ['ANTHROPIC_API_KEY'],
            'package': 'langchain-anthropic',
        },
        'google': {
            'available': GOOGLE_AVAILABLE,
            'required_env_vars': ['GOOGLE_API_KEY'],
            'package': 'langchain-google-genai',
        },
        'ollama': {
            'available': OLLAMA_AVAILABLE,
            'required_env_vars': [],
            'package': 'langchain-ollama',
        },
        'bedrock': {
            'available': BEDROCK_AVAILABLE,
            'required_env_vars': ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'],
            'optional_env_vars': ['AWS_DEFAULT_REGION'],
            'package': 'langchain-aws',
        },
    }

    return provider_checks.get(
        provider, {'available': False, 'required_env_vars': [], 'package': 'unknown'}
    )

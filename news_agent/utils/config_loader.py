"""Configuration loader utility for loading YAML configuration files."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigLoader:
    """Loads configuration from YAML files with support for local overrides."""

    def __init__(self, config_dir: str, config_name: str = "config.yaml"):
        """
        Initialize the config loader.

        Args:
            config_dir: Directory containing the config files
            config_name: Base name of the config file (default: config.yaml)
        """
        self.config_dir = Path(config_dir)
        self.config_name = config_name
        self._config: Optional[Dict[str, Any]] = None

    def load_config(self, agent_name: str = None) -> Dict[str, Any]:
        """
        Load configuration from YAML files.

        First loads the base config.yaml, then overlays any config.local.yaml
        if it exists. This allows for local development overrides.

        Returns:
            Dict containing the merged configuration
        """
        if self._config is not None:
            return self._config

        # Load base config
        base_config_path = self.config_dir / self.config_name
        if not base_config_path.exists():
            raise FileNotFoundError(f"Base config file not found: {base_config_path}")

        with open(base_config_path, 'r') as f:
            config = yaml.safe_load(f) or {}

        # Load local config override if it exists
        # Look for local config in global config folder
        agent_name = agent_name or getattr(self, '_agent_name', None)
        if agent_name:
            global_config_dir = Path(__file__).parent.parent.parent / "configs"
            local_config_path = global_config_dir / f"{agent_name}.config.yaml"

            if local_config_path.exists():
                with open(local_config_path, 'r') as f:
                    local_config = yaml.safe_load(f) or {}
                    config = self._merge_configs(config, local_config)

        self._config = config
        return config

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'models.main_model.provider')
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        config = self.load_config()
        keys = key.split('.')

        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set_env_vars(self, agent_name: str = None) -> None:
        """
        Set environment variables from the configuration.

        This method sets environment variables that the existing code expects,
        allowing for a gradual migration from env vars to YAML config.
        """
        agent_name = agent_name or getattr(self, '_agent_name', None)
        config = self.load_config(agent_name)

        # Set API keys
        api_keys = config.get('api_keys', {})
        for key, value in api_keys.items():
            if value and value != f"your_{key}_here":
                os.environ[key.upper()] = str(value)

        # Set LangChain configuration
        langchain = config.get('langchain', {})
        if 'tracing_v2' in langchain:
            os.environ['LANGCHAIN_TRACING_V2'] = str(langchain['tracing_v2']).lower()

        # Set model configurations
        models = config.get('models', {})

        # Handle simple model config (like news agent) - just provider and name directly
        if 'provider' in models and 'name' in models:
            # This is a simple config, set as small_model (used by news agent)
            os.environ['SMALL_MODEL_PROVIDER'] = models['provider']
            os.environ['SMALL_MODEL_NAME'] = models['name']
        else:
            # Handle complex model config (like review writer) - with model types
            for model_type, model_config in models.items():
                if isinstance(model_config, dict) and 'provider' in model_config:
                    os.environ[f'{model_type.upper()}_PROVIDER'] = model_config['provider']
                if isinstance(model_config, dict) and 'name' in model_config:
                    os.environ[f'{model_type.upper()}_NAME'] = model_config['name']

        # Set embedding configuration
        embeddings = config.get('embeddings', {})
        if 'provider' in embeddings:
            os.environ['EMBEDDING_PROVIDER'] = embeddings['provider']
        if 'model_name' in embeddings:
            os.environ['EMBEDDING_MODEL_NAME'] = embeddings['model_name']

        # Set Langfuse configuration
        langfuse = config.get('langfuse', {})
        if 'enabled' in langfuse:
            os.environ['USE_LANGFUSE'] = str(langfuse['enabled']).lower()

        # Set cache configuration
        cache = config.get('cache', {})
        if 'path' in cache and cache['path']:
            os.environ['CACHE_PATH'] = cache['path']
        if 'ttl' in cache:
            os.environ['CACHE_TTL'] = str(cache['ttl'])

        # Set Arxiv configuration
        arxiv = config.get('arxiv', {})
        if 'storage_path' in arxiv and arxiv['storage_path']:
            os.environ['ARXIV_STORAGE_PATH'] = arxiv['storage_path']

        # Set additional environment variables from .env
        # Max tokens configurations
        if 'max_writing_tokens' in config:
            os.environ['MAX_WRITING_TOKENS'] = str(config['max_writing_tokens'])

        # Review writer specific max tokens
        review_writer = config.get('review_writer', {})
        if 'max_writing_tokens' in review_writer:
            os.environ['MAX_WRITING_TOKENS'] = str(review_writer['max_writing_tokens'])
        if 'max_rewrite_tokens' in review_writer:
            os.environ['MAX_REWRITE_TOKENS'] = str(review_writer['max_rewrite_tokens'])
        if 'max_refine_tokens' in review_writer:
            os.environ['MAX_REFINE_TOKENS'] = str(review_writer['max_refine_tokens'])

        # Search tools configurations
        search_tools = config.get('search_tools', {})
        if 'toc_search_tools' in search_tools:
            os.environ['TOC_SEARCH_TOOLS'] = search_tools['toc_search_tools']
        if 'section_writer_search_tools' in search_tools:
            os.environ['SECTION_WRITER_SEARCH_TOOLS'] = search_tools['section_writer_search_tools']
        if 'section_refine_search_tools' in search_tools:
            os.environ['SECTION_REFINE_SEARCH_TOOLS'] = search_tools['section_refine_search_tools']

        # Review writer specific settings
        review_writer = config.get('review_writer', {})
        if 'skip_latex_review' in review_writer:
            os.environ['SKIP_LATEX_REVIEW'] = str(review_writer['skip_latex_review']).lower()
        if 'tex_file' in review_writer:
            os.environ['TEX_FILE'] = review_writer['tex_file']
        if 'bib_file' in review_writer:
            os.environ['BIB_FILE'] = review_writer['bib_file']
        if 'pdf_file' in review_writer:
            os.environ['PDF_FILE'] = review_writer['pdf_file']

        # News agent specific settings
        news_agent = config.get('news_agent', {})
        if 'topics_file' in news_agent:
            os.environ['TOPICS_FILE'] = news_agent['topics_file']
        if 'output_dir' in news_agent:
            os.environ['OUTPUT_DIR'] = news_agent['output_dir']
        if 'news_dest_file' in news_agent and news_agent['news_dest_file']:
            os.environ['NEWS_DEST_FILE'] = news_agent['news_dest_file']


def load_agent_config(agent_name: str) -> ConfigLoader:
    """
    Load configuration for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., 'news', 'review_writer')

    Returns:
        ConfigLoader instance for the agent
    """
    # Look in agent-specific folder for base config
    config_dir = Path(__file__).parent.parent / "agents" / agent_name
    loader = ConfigLoader(str(config_dir))
    # Pass agent_name to the loader for local config lookup
    loader._agent_name = agent_name
    return loader

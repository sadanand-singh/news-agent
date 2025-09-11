# News Agent

A LangGraph-based system for collecting and curating news articles across multiple topics using AI-powered search and deduplication.

## Features

- **Automated News Collection**: Gathers latest news from multiple sources (Brave Search, Tavily)
- **Smart Deduplication**: Removes duplicate articles using semantic similarity
- **Topic-based Organization**: Collects news for predefined topics (Technology, AI, Health, Science, etc.)
- **Multiple LLM Support**: OpenAI, Anthropic, Google Gemini, and Ollama
- **YAML Output**: Saves collected news in structured YAML format

## Installation

```bash
# Clone repository
git clone <repository-url>
cd news-agent

# Install dependencies
uv sync
```

## Configuration

This project uses YAML configuration files for different configuration options.

### Quick Setup

1. **Copy the example configuration file:**

   ```bash
   cp configs/news.config.sample.yaml configs/news.config.yaml
   ```

2. **Edit the configuration file with your API keys:**

   ```bash
   # Edit configs/news.config.yaml
   # Replace placeholder values with your actual API keys
   ```

### Configuration Structure

The configuration file contains several sections:

#### API Keys

```yaml
api_keys:
  openai_api_key: "your-key-here"
  anthropic_api_key: "your-key-here"
  google_api_key: "your-key-here"
  brave_api_key: "your-key-here"
  tavily_api_key: "your-key-here"
  aws_access_key_id: ""
  aws_secret_access_key: ""
  langchain_api_key: "your-key-here"
  llamaindex_api_key: "your-key-here"
  langfuse_public_key: "your-key-here"
  langfuse_secret_key: "your-key-here"
```

#### Model Configuration

```yaml
models:
  provider: "openai"
  name: "gpt-5-mini-2025-08-07"
```

#### Embedding Configuration

```yaml
embeddings:
  provider: "ollama"
  model_name: "bge-large"
```

#### News Agent Settings

```yaml
news_agent:
  topics_file: "/Users/sadanand/Develop/news-agent/news_agent/agents/news/topics.yaml"
  output_dir: "/Users/sadanand/Develop/news-agent/news_agent/agents/news/output"
  news_dest_file: "/Users/sadanand/Develop/news-site/src/data/news.yaml"
  similarity_threshold: 0.95
  max_writing_tokens: 16000
```

#### Langfuse Configuration

```yaml
langfuse:
  enabled: false
```

#### LangChain Configuration

```yaml
langchain:
  tracing_v2: false
```

### Security Notes

- **Never commit your actual configuration file** - it contains your API keys
- The `config.sample.yaml` files are safe to commit as they contain only placeholder values
- Use different config files for different environments if needed

### Programmatic Configuration Access

```python
from news_agent.utils.config_loader import load_agent_config

# Load configuration for news agent
config = load_agent_config('news')

# Get a specific setting
output_dir = config.get('news_agent.output_dir')

# Set environment variables (for backward compatibility)
config.set_env_vars()
```

## Usage

### Run the News Agent

```bash
python main.py
```

This will:

- Read topics from the configured topics file
- Collect news items using the configured search tools
- Apply deduplication using the configured similarity threshold
- Save results to the configured output directory
- Copy output to the news site data file for deployment (controlled via `news_agent.news_dest_file`)

### Programmatic Usage

```python
from news_agent.agents.news.agent import graph

# Run the news collection graph
result = await graph.ainvoke({'messages': []})
```

## Output

The system generates YAML files containing:

- News collections organized by topic
- Article metadata (title, URL, content, date, source)
- Deduplication status
- Collection timestamps

## Project Structure

```text
news-site/                     # For deployment of news site
news_agent/
├── agents/
│   └── news/
│       ├── agent.py           # Main news collection workflow
│       ├── topics.yaml        # Topic definitions
│       ├── helpers/           # Utilities and state management
│       └── output/            # Generated news collections
├── utils/
│   ├── get_llm.py            # LLM provider utilities
│   └── get_search_tool.py    # Search tool integrations
```

## Supported Topics

The agent collects news for topics including:

- **Technology**: AI, Machine Learning, Robotics, Blockchain
- **Health**: Medical devices, Biotechnology, Wellness
- **Science**: Space programs, Climate change, Genomics
- **Business**: Stock markets, Cryptocurrency, Tech companies
- **World**: US, UK, EU, India, China, and other regions

## Troubleshooting

1. **Configuration not loading:** Make sure the `configs/news.config.yaml` file exists and has the correct format
2. **API key errors:** Verify your API keys are correctly set in the configuration file
3. **File not found errors:** Check that file paths in the configuration are correct and files exist
4. **No news collected:** Check your search API keys (Brave, Tavily) and internet connection
5. **Import errors:** Make sure all dependencies are installed with `uv sync`

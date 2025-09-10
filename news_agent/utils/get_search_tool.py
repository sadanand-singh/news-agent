import asyncio
import os
import random
import threading
import time
from typing import Any, Literal, Optional, Union

from duckduckgo_search import DDGS
from langchain_community.tools import (
    ArxivQueryRun,
    WikipediaQueryRun,
)
from langchain_community.utilities import (
    ArxivAPIWrapper,
    WikipediaAPIWrapper,
)
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_tavily import TavilySearch

from news_agent.utils.brave_search import BraveSearch

# Global rate limiter for DuckDuckGo search (configurable delay between requests)
_ddg_search_lock = threading.Lock()
_last_ddg_request_time = 0
_ddg_base_delay = 15.0
_ddg_max_retries = 5


def get_client_settings():
    """Get client settings with current environment variables."""
    return {
        'arxiv': {
            'command': 'uv',
            'args': [
                'tool',
                'run',
                'arxiv-mcp-server',
                '--storage-path',
                os.getenv('ARXIV_STORAGE_PATH'),
            ],
            'transport': 'stdio',
        },
        'brave': {
            'command': 'npx',
            'args': [
                '-y',
                '@modelcontextprotocol/server-brave-search',
            ],
            'env': {'BRAVE_API_KEY': os.getenv('BRAVE_API_KEY')},
            'transport': 'stdio',
        },
        'tavily': {
            'command': 'npx',
            'args': ['-y', 'tavily-mcp@latest'],
            'env': {'TAVILY_API_KEY': os.getenv('TAVILY_API_KEY')},
            'transport': 'stdio',
        },
        'ddg': {
            'command': 'uv',
            'args': ['tool', 'run', 'duckduckgo-mcp-server'],
            'transport': 'stdio',
        },
        'wikipedia': {
            'command': 'uv',
            'args': ['tool', 'run', 'mediawiki-mcp-server'],
            'transport': 'stdio',
        },
        'deepwiki': {
            'command': 'npx',
            'args': ['-y', 'deepwiki-mcp@latest'],
            'transport': 'stdio',
        },
    }


def ddg_tool(
    keywords: str,
) -> list[dict[str, str]]:
    """DuckDuckGo text search generator with robust rate limiting and retry logic.

    Args:
        keywords: keywords for query.

    Returns:
        List of dictionaries with search results.
    """
    global _last_ddg_request_time

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0',
    ]

    for attempt in range(_ddg_max_retries):
        with _ddg_search_lock:
            current_time = time.time()
            # Calculate delay (increase after failed attempts)
            current_delay = _ddg_base_delay * (1.5**attempt)  # Progressive delay
            time_since_last = current_time - _last_ddg_request_time

            if time_since_last < current_delay:
                sleep_time = current_delay - time_since_last
                print(
                    f'DuckDuckGo rate limiting: waiting {sleep_time:.1f} seconds (attempt {attempt + 1}/{_ddg_max_retries})...'
                )
                time.sleep(sleep_time)

            try:
                print(
                    f"DuckDuckGo search: attempting query '{keywords}' (attempt {attempt + 1}/{_ddg_max_retries})"
                )
                res = DDGS(headers={'User-Agent': random.choice(USER_AGENTS)}).text(
                    keywords, max_results=5
                )
                _last_ddg_request_time = time.time()

                # Check if we got a rate limit response in the results
                if isinstance(res, list) and len(res) > 0:
                    # Sometimes rate limit info comes in the response
                    first_result = res[0] if res else {}
                    if any(
                        term in str(first_result).lower()
                        for term in ['ratelimit', 'rate limit', '202']
                    ):
                        raise Exception('DuckDuckGo rate limit detected in response')

                print(f'DuckDuckGo search successful: found {len(res)} results')
                return res

            except Exception as e:
                _last_ddg_request_time = time.time()
                error_msg = str(e).lower()

                # Check for rate limit related errors
                if any(
                    term in error_msg
                    for term in ['ratelimit', 'rate limit', '202', 'too many requests']
                ):
                    if attempt < _ddg_max_retries - 1:
                        # Exponential backoff for rate limit errors
                        backoff_time = (2**attempt) * 5  # 5, 10, 20 seconds
                        print(
                            f'DuckDuckGo rate limit error detected. Backing off for {backoff_time} seconds...'
                        )
                        time.sleep(backoff_time)
                        continue
                    else:
                        print(f'DuckDuckGo: Max retries exceeded due to rate limiting. Error: {e}')
                        # Return empty results instead of crashing
                        return []
                else:
                    # Non-rate-limit error, re-raise immediately
                    print(f'DuckDuckGo search error (non-rate-limit): {e}')
                    raise e

    # If we get here, all retries failed due to rate limiting
    print('DuckDuckGo: All retry attempts failed due to rate limiting. Returning empty results.')
    return []


def get_tavily_tool(
    max_results: int = 5,
    topic: Literal['general', 'news'] = 'general',
    include_domains: list[str] = [],
    exclude_domains: list[str] = [],
    days: int = 7,
    time_range: Optional[Literal['day', 'week', 'month', 'year', 'd', 'w', 'm', 'y']] = None,
    auto_parameters: bool = False,
    search_depth: Literal['basic', 'advanced'] = 'basic',
    chunks_per_source: int = 3,
    include_images: bool = False,
    include_image_descriptions: bool = False,
    include_answer: Union[bool, Literal['basic', 'advanced']] = False,
    country: Optional[str] = None,
    timeout: int = 60,
    include_favicon: bool = False,
) -> TavilySearch:
    return TavilySearch(
        max_results=max_results,
        topic=topic,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        days=days,
        time_range=time_range,
        auto_parameters=auto_parameters,
        search_depth=search_depth,
        chunks_per_source=chunks_per_source,
        include_images=include_images,
        include_image_descriptions=include_image_descriptions,
        include_answer=include_answer,
        country=country,
        timeout=timeout,
        include_favicon=include_favicon,
    )


def get_brave_tool(
    count: int = 5,
    freshness: Optional[Literal['pd', 'pw', 'pm', 'py']] = None,
    result_filter: Optional[str] = None,
) -> BraveSearch:
    return BraveSearch.from_api_key(
        api_key=os.getenv('BRAVE_API_KEY'),
        search_kwargs={'count': count, 'freshness': freshness, 'result_filter': result_filter},
    )


def get_arxiv_tool(
    top_k_results: int = 3, doc_content_chars_max: int = 4000, load_max_docs: int = 5
):
    return ArxivQueryRun(
        api_wrapper=ArxivAPIWrapper(
            top_k_results=top_k_results,
            doc_content_chars_max=doc_content_chars_max,
            load_max_docs=load_max_docs,
            continue_on_failure=True,
        )
    )


def get_wiki_tool(top_k_results: int = 3, doc_content_chars_max: int = 4000, lang: str = 'en'):
    api_wrapper = WikipediaAPIWrapper(
        top_k_results=top_k_results, doc_content_chars_max=doc_content_chars_max, lang=lang
    )
    return WikipediaQueryRun(api_wrapper=api_wrapper)


def get_mcp_tools(sources: list[str]) -> Any:
    client_settings = get_client_settings()
    client_with_sources = MultiServerMCPClient(
        {source: client_settings[source] for source in sources if source in client_settings}
    )
    tools = asyncio.run(client_with_sources.get_tools())
    return tools


def get_tools(tool_names: str, **input_kwargs: Any) -> list[Any]:
    tool_names = tool_names.split(',')
    tools_kwargs = build_tool_kwargs(tool_names, **input_kwargs)
    tools = []
    for tool_name, kwargs in tools_kwargs.items():
        if tool_name == 'tavily':
            tools.append(get_tavily_tool(**kwargs))
        elif tool_name == 'brave':
            tools.append(get_brave_tool(**kwargs))
        elif tool_name == 'ddg':
            tools.append(ddg_tool)
        elif tool_name == 'arxiv':
            tools.append(get_arxiv_tool(**kwargs))
        elif tool_name == 'wiki':
            tools.append(get_wiki_tool(**kwargs))
        else:
            raise ValueError(f'Invalid tool name: {tool_name}')
    return tools


def build_tool_kwargs(tool_names: list[str], **input_kwargs: Any) -> dict[str, Any]:
    kwargs = {}
    for tool in tool_names:
        if tool == 'tavily':
            kwargs['tavily'] = {
                'max_results': 5,
                'topic': 'general',
                'days': 7,
                'auto_parameters': False,
                'search_depth': 'basic',
                'chunks_per_source': 3,
                'include_images': False,
                'include_image_descriptions': False,
                'include_answer': False,
                'timeout': 60,
                'include_favicon': False,
            }
            # Override/add tavily_ prefixed kwargs
            for key, value in input_kwargs.items():
                if key.startswith('tavily_'):
                    clean_key = key.replace('tavily_', '')
                    # Verify key is allowed for TavilySearch
                    if clean_key in [
                        'max_results',
                        'topic',
                        'days',
                        'include_domains',
                        'exclude_domains',
                        'time_range',
                        'auto_parameters',
                        'search_depth',
                        'chunks_per_source',
                        'include_images',
                        'include_image_descriptions',
                        'include_answer',
                        'country',
                        'timeout',
                        'include_favicon',
                    ]:
                        kwargs['tavily'][clean_key] = value
        elif tool == 'brave':
            kwargs['brave'] = {'count': 5}
            # Override/add brave_ prefixed kwargs
            for key, value in input_kwargs.items():
                if key.startswith('brave_'):
                    clean_key = key.replace('brave_', '')
                    # Verify key is allowed for BraveSearch
                    if clean_key in ['count', 'freshness', 'result_filter']:
                        kwargs['brave'][clean_key] = value
        elif tool == 'ddg':
            kwargs['ddg'] = {}
        elif tool == 'arxiv':
            kwargs['arxiv'] = {
                'top_k_results': 3,
                'doc_content_chars_max': 4000,
                'load_max_docs': 5,
            }
            # Override/add arxiv_ prefixed kwargs
            for key, value in input_kwargs.items():
                if key.startswith('arxiv_'):
                    clean_key = key.replace('arxiv_', '')
                    # Verify key is allowed for ArxivQueryRun
                    if clean_key in ['top_k_results', 'doc_content_chars_max', 'load_max_docs']:
                        kwargs['arxiv'][clean_key] = value
        elif tool == 'wiki':
            kwargs['wiki'] = {
                'top_k_results': 3,
                'doc_content_chars_max': 4000,
                'lang': 'en',
            }
            # Override/add wiki_ prefixed kwargs
            for key, value in input_kwargs.items():
                if key.startswith('wiki_'):
                    clean_key = key.replace('wiki_', '')
                    # Verify key is allowed for WikipediaQueryRun
                    if clean_key in ['top_k_results', 'doc_content_chars_max', 'lang']:
                        kwargs['wiki'][clean_key] = value
    return kwargs

from __future__ import annotations

import threading
import time
from typing import Any, Optional

from langchain_community.utilities.brave_search import BraveSearchWrapper
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import Field, SecretStr

# Global rate limiter for Brave Search API (1 request per second for free tier)
_brave_search_lock = threading.Lock()
_last_request_time = 0


class BraveSearch(BaseTool):
    """Tool that queries the BraveSearch.

    Api key can be provided as an environment variable BRAVE_SEARCH_API_KEY
    or as a parameter.


    Example usages:
    .. code-block:: python
        # uses BRAVE_SEARCH_API_KEY from environment
        tool = BraveSearch()

    .. code-block:: python
        # uses the provided api key
        tool = BraveSearch.from_api_key("your-api-key")

    .. code-block:: python
        # uses the provided api key and search kwargs
        tool = BraveSearch.from_api_key(
                                api_key = "your-api-key",
                                search_kwargs={"max_results": 5}
                                )

    .. code-block:: python
        # uses BRAVE_SEARCH_API_KEY from environment
        tool = BraveSearch.from_search_kwargs({"max_results": 5})
    """

    name: str = 'brave_search'
    description: str = (
        'a search engine. '
        'useful for when you need to answer questions about current events.'
        ' input should be a search query.'
    )
    search_wrapper: BraveSearchWrapper = Field(default_factory=BraveSearchWrapper)
    max_retries: int = Field(
        default=3, description='Maximum number of retries for rate-limited requests'
    )

    @classmethod
    def from_api_key(
        cls, api_key: str, search_kwargs: Optional[dict] = None, **kwargs: Any
    ) -> BraveSearch:
        """Create a tool from an api key.

        Args:
            api_key: The api key to use.
            search_kwargs: Any additional kwargs to pass to the search wrapper.
            **kwargs: Any additional kwargs to pass to the tool.

        Returns:
            A tool.
        """
        wrapper = BraveSearchWrapper(api_key=SecretStr(api_key), search_kwargs=search_kwargs or {})
        return cls(search_wrapper=wrapper, **kwargs)

    @classmethod
    def from_search_kwargs(cls, search_kwargs: dict, **kwargs: Any) -> BraveSearch:
        """Create a tool from search kwargs.

        Uses the environment variable BRAVE_SEARCH_API_KEY for api key.

        Args:
            search_kwargs: Any additional kwargs to pass to the search wrapper.
            **kwargs: Any additional kwargs to pass to the tool.

        Returns:
            A tool.
        """
        # we can not provide api key because it's calculated in the wrapper,
        # so the ignore is needed for linter
        # not ideal but needed to keep the tool code changes non-breaking
        wrapper = BraveSearchWrapper(search_kwargs=search_kwargs)
        return cls(search_wrapper=wrapper, **kwargs)

    def _rate_limited_request(self, query: str) -> str:
        """Make a rate-limited request to Brave Search API."""
        global _last_request_time

        with _brave_search_lock:
            current_time = time.time()
            # Ensure at least 1.5 second between requests (free tier limit)
            time_since_last = current_time - _last_request_time
            if time_since_last < 1.5:
                sleep_time = 1.5 - time_since_last
                time.sleep(sleep_time)

            try:
                result = self.search_wrapper.run(query)
                _last_request_time = time.time()
                return result
            except Exception as e:
                _last_request_time = time.time()
                raise e

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool with rate limiting and retry logic."""
        import requests

        for attempt in range(self.max_retries):
            try:
                return self._rate_limited_request(query)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = 2**attempt
                    print(
                        f'Rate limited. Waiting {wait_time} seconds before retry {attempt + 1}/{self.max_retries}'
                    )
                    time.sleep(wait_time)
                    if attempt == self.max_retries - 1:
                        raise Exception(
                            f'Max retries exceeded for query: {query}. Brave Search API rate limit exceeded.'
                        )
                else:
                    # Other HTTP error, re-raise immediately
                    raise e
            except Exception as e:
                # Other errors, re-raise immediately
                raise e

        # This should never be reached, but just in case
        raise Exception(f'Unexpected error in BraveSearch for query: {query}')

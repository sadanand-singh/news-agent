from typing import Annotated, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, RootModel


class NewsItem(BaseModel):
    """Structure for individual news item."""

    title: str = Field(description='News title (max 15 words)')
    summary: str = Field(description='News summary (max 1-2 paragraphs)')
    sources: List[str] = Field(
        description='List of URLs which point to this news', default_factory=list
    )
    published_date: Optional[str] = Field(
        description='Publication date if available', default=None
    )
    topic: str = Field(description='The topic this news item belongs to')
    groups: List[str] = Field(
        description='The groups this news item is categorized under', default_factory=list
    )


class SavedNewsItem(BaseModel):
    """Simplified news item for saving to file."""

    title: str
    summary: str
    sources: List[str]
    published_date: Optional[str] = None


class SavedTopicData(BaseModel):
    """Topic data structure for saving to file."""

    groups: List[str]
    news: List[SavedNewsItem]


class SaveNewsCollection(RootModel[Dict[str, SavedTopicData]]):
    """Final news collection for saving - mirrors topics.yaml structure."""

    pass


class NewsCollectionOutput(BaseModel):
    """Output schema for the news collection reactive agent."""

    news_items: List[NewsItem] = Field(description='Collected and processed news items')


class MainNewsAgentState(BaseModel):
    """State for the main news agent orchestrator."""

    topics_file: str = Field(
        default='news_agent/agents/news/topics.yaml', description='Path to topics YAML file'
    )
    topics_data: dict = Field(default_factory=dict, description='Loaded topics data from YAML')
    current_topic_index: int = Field(default=0, description='Current topic index being processed')
    topic_list: List[tuple] = Field(
        default_factory=list, description='List of (topic_name, topic_info) tuples'
    )
    news_collections: List[NewsItem] = Field(
        default_factory=list, description='News collections for each topic'
    )
    current_news_items: List[NewsItem] = Field(
        default_factory=list, description='Current topic news items from reactive agent'
    )
    current_topic: str = Field(default='', description='Current topic being processed')
    current_groups: List[str] = Field(default_factory=list, description='Current topic groups')
    days_filter: int = Field(default=2, description='Days filter for current topic')
    current_step: str = Field(default='', description='Current processing step')
    max_items_per_topic: int = Field(default=20, description='Maximum news items per topic')
    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(default_factory=list)
    tool_call_count: int = Field(default=0, description='Tool call counter for rate limiting')

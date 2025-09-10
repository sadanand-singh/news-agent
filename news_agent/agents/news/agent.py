import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Literal

import yaml
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from news_agent.agents.news.helpers.state import (
    MainNewsAgentState,
    NewsCollectionOutput,
    SavedNewsItem,
    SavedTopicData,
    SaveNewsCollection,
)
from news_agent.agents.news.helpers.deduplication import deduplicate_news_items
from news_agent.agents.news.helpers.reactive_agent import create_reactive_graph
from news_agent.utils.get_search_tool import get_brave_tool, get_tavily_tool
from news_agent.utils.config_loader import load_agent_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config = load_agent_config('news')
config.set_env_vars()

if os.getenv('USE_LANGFUSE', 'false').lower() == 'true':
    langfuse_handler = CallbackHandler()
else:
    langfuse_handler = None


def get_days_filter_for_groups(groups: List[str]) -> int:
    """Determine the number of days to filter news based on group categories."""
    if any(group.lower() in ['politics'] for group in groups):
        return 2
    elif any(group.lower() in ['technology'] for group in groups):
        return 4
    elif any(group.lower() in ['science'] for group in groups):
        return 7
    elif any(group.lower() in ['health'] for group in groups):
        return 7
    else:
        return 2


def load_topics_data(state: MainNewsAgentState) -> MainNewsAgentState:
    """Load topics data from YAML file."""
    topics_file = config.get('news_agent.topics_file')
    if not topics_file:
        raise ValueError('topics_file not configured in news_agent section')

    try:
        with open(topics_file, 'r') as file:
            topics_data = yaml.safe_load(file)

        # Convert to list of tuples for processing
        topic_list = list(topics_data.items())

        logger.info(f'Loaded {len(topics_data)} topics from {topics_file}')
        return {
            'topics_file': topics_file,
            'topics_data': topics_data,
            'topic_list': topic_list,
            'current_step': 'topics_loaded',
        }
    except Exception as e:
        logger.error(f'Failed to load topics file: {e}')
        return {'current_step': 'error'}


def route_to_next_topic(
    state: MainNewsAgentState,
) -> Command[Literal['process_topic', 'deduplicate_collections']]:
    """Accumulate current news items and decide whether to process next topic or finish."""
    # First, accumulate any current news items from the last topic processing
    updates = {}
    if state.current_news_items:
        updates['news_collections'] = state.news_collections + state.current_news_items
        updates['current_news_items'] = []

    if state.current_topic_index < len(state.topic_list):
        topic_name, topic_info = state.topic_list[state.current_topic_index]
        groups = topic_info.get('groups', [])
        days_filter = get_days_filter_for_groups(groups)

        if any(group.lower() in ['us', 'india', 'world'] for group in groups):
            groups += ['breaking news', 'politics']
        groups += ['recent events', 'recent developments', 'latest news']

        logger.info(
            f'Processing topic {state.current_topic_index + 1}/{len(state.topic_list)}: {topic_name}'
        )

        updates.update(
            {
                'current_step': f'processing_topic_{state.current_topic_index}',
                'current_topic': topic_name,
                'current_groups': groups,
                'days_filter': days_filter,
                'current_topic_index': state.current_topic_index + 1,
            }
        )

        return Command(goto='process_topic', update=updates)
    else:
        logger.info('All topics processed, saving collections')
        updates.update({'current_step': 'all_topics_processed'})
        return Command(goto='deduplicate_collections', update=updates)


def deduplicate_collections(state: MainNewsAgentState) -> MainNewsAgentState:
    """Deduplicate the collected news items."""
    collections = state.news_collections

    if not collections:
        return {'current_step': 'no_collections_to_deduplicate'}

    logger.info(f'Deduplicating {len(collections)} news items')
    try:
        similarity_threshold = config.get('news_agent.similarity_threshold', 0.95)
        deduplicated_collections = deduplicate_news_items(collections, similarity_threshold=similarity_threshold)
        # Safety check: if deduplication returns empty when we had items, use original
        if not deduplicated_collections and collections:
            logger.warning("Deduplication returned empty list, using original collections")
            deduplicated_collections = collections
        logger.info(f'After deduplication: {len(deduplicated_collections)} news items remain')
    except Exception as e:
        logger.error(f"Deduplication failed: {e}", exc_info=True)
        logger.warning("Using original collections without deduplication")
        deduplicated_collections = collections

    return {
        'news_collections': deduplicated_collections,
        'current_step': 'collections_deduplicated'
    }


def save_collections(state: MainNewsAgentState) -> MainNewsAgentState:
    """Save the deduplicated news collections to files."""
    deduplicated_collections = state.news_collections

    if not deduplicated_collections:
        return {'current_step': 'no_collections_to_save'}

    # Save as JSON
    output_dir = config.get('news_agent.output_dir')
    if not output_dir:
        raise ValueError('output_dir not configured in news_agent section')

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Group deduplicated news items by topic
    topics_data = {}
    for news_item in deduplicated_collections:
        topic = news_item.topic
        if topic not in topics_data:
            topics_data[topic] = SavedTopicData(groups=news_item.groups, news=[])

        saved_item = SavedNewsItem(
            title=news_item.title,
            summary=news_item.summary,
            sources=news_item.sources,
            published_date=news_item.published_date,
        )
        topics_data[topic].news.append(saved_item)

    # Create the final collection
    save_collection = SaveNewsCollection(topics_data)

    # Save as YAML
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    yaml_file = output_dir / f'news_collections_{timestamp}.yaml'
    with open(yaml_file, 'w') as f:
        yaml.dump(save_collection.model_dump(), f, default_flow_style=False, allow_unicode=True)

    logger.info(f'Saved {len(deduplicated_collections)} news collections to {output_dir}')

    dest_file = config.get('news_agent.news_dest_file')
    if dest_file:
        with open(dest_file, 'w') as f:
            yaml.dump(
                save_collection.model_dump(), f, default_flow_style=False, allow_unicode=True
            )
        logger.info(f'Saved {len(deduplicated_collections)} news collections to {dest_file}')

    return {'current_step': 'collections_saved'}


def create_news_worker_agent():
    """Create the reactive agent that collects news for a single topic."""

    # Create search tools optimized for recent news
    search_config = config.get('search_tools', {})
    brave_config = search_config.get('brave', {})
    tavily_config = search_config.get('tavily', {})

    brave_tool = get_brave_tool(
        count=brave_config.get('count', 8),
        freshness=brave_config.get('freshness', 'pw')
    )
    tavily_tool = get_tavily_tool(
        max_results=tavily_config.get('max_results', 8),
        topic=tavily_config.get('topic', 'news'),
        days=tavily_config.get('days', 2),
        search_depth=tavily_config.get('search_depth', 'basic'),
    )
    tools = [brave_tool, tavily_tool]

    system_prompt = """You are a news collection agent. Your task is to collect the latest news articles for the topic "{current_topic}" in the groups {current_groups}.

    You must collect {max_items_per_topic} unique news items for each topic. Sort them by relevance and recency.

    IMPORTANT: You do need any confirmation for anything.

IMPORTANT: Only include news from the last {days_filter} days. Filter out any articles older than {days_filter} days from today's date. Use multiple search queries combining the topic with each group.

If {current_topic} contains a comma separated list of topics, use each topic individually and in combination with the groups to create a list of search queries. you can also combine multiple topics together to optimize the search queries.

Search queries to use:
1. topic (after splitting by comma) + each group individually
2. topic (after splitting by comma) + combinations of groups
3. topic (after splitting by comma) + combinations of groups + combinations of topics

After collecting search results, analyze and extract the most relevant and recent news items. For each news item, provide:
** Output schema **
- title: A concise title (max 15 words)
- summary: A comprehensive summary (At least 1-2 paragraphs, 150-250 words.)
- sources: List of Source URLs - retrieve the URL from the search results - each URL should be a valid URL
- topic: {current_topic}
- groups: {current_groups}
- published_date: The date the news item was published

Focus on unique, high-quality news items and avoid duplicates. Prioritize recent and authoritative sources."""

    user_prompt = """Please collect the latest news for the topic "{current_topic}" related to {current_groups}.

Search thoroughly using multiple queries and tools. Then provide a comprehensive list of unique news items with proper summaries and source attribution."""

    return create_reactive_graph(
        prompt=user_prompt,
        system_prompt=system_prompt,
        assistant_schema=MainNewsAgentState,
        output_schema=MainNewsAgentState,
        output_key='current_news_items',
        tools=tools,
        structured_output_schema=NewsCollectionOutput,
        passthrough_keys=['current_topic', 'current_groups', 'days_filter', 'max_items_per_topic'],
        aggregate_output=False,
        model_type='small',
        max_tool_calls=10,
        extracted_output_key='news_items',
        max_tokens=config.get('news_agent.max_writing_tokens', 16000),
        extractor_prompt="""Extract news items from the following input text: {content}""",
    )


def create_main_news_agent():
    """Create the main news agent orchestrator."""

    builder = StateGraph(MainNewsAgentState)

    builder.add_node('load_topics', load_topics_data)
    builder.add_node('route_to_next_topic', route_to_next_topic)
    builder.add_node('process_topic', create_news_worker_agent().compile())
    builder.add_node('deduplicate_collections', deduplicate_collections)
    builder.add_node('save_collections', save_collections)

    builder.set_entry_point('load_topics')
    builder.add_edge('load_topics', 'route_to_next_topic')
    builder.add_edge('process_topic', 'route_to_next_topic')
    builder.add_edge('deduplicate_collections', 'save_collections')
    builder.add_edge('save_collections', END)

    return builder


# cacher = SqliteCache(path=os.getenv('CACHE_PATH')) if os.getenv('CACHE_PATH') else None

graph = (
    create_main_news_agent()
    .compile()
    .with_config(
        config={
            'callbacks': [langfuse_handler] if langfuse_handler is not None else [],
            'checkpointer': MemorySaver(),
            'recursion_limit': 500,
        }
    )
)


# Manually invoke the graph
async def run_graph():
    initial_state = {'messages': []}
    result = await graph.ainvoke(initial_state)
    print(result)


# Run the asynchronous function
if __name__ == '__main__':
    asyncio.run(run_graph())

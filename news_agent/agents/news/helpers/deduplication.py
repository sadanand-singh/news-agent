"""News deduplication utilities using embeddings and similarity comparison."""

import logging
from typing import List, Tuple

from news_agent.agents.news.helpers.state import NewsItem
from news_agent.utils.get_embeddings import calculate_similarity, get_embeddings
from news_agent.utils.get_llm import get_llm

logger = logging.getLogger(__name__)


def merge_news_items(item1: NewsItem, item2: NewsItem) -> NewsItem:
    """
    Merge two similar news items using the SMALL model for intelligent merging.

    Args:
        item1: First news item
        item2: Second news item

    Returns:
        NewsItem: Merged news item
    """
    # Get the small model for merging
    llm = get_llm(model_type='small')

    # Create merge prompt
    merge_prompt = f"""You are tasked with merging two similar news items into one comprehensive item.

**News Item 1:**
Title: {item1.title}
Summary: {item1.summary}
Sources: {', '.join(item1.sources)}
Published Date: {item1.published_date or 'Unknown'}

**News Item 2:**
Title: {item2.title}
Summary: {item2.summary}
Sources: {', '.join(item2.sources)}
Published Date: {item2.published_date or 'Unknown'}

Please merge these into a single news item that:
1. Creates a new title that best captures both articles (max 15 words)
2. Combines information from both summaries into a comprehensive summary (150-250 words)
3. Combines all unique sources from both items
4. Uses the more recent published date if available

Return your response in this exact format:
TITLE: [merged title]
SUMMARY: [merged summary]
SOURCES: [comma-separated list of all unique URLs]
PUBLISHED_DATE: [more recent date or 'Unknown' if both are unknown]"""

    try:
        response = llm.invoke(merge_prompt)
        content = response.content.strip()

        # Parse the response
        lines = content.split('\n')
        merged_title = ""
        merged_summary = ""
        merged_sources = []
        merged_date = None

        current_section = ""
        for line in lines:
            line = line.strip()
            if line.startswith('TITLE:'):
                merged_title = line.replace('TITLE:', '').strip()
                current_section = "title"
            elif line.startswith('SUMMARY:'):
                merged_summary = line.replace('SUMMARY:', '').strip()
                current_section = "summary"
            elif line.startswith('SOURCES:'):
                sources_text = line.replace('SOURCES:', '').strip()
                merged_sources = [s.strip() for s in sources_text.split(',') if s.strip()]
                current_section = "sources"
            elif line.startswith('PUBLISHED_DATE:'):
                merged_date = line.replace('PUBLISHED_DATE:', '').strip()
                if merged_date.lower() == 'unknown':
                    merged_date = None
                current_section = "date"
            elif line and current_section == "summary":
                # Continue building summary if it spans multiple lines
                merged_summary += " " + line

        # Combine sources from both items and remove duplicates
        all_sources = list(set(item1.sources + item2.sources))
        if merged_sources:
            # Use merged sources from LLM, but ensure we don't lose any original sources
            all_sources = list(set(all_sources + merged_sources))

        # Use the first item's topic and groups (they should be the same for duplicates)
        return NewsItem(
            title=merged_title or f"{item1.title} / {item2.title}"[:100],  # Fallback
            summary=merged_summary or f"{item1.summary}\n\n{item2.summary}",  # Fallback
            sources=all_sources,
            published_date=merged_date or item1.published_date or item2.published_date,
            topic=item1.topic,
            groups=item1.groups
        )

    except Exception as e:
        logger.warning(f"Error merging news items with LLM: {e}. Using simple merge.")
        # Fallback: simple merge
        return NewsItem(
            title=f"{item1.title} / {item2.title}"[:100],
            summary=f"{item1.summary}\n\n{item2.summary}",
            sources=list(set(item1.sources + item2.sources)),
            published_date=item1.published_date or item2.published_date,
            topic=item1.topic,
            groups=item1.groups
        )


def deduplicate_news_items(news_items: List[NewsItem], similarity_threshold: float = 0.95) -> List[NewsItem]:
    """
    Deduplicate news items using embedding-based similarity comparison.

    Args:
        news_items: List of news items to deduplicate
        similarity_threshold: Similarity threshold for considering items duplicates (default: 0.8)

    Returns:
        List[NewsItem]: Deduplicated list of news items
    """
    if not news_items or len(news_items) <= 1:
        return news_items

    logger.info(f"Starting deduplication of {len(news_items)} news items")

    try:
        # Get embedding model
        logger.info("Initializing embeddings model (ollama/bge-large)")
        embeddings_model = get_embeddings(provider='ollama', model_name='bge-large')
        logger.info("Embeddings model initialized successfully")

        # Calculate embeddings for all news items
        texts_to_embed = []
        for item in news_items:
            # Combine title and summary for embedding
            combined_text = f"{item.title}\n{item.summary}"
            texts_to_embed.append(combined_text)

        logger.info(f"Calculating embeddings for {len(texts_to_embed)} items...")
        embeddings = embeddings_model.embed_documents(texts_to_embed)
        logger.info(f"Successfully calculated {len(embeddings)} embeddings")

        # Track which items have been merged
        merged_indices = set()
        deduplicated_items = []

        # Compare each pair of news items
        for i in range(len(news_items)):
            if i in merged_indices:
                continue

            current_item = news_items[i]
            items_to_merge = [current_item]
            indices_to_merge = [i]

            # Find all similar items
            for j in range(i + 1, len(news_items)):
                if j in merged_indices:
                    continue

                similarity = calculate_similarity(embeddings[i], embeddings[j])
                logger.debug(f"Similarity between item {i} and {j}: {similarity:.3f}")

                if similarity >= similarity_threshold:
                    logger.info(f"Found duplicate: items {i} and {j} (similarity: {similarity:.3f})")
                    items_to_merge.append(news_items[j])
                    indices_to_merge.append(j)
                    merged_indices.add(j)

            # Merge all similar items
            if len(items_to_merge) > 1:
                logger.info(f"Merging {len(items_to_merge)} similar items")
                merged_item = items_to_merge[0]
                for item_to_merge in items_to_merge[1:]:
                    merged_item = merge_news_items(merged_item, item_to_merge)
                deduplicated_items.append(merged_item)
            else:
                # No duplicates found, keep original item
                deduplicated_items.append(current_item)

        logger.info(f"Deduplication completed: {len(news_items)} -> {len(deduplicated_items)} items")
        return deduplicated_items

    except Exception as e:
        logger.error(f"Error during deduplication: {e}", exc_info=True)
        logger.warning("Returning original items without deduplication")
        return news_items
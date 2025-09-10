"""Main entry point for the news collection agent.

This script demonstrates how to use the news collection agent
to gather latest news based on topics defined in topics.yaml.
"""

import asyncio
import logging

from news_agent.agents.news.agent import graph

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Example of how to use the news collection agent."""

    print('🚀 Starting News Collection Agent...')
    print('📁 Reading topics from: news_agent/agents/news/topics.yaml')
    print('🔍 Will collect up to 30 news items per topic')
    print('⏰ Using date filters based on topic groups:')
    print('   • Politics: last 2 days')
    print('   • Technology: last 4 days')
    print('   • Science: last 7 days')
    print('   • Health: last 7 days')
    print('   • Others: last 2 days')
    print('-' * 50)

    # Example input - empty messages list to start the workflow
    input_data = {'messages': []}

    try:
        # Use async invocation
        result = await graph.ainvoke(input_data)
        print('✅ News collection completed successfully!')
        print(f'📊 Final result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}')

        # Print summary if we have news collections
        if 'news_collections' in result:
            total_items = sum(len(collection.news_items) for collection in result['news_collections'])
            print(f'📈 Total news items collected: {total_items}')
            print('💾 Results saved to: news_agent/agents/news/output/')

            # Print per-topic summary
            print('\n📋 Topic Summary:')
            for collection in result['news_collections']:
                print(f'   • {collection.topic}: {len(collection.news_items)} items')

    except Exception as e:
        print(f'❌ Error during execution: {e}')
        logging.exception('Failed to run news agent')


async def stream_example():
    """Example of streaming the news collection process."""

    print('--- Streaming news collection process ---')
    input_data = {'messages': []}

    try:
        async for chunk in graph.astream(input_data):
            print(f'Step: {chunk}')
    except Exception as e:
        print(f'Error during streaming: {e}')


if __name__ == '__main__':
    # Run the main news collection
    asyncio.run(main())

    # Or run with streaming
    # asyncio.run(stream_example())

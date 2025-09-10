from typing import Any, Literal, Optional, Union

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel
from trustcall import create_extractor

from news_agent.utils.get_llm import get_llm


def tools_condition(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = 'messages',
    max_tool_calls: int = 3,
) -> Literal['tools', 'output_node']:
    if isinstance(state, list):
        ai_message = state[-1]
        messages = state
    elif isinstance(state, dict) and (messages := state.get(messages_key, [])):
        ai_message = messages[-1]
    elif messages := getattr(state, messages_key, []):
        ai_message = messages[-1]
    else:
        raise ValueError(f'No messages found in input state to tool_edge: {state}')
    if hasattr(ai_message, 'tool_calls') and len(ai_message.tool_calls) > 0:
        return 'tools'
    return 'output_node'


def create_reactive_graph(
    prompt: str,
    system_prompt: str,
    assistant_schema: BaseModel,
    output_schema: BaseModel,
    output_key: str,
    tools: list[Any],
    extractor_prompt: str = """
        Extract latex and bibliography components from the following input text:
        {content}

        The two components are separated by a `---BIBLIOGRAPHY---` line.
        """,
    structured_output_schema: Optional[BaseModel] = None,
    passthrough_keys: list[str] = [],
    aggregate_output: bool = False,
    model_type: Literal['small', 'main'] = 'main',
    max_tool_calls: int = 3,
    extracted_output_key: Optional[str] = None,
    max_tokens: Optional[int] = None,
):
    llm = get_llm(model_type=model_type, max_tokens=max_tokens)
    llm_with_tools = llm.bind_tools(tools)

    async def assistant(state: assistant_schema) -> assistant_schema:
        tool_call_count = getattr(state, 'tool_call_count', 0)

        # If we've reached max tool calls, use LLM without tools to force final response
        if tool_call_count >= max_tool_calls:
            # Add instruction to provide final response based on gathered information
            messages = state.messages + [
                HumanMessage(
                    content="You have gathered enough information. Please provide your final response based on all the information you've collected so far. Do not attempt to use any tools."
                )
            ]
            return {'messages': [await llm.ainvoke(messages)]}
        else:
            return {'messages': [await llm_with_tools.ainvoke(state.messages)]}

    def build_prompt(state: assistant_schema) -> assistant_schema:
        # Build a dict of values to format the system prompt with

        def resolve_path(obj, path: str):
            """
            Recursively resolve a complex path with attribute access (@) and array indexing (#).

            Examples:
            - 'plan@zzz@dddf' -> obj.plan.zzz.dddf
            - 'plan#0' -> obj.plan[0]
            - 'plan#$index' -> obj.plan[obj.index]
            - 'plan@zzz#-1@latex' -> obj.plan.zzz[-1].latex
            - 'plan@zzz@dddf@aa@bb@ddc@ccd@#-2@dfg#$yhf@ndf#$ndx' -> obj.plan.zzz.dddf.aa.bb.ddc.ccd[-2].dfg[obj.yhf].ndf[obj.ndx]
            """
            if not path:
                return obj

            # Find the first special character
            at_pos = path.find('@')
            hash_pos = path.find('#')

            # If no special characters, it's a simple attribute
            if at_pos == -1 and hash_pos == -1:
                return getattr(obj, path)

            # Determine which comes first
            if at_pos != -1 and (hash_pos == -1 or at_pos < hash_pos):
                # Attribute access comes first
                attr_name = path[:at_pos]
                rest = path[at_pos + 1 :]
                return resolve_path(getattr(obj, attr_name), rest)

            elif hash_pos != -1:
                # Array indexing comes first
                base_path = path[:hash_pos]
                index_and_rest = path[hash_pos + 1 :]

                # Get the base object
                if base_path:
                    base_obj = resolve_path(obj, base_path)
                else:
                    base_obj = obj

                # Find where the index ends (next @ or # or end of string)
                next_at = index_and_rest.find('@')
                next_hash = index_and_rest.find('#')

                # Find the end of the index part
                if next_at != -1 and (next_hash == -1 or next_at < next_hash):
                    index_str = index_and_rest[:next_at]
                    rest = index_and_rest[next_at + 1 :]
                elif next_hash != -1:
                    index_str = index_and_rest[:next_hash]
                    rest = index_and_rest[next_hash:]
                else:
                    index_str = index_and_rest
                    rest = ''

                # Apply the index
                if index_str.startswith('$'):
                    # Dynamic index
                    index_attr = index_str[1:]
                    index_val = getattr(obj, index_attr)
                    indexed_obj = base_obj[index_val]
                else:
                    # Static index
                    indexed_obj = base_obj[int(index_str)]

                # Continue with the rest
                return resolve_path(indexed_obj, rest)

            # This shouldn't happen, but just in case
            return getattr(obj, path)

        format_values = {}
        for key in passthrough_keys:
            # Handle different key formats
            if '=' in key:
                output_key, input_path = key.split('=', maxsplit=1)
            else:
                output_key = input_path = key

            # Handle json serialization flag
            json_serialize = input_path.endswith(':json')
            if json_serialize:
                input_path = input_path.replace(':json', '')

            # Use the recursive resolver
            base_val = resolve_path(state, input_path)

            # Handle json serialization
            if json_serialize:
                base_val = base_val.model_dump_json()

            format_values[output_key] = base_val

        return {
            'messages': [
                SystemMessage(content=system_prompt.format(**format_values)),
                HumanMessage(content=prompt.format(**format_values)),
            ],
            'tool_call_count': 0,
        }

    def manage_tool_context(state: assistant_schema) -> assistant_schema:
        """Manage tool call context by keeping only the last 2 tool call results and incrementing counter"""
        messages = state.messages
        tool_call_count = getattr(state, 'tool_call_count', 0) + 1

        # Keep system and human messages (non-tool related)
        preserved_messages = []
        ai_tool_pairs = []  # [(ai_message, [tool_messages])]

        current_ai_msg = None
        current_tool_msgs = []

        for msg in messages:
            if isinstance(msg, (SystemMessage, HumanMessage)):
                preserved_messages.append(msg)
            elif isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                # If we have a pending AI message, save the pair
                if current_ai_msg is not None:
                    ai_tool_pairs.append((current_ai_msg, current_tool_msgs))

                # Start new AI message
                current_ai_msg = msg
                current_tool_msgs = []
            elif isinstance(msg, ToolMessage):
                # Add to current tool messages if we have an AI message
                if current_ai_msg is not None:
                    current_tool_msgs.append(msg)
            elif isinstance(msg, AIMessage):
                # Regular AI message without tool calls
                # If we have a pending AI message, save the pair first
                if current_ai_msg is not None:
                    ai_tool_pairs.append((current_ai_msg, current_tool_msgs))
                    current_ai_msg = None
                    current_tool_msgs = []

                # This regular AI message should be preserved
                preserved_messages.append(msg)

        # Don't forget the last AI message if it exists
        if current_ai_msg is not None:
            ai_tool_pairs.append((current_ai_msg, current_tool_msgs))

        # Keep only the last 2 AI-tool pairs
        if len(ai_tool_pairs) > 2:
            ai_tool_pairs = ai_tool_pairs[-2:]

        # Reconstruct messages: preserved messages first, then AI-tool pairs in order
        new_messages = preserved_messages.copy()

        for ai_msg, tool_msgs in ai_tool_pairs:
            new_messages.append(ai_msg)
            new_messages.extend(tool_msgs)

        return {
            'messages': new_messages,
            'tool_call_count': tool_call_count,
        }

    async def struct_output(state: assistant_schema) -> output_schema:
        last_message = state.messages[-1]
        if isinstance(last_message.content, str):
            content = last_message.content
        elif isinstance(last_message.content, list) and last_message.content:
            # Handle different content formats
            first_content = last_message.content[0]
            if isinstance(first_content, dict):
                content = first_content.get('text', str(first_content))
            else:
                content = str(first_content)
        else:
            content = str(last_message.content)
        extractor = create_extractor(llm, tools=[structured_output_schema], tool_choice='any')
        messages = extractor_prompt.format(content=content)
        res = await extractor.ainvoke(messages)

        if aggregate_output:
            return {
                output_key: [
                    res['responses'][0]
                    if extracted_output_key is None
                    else getattr(res['responses'][0], extracted_output_key)
                ],
                'messages': [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
                'tool_call_count': 0,
            }
        else:
            return {
                output_key: (
                    res['responses'][0]
                    if extracted_output_key is None
                    else getattr(res['responses'][0], extracted_output_key)
                ),
                'messages': [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
                'tool_call_count': 0,
            }

    def reg_output(state: assistant_schema) -> output_schema:
        if aggregate_output:
            return {
                output_key: [state.messages[-1].content],
                'messages': [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
                'tool_call_count': 0,
            }
        else:
            return {
                output_key: state.messages[-1].content,
                'messages': [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
                'tool_call_count': 0,
            }

    # Create a custom tools condition with the max_tool_calls parameter
    def custom_tools_condition(state: assistant_schema) -> Literal['tools', 'output_node']:
        return tools_condition(state, max_tool_calls=max_tool_calls)

    builder = StateGraph(assistant_schema, output=output_schema)
    builder.add_node('prompt_builder', build_prompt)
    builder.add_node('assistant', assistant)
    builder.add_node('tools', ToolNode(tools))
    builder.add_node('manage_context', manage_tool_context)
    builder.add_node(
        'output_node', struct_output if structured_output_schema is not None else reg_output
    )
    builder.set_entry_point('prompt_builder')
    builder.add_edge('prompt_builder', 'assistant')
    builder.add_conditional_edges('assistant', custom_tools_condition)
    builder.add_edge('tools', 'manage_context')
    builder.add_edge('manage_context', 'assistant')
    builder.add_edge('output_node', END)

    return builder

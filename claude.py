"""A thin shim over the Anthropic SDK, with names we find clearer."""

import anthropic

MODEL = "claude-sonnet-5-5"

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


def get_next_answer(conversation, tools):
    """Send the whole conversation and the tools to Claude, and return its reply."""
    return client.messages.create(
        model=MODEL, max_tokens=16000, messages=conversation, tools=tools
    )


def text_of(message):
    """The text of Claude's reply, without tool calls or thinking."""
    return "".join(block.text for block in message.content if block.type == "text")

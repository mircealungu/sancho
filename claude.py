"""A thin shim over the Anthropic SDK, with names we find clearer."""

import anthropic

MODEL = "claude-sonnet-5-5"

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment


def get_next_answer(conversation):
    """Send the whole conversation to Claude and return its reply."""
    return client.messages.create(model=MODEL, max_tokens=16000, messages=conversation)

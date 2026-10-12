"""A thin shim over the Anthropic SDK, with names we find clearer."""

import os

import anthropic

MODEL = "claude-sonnet-5-5"

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

# Raised when Claude can't be reached: no network, overloaded, rate-limited, ...
# (the SDK has already retried twice by then).
Unreachable = anthropic.APIError


OWN_CODE_FOLDER = os.path.dirname(os.path.abspath(__file__))

SYSTEM_PROMPT = f"""\
You are Sancho, a small coding agent running in a terminal.
You have four tools: read_file, list_folder, edit_file and run_program.
You work in {os.getcwd()}, the folder the user started you in.
Your own code is in {OWN_CODE_FOLDER}, so you can read it to learn how you work.
If you change your own code, the changes take effect only after the user restarts you.
Keep your answers short: they are shown in a terminal."""


def get_next_answer(conversation, tools):
    """Send the whole conversation and the tools to Claude, and return its reply."""
    return client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=conversation,
        tools=tools,
    )


def text_of(message):
    """The text of Claude's reply, without tool calls or thinking."""
    return "".join(block.text for block in message.content if block.type == "text")


def tool_calls_of(message):
    """The tools Claude asks us to run in this reply."""
    return [block for block in message.content if block.type == "tool_use"]

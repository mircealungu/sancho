"""Sancho: a basic chat agent, inspired by Thorsten Ball's "How to Build an Agent"."""

import readline  # importing it is enough: input() gets line editing and history
import sys

from rich.console import Console
from rich.markdown import Markdown

import claude
import tools

console = Console()


def agent_loop(conversation):
    """Keep asking Claude, and running the tools it asks for, until it's done."""
    while True:
        message = claude.get_next_answer(conversation, tools.DEFINITIONS, yolo=tools.yolo)

        # Every reply goes into the conversation, tool calls included: the API
        # matches each tool_result to a tool_use in the previous assistant message,
        # and wants the reply's thinking blocks sent back unchanged.
        conversation.append({"role": "assistant", "content": message.content})

        text = claude.text_of(message)
        if text:
            console.print("Sancho:", Markdown(text))

        if message.stop_reason != "tool_use":
            return

        tool_calls = claude.tool_calls_of(message)
        results = tools.run(tool_calls)
        conversation.append({"role": "user", "content": results})


def main():
    conversation = []
    if "--yolo" in sys.argv:
        tools.yolo = True
        print(
            "\033[33mWarning: --yolo is on. Sancho will run programs without asking.\033[0m"
        )
    print("Sancho: ¡A sus órdenes, mi señor! 🫡  (adiós or Ctrl-D to quit)")

    try:
        while True:
            user_input = input("\nYou: ")

            if user_input.strip().lower() in ["quit", "exit", "adios", "adiós"]:
                break

            if not user_input.strip():
                continue

            conversation.append({"role": "user", "content": user_input})
            try:
                agent_loop(conversation)
            except claude.Unreachable as e:
                print(
                    f"Sancho can't reach Claude right now: {e} Try again in a moment."
                )
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
